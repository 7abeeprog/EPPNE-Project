"""
regression test لجلسة `achievement-network-tracking-implementation` (2026-09-15)
— (أ) نشر حدث "academy.bootcamp_enrollment.created" عند تسجيل بوتكامب في
academy، (ب) منطق walk-up + تحديث user_network_stats.bootcamp_network_size.
صفر منح UserAchievement تلقائي في هذه الجلسة (المرحلة الجاية). راجع:
.claude/reports/achievement-network-tracking-implementation-session-log.md

يغطي:
1) الحدث بينشر فعليًا لما course.bootcamp_id is not None، وبلا نشر لكورس
   عادي (bootcamp_id=None) — تأكيد الشرط بالاتجاهين.
2) الـwalk-up المباشر (AchievementService.update_bootcamp_network_stats):
   سلسلة أ→ب→ج (referred_by_user_id)، تحديث من نقطة ج → عداد ب وأ
   بيزيد بـ1 لكل واحد، عداد ج نفسه (مش سلف لحد) يفضل بلا صف/0.
3) المسار الكامل عبر dispatch_critical_event_task.run(...) (نفس نمط
   test_critical_event_dispatch_infrastructure.py — بلا worker Celery
   حقيقي محتاج يشتغل، الاستدعاء المباشر بيحاكي تمامًا اللي الـworker
   كان هيعمله): enroll_in_course حقيقي على كورس بوتكامب throwaway من
   طرف ج → الحدث المُلتقَط (spy على event_bus.publish) بيتمرر يدويًا
   لـdispatch_critical_event_task.run(...) → عداد ب وأ اتحدّث فعليًا.
"""
import asyncio
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import delete, select

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal, engine
from app.core.celery_app import celery_app
from app.core.critical_events import CRITICAL_EVENT_HANDLERS

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.academy.service import AcademyService
from app.domains.academy.models import OrganizationEntity, Bootcamp, Course, Enrollment

from app.domains.achievements.service import AchievementService
from app.domains.achievements.models import UserNetworkStats

from app.tasks.events import dispatch_critical_event_task

TENANT_ID = 1
EVENT_NAME = "academy.bootcamp_enrollment.created"


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


async def _create_org_entity(db) -> OrganizationEntity:
    entity = OrganizationEntity(
        tenant_id=TENANT_ID,
        name=f"REGTEST-ACH-NETWORK-ORG-{_suffix()}",
        entity_type="ACADEMY",
    )
    db.add(entity)
    await db.flush()
    return entity


async def _create_bootcamp(db, org_entity_id: int) -> Bootcamp:
    bootcamp = Bootcamp(
        org_entity_id=org_entity_id,
        title=f"REGTEST-ACH-NETWORK-BOOTCAMP-{_suffix()}",
    )
    db.add(bootcamp)
    await db.flush()
    return bootcamp


async def _create_course(db, org_entity_id: int, bootcamp_id=None) -> Course:
    course = Course(
        tenant_id=TENANT_ID,
        org_entity_id=org_entity_id,
        bootcamp_id=bootcamp_id,
        title=f"REGTEST-ACH-NETWORK-COURSE-{_suffix()}",
        price_mrusdt=0,
        is_free=True,
        is_published=True,
    )
    db.add(course)
    await db.flush()
    return course


# ============================================================
# 0) القيد الأول المطلوب: الحدث مسجَّل فعليًا في CRITICAL_EVENT_HANDLERS
# ============================================================

def test_event_registered_as_critical():
    assert EVENT_NAME in CRITICAL_EVENT_HANDLERS


# ============================================================
# 1) academy: الحدث بينشر بس لما bootcamp_id مش None
# ============================================================

@pytest.mark.asyncio
async def test_enroll_publishes_event_only_for_bootcamp_course(db):
    student = await _create_user(db, "p_regtest_ach_net_student")
    org = await _create_org_entity(db)
    bootcamp = await _create_bootcamp(db, org.id)
    bootcamp_course = await _create_course(db, org.id, bootcamp_id=bootcamp.id)
    plain_course = await _create_course(db, org.id, bootcamp_id=None)
    await db.commit()

    service = AcademyService(db, TENANT_ID)
    captured_events = []
    original_publish = service.event_bus.publish

    async def _spy_publish(event_name, payload):
        captured_events.append((event_name, payload))
        return await original_publish(event_name, payload)

    service.event_bus.publish = _spy_publish

    try:
        with patch.object(celery_app, "send_task") as mock_send_task:
            # كورس عادي (بلا بوتكامب) → صفر حدث
            await service.enroll_in_course(student.id, plain_course.id, payment_method="FREE")
            assert captured_events == [], "كورس عادي (bootcamp_id=None) لازم ميبعتش academy.bootcamp_enrollment.created"
            mock_send_task.assert_not_called()

            # كورس بوتكامب → الحدث بينشر بالـpayload المطلوب بالحرف
            await service.enroll_in_course(student.id, bootcamp_course.id, payment_method="FREE")

            assert len(captured_events) == 1
            event_name, payload = captured_events[0]
            assert event_name == EVENT_NAME
            assert payload == {
                "user_id": student.id,
                "tenant_id": TENANT_ID,
                "course_id": bootcamp_course.id,
                "bootcamp_id": bootcamp.id,
            }
            # الحدث مسجَّل في CRITICAL_EVENT_HANDLERS → لازم celery_app.send_task
            # تتنادى بالضبط زي نمط test_critical_event_dispatch_infrastructure.py
            mock_send_task.assert_called_once_with(
                "events.dispatch_critical_event", args=[EVENT_NAME, payload], queue="events",
            )
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(Enrollment).where(Enrollment.user_id == student.id))
            await cleanup_db.execute(delete(Course).where(Course.id.in_([bootcamp_course.id, plain_course.id])))
            await cleanup_db.execute(delete(Bootcamp).where(Bootcamp.id == bootcamp.id))
            await cleanup_db.execute(delete(OrganizationEntity).where(OrganizationEntity.id == org.id))
            await cleanup_db.execute(delete(User).where(User.id == student.id))
            await cleanup_db.commit()


# ============================================================
# 2) walk-up المباشر: أ→ب→ج، تحديث من ج → عداد ب وأ +1، عداد ج يفضل صفر
# ============================================================

@pytest.mark.asyncio
async def test_update_bootcamp_network_stats_walks_up_referral_chain(db):
    user_a = await _create_user(db, "p_regtest_ach_net_a")
    user_b = await _create_user(db, "p_regtest_ach_net_b")
    user_c = await _create_user(db, "p_regtest_ach_net_c")
    user_b.referred_by_user_id = user_a.id
    user_c.referred_by_user_id = user_b.id
    await db.commit()
    a_id, b_id, c_id = user_a.id, user_b.id, user_c.id

    service = AchievementService(db, TENANT_ID)
    try:
        updated = await service.update_bootcamp_network_stats(c_id, TENANT_ID)
        assert updated == [b_id, a_id]  # الأقرب أولًا

        stats_b = await service.repo.get_network_stats(b_id)
        stats_a = await service.repo.get_network_stats(a_id)
        stats_c = await service.repo.get_network_stats(c_id)

        assert stats_b is not None and stats_b.bootcamp_network_size == 1
        assert stats_a is not None and stats_a.bootcamp_network_size == 1
        assert stats_c is None, "ج مش سلف لحد — مفروض مفيش صف user_network_stats ليه من الـwalk-up"

        # تحديث تاني (زي لو ج سجّل في بوتكامب تاني) → العداد يتراكم لـ2
        await service.update_bootcamp_network_stats(c_id, TENANT_ID)
        stats_a_again = await service.repo.get_network_stats(a_id)
        assert stats_a_again is not None and stats_a_again.bootcamp_network_size == 2
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(UserNetworkStats).where(UserNetworkStats.user_id.in_([a_id, b_id, c_id])))
            await cleanup_db.execute(delete(User).where(User.id.in_([a_id, b_id, c_id])))
            await cleanup_db.commit()


# ============================================================
# 3) المسار الكامل: enroll حقيقي → الحدث المُلتقَط يتمرر لـ
#    dispatch_critical_event_task.run(...) (محاكاة الـworker) → العداد اتحدّث
# ============================================================

@pytest.mark.asyncio
async def test_full_dispatch_path_updates_ancestors_network_stats(db):
    user_a = await _create_user(db, "p_regtest_ach_net_full_a")
    user_b = await _create_user(db, "p_regtest_ach_net_full_b")
    user_c = await _create_user(db, "p_regtest_ach_net_full_c")
    user_b.referred_by_user_id = user_a.id
    user_c.referred_by_user_id = user_b.id
    a_id, b_id, c_id = user_a.id, user_b.id, user_c.id

    org = await _create_org_entity(db)
    bootcamp = await _create_bootcamp(db, org.id)
    bootcamp_course = await _create_course(db, org.id, bootcamp_id=bootcamp.id)
    await db.commit()

    academy_service = AcademyService(db, TENANT_ID)
    captured_events = []
    original_publish = academy_service.event_bus.publish

    async def _spy_publish(event_name, payload):
        captured_events.append((event_name, payload))
        return await original_publish(event_name, payload)

    academy_service.event_bus.publish = _spy_publish

    try:
        with patch.object(celery_app, "send_task"):
            # ج يسجّل في بوتكامب throwaway
            await academy_service.enroll_in_course(c_id, bootcamp_course.id, payment_method="FREE")

        assert len(captured_events) == 1
        event_name, payload = captured_events[0]
        assert event_name == EVENT_NAME
        assert payload["user_id"] == c_id

        # محاكاة الـworker: نفس ما celery_app.send_task كان هيبعته فعليًا.
        # dispatch_critical_event_task.run(...) بيفتح event loop خاص بيه
        # داخليًا (_run_async في app/tasks/events.py — نفس نمط worker Celery
        # حقيقي، تحت لا يوجد loop شغّال أصلًا). الاختبار الحالي نفسه async
        # وجوّه loop شغّال بالفعل (pytest-asyncio) — استدعاء .run() مباشرة
        # هنا كان بيفشل بـ"Cannot run the event loop while another loop is
        # running" (اتأكَّد بالتنفيذ الفعلي). asyncio.to_thread وحده مش كافي
        # كمان: engine العام (app/core/database.py) مشترك بين كل الـloops في
        # نفس العملية — thread جديد بـloop جديد ممكن ياخد من pool اتصال
        # asyncpg اتعمل أصلًا في loop التست الرئيسي (pytest-asyncio) فيفشل
        # بـ"attached to a different loop" (اتأكَّد بالتنفيذ الفعلي كمان).
        # الحل الكامل المتطابق مع تعليق conftest.py نفسه (نفس السبب بالظبط):
        # engine.dispose() قبل الـthread يضمن اتصالات جديدة تتبني في loop
        # الـthread، وبعده يضمن استمرار استخدام `db`/AsyncSessionLocal في
        # loop التست الرئيسي بأمان بلا أي اتصال "ملوّث" بـloop التصر.
        await engine.dispose()
        await asyncio.to_thread(dispatch_critical_event_task.run, event_name, payload)
        await engine.dispose()

        async with AsyncSessionLocal() as verify_db:
            stats_b = (await verify_db.execute(
                select(UserNetworkStats).where(UserNetworkStats.user_id == b_id)
            )).scalar_one_or_none()
            stats_a = (await verify_db.execute(
                select(UserNetworkStats).where(UserNetworkStats.user_id == a_id)
            )).scalar_one_or_none()
            stats_c = (await verify_db.execute(
                select(UserNetworkStats).where(UserNetworkStats.user_id == c_id)
            )).scalar_one_or_none()

        assert stats_b is not None and stats_b.bootcamp_network_size == 1
        assert stats_a is not None and stats_a.bootcamp_network_size == 1
        assert stats_c is None
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(Enrollment).where(Enrollment.user_id == c_id))
            await cleanup_db.execute(delete(UserNetworkStats).where(UserNetworkStats.user_id.in_([a_id, b_id, c_id])))
            await cleanup_db.execute(delete(Course).where(Course.id == bootcamp_course.id))
            await cleanup_db.execute(delete(Bootcamp).where(Bootcamp.id == bootcamp.id))
            await cleanup_db.execute(delete(OrganizationEntity).where(OrganizationEntity.id == org.id))
            await cleanup_db.execute(delete(User).where(User.id.in_([a_id, b_id, c_id])))
            await cleanup_db.commit()
