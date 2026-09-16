"""
regression test لجلسة `achievement-auto-grant-training` (2026-09-15) —
ربط فئة TRAINING بالمنح التلقائي: حدث واحد بسيط
("academy.course.completed")، بلا walk-up، بلا تخصيص كورس، بلا فحص
عتبة (منح مباشر لأول مرة). راجع:
.claude/reports/achievement-auto-grant-training-session-log.md

يغطي:
1) `AcademyService.update_progress` بينشر الحدث **بس** لما
   `progress >= 100` (`is_completed` بيبقى `True`) — صفر نشر لتحديث
   تقدّم جزئي (`progress=50`).
2) `AchievementService.grant_training_achievements_for_course_completion`:
   أول إكمال كورس → إنجاز TRAINING يتمنح (`granted_by=None`). إكمال
   كورس **تاني مختلف** بنفس المستخدم → صفر إنجاز إضافي (القيد الفريد
   بيمنع — التعريف عام، مش خاص بكورس معيّن، زي ما تقرَّر في تقرير
   التخطيط).
3) المسار الكامل عبر dispatch_critical_event_task.run(...) (نفس نمط
   test_achievement_network_tracking_implementation.py — asyncio.to_thread
   + engine.dispose() bracketing لتفادي تضارب event loop المُوثَّق هناك).
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
from app.domains.academy.models import OrganizationEntity, Course, Enrollment

from app.domains.achievements.service import AchievementService, COURSE_COMPLETED_EVENT_NAME
from app.domains.achievements.schemas import AchievementDefinitionCreate
from app.domains.achievements.models import (
    AchievementDefinition, UserAchievement, AchievementCategory, AchievementTriggerType,
)

from app.tasks.events import dispatch_critical_event_task

TENANT_ID = 1


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
        name=f"REGTEST-ACH-TRAINING-ORG-{_suffix()}",
        entity_type="ACADEMY",
    )
    db.add(entity)
    await db.flush()
    return entity


async def _create_course(db, org_entity_id: int) -> Course:
    # كورس عادي (بلا بوتكامب) عمدًا — TRAINING مش خاصة بالبوتكامب
    course = Course(
        tenant_id=TENANT_ID,
        org_entity_id=org_entity_id,
        bootcamp_id=None,
        title=f"REGTEST-ACH-TRAINING-COURSE-{_suffix()}",
        price_mrusdt=0,
        is_free=True,
        is_published=True,
    )
    db.add(course)
    await db.flush()
    return course


async def _get_user_achievements(user_id: int, definition_id: int) -> list:
    async with AsyncSessionLocal() as verify_db:
        result = await verify_db.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_definition_id == definition_id,
            )
        )
        return list(result.scalars().all())


def test_event_registered_as_critical():
    assert COURSE_COMPLETED_EVENT_NAME in CRITICAL_EVENT_HANDLERS


@pytest.mark.asyncio
async def test_update_progress_publishes_event_only_on_completion(db):
    student = await _create_user(db, "p_regtest_ach_training_progress")
    org = await _create_org_entity(db)
    course = await _create_course(db, org.id)
    await db.commit()

    academy_service = AcademyService(db, TENANT_ID)
    await academy_service.enroll_in_course(student.id, course.id, payment_method="FREE")

    captured_events = []
    original_publish = academy_service.event_bus.publish

    async def _spy_publish(event_name, payload):
        captured_events.append((event_name, payload))
        return await original_publish(event_name, payload)

    academy_service.event_bus.publish = _spy_publish

    try:
        with patch.object(celery_app, "send_task") as mock_send_task:
            # تحديث تقدّم جزئي → صفر نشر
            await academy_service.update_progress(student.id, course.id, 50.0)
            assert captured_events == [], "progress=50 (لسه مش مكتمل) لازم ميبعتش academy.course.completed"
            mock_send_task.assert_not_called()

            # إكمال فعلي → الحدث بينشر بالـpayload المطلوب بالحرف
            await academy_service.update_progress(student.id, course.id, 100.0)

        assert len(captured_events) == 1
        event_name, payload = captured_events[0]
        assert event_name == COURSE_COMPLETED_EVENT_NAME
        assert payload == {"user_id": student.id, "tenant_id": TENANT_ID, "course_id": course.id}
        mock_send_task.assert_called_once_with(
            "events.dispatch_critical_event", args=[COURSE_COMPLETED_EVENT_NAME, payload], queue="events",
        )
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(Enrollment).where(Enrollment.user_id == student.id))
            await cleanup_db.execute(delete(Course).where(Course.id == course.id))
            await cleanup_db.execute(delete(OrganizationEntity).where(OrganizationEntity.id == org.id))
            await cleanup_db.execute(delete(User).where(User.id == student.id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_first_course_completion_grants_training_achievement_second_course_does_not(db):
    student = await _create_user(db, "p_regtest_ach_training_grant")
    org = await _create_org_entity(db)
    course_1 = await _create_course(db, org.id)
    course_2 = await _create_course(db, org.id)
    await db.commit()

    academy_service = AcademyService(db, TENANT_ID)
    achievement_service = AchievementService(db, TENANT_ID)
    definition_id = None
    try:
        definition = await achievement_service.create_definition(
            AchievementDefinitionCreate(
                name="أول خطوة",
                description="إنجاز اختباري لجلسة achievement-auto-grant-training",
                category=AchievementCategory.TRAINING,
                trigger_type=AchievementTriggerType.AUTO_EVENT,
                trigger_event_name=COURSE_COMPLETED_EVENT_NAME,
            ),
            created_by=student.id,
        )
        definition_id = definition.id
        assert definition.trigger_threshold is None  # غير مستخدَم لـTRAINING

        # ---- إكمال الكورس الأول → منح مباشر ----
        await academy_service.enroll_in_course(student.id, course_1.id, payment_method="FREE")
        with patch.object(celery_app, "send_task"):
            await academy_service.update_progress(student.id, course_1.id, 100.0)

        granted = await achievement_service.grant_training_achievements_for_course_completion(
            user_id=student.id, tenant_id=TENANT_ID, course_id=course_1.id,
        )
        assert granted == [definition_id]

        achievements_after_first = await _get_user_achievements(student.id, definition_id)
        assert len(achievements_after_first) == 1
        row = achievements_after_first[0]
        assert row.granted_by is None
        assert row.source_event_name == COURSE_COMPLETED_EVENT_NAME
        assert row.source_payload == {"course_id": course_1.id}

        # ---- إكمال كورس تاني مختلف → صفر إنجاز إضافي (نفس التعريف العام) ----
        await academy_service.enroll_in_course(student.id, course_2.id, payment_method="FREE")
        with patch.object(celery_app, "send_task"):
            await academy_service.update_progress(student.id, course_2.id, 100.0)

        granted_again = await achievement_service.grant_training_achievements_for_course_completion(
            user_id=student.id, tenant_id=TENANT_ID, course_id=course_2.id,
        )
        assert granted_again == [], "كورس تاني — التعريف عام مش خاص بكورس، مايتمنحش تاني"

        achievements_after_second = await _get_user_achievements(student.id, definition_id)
        assert len(achievements_after_second) == 1, "لازم يفضل صف واحد بالظبط، مش اتنين"
        assert achievements_after_second[0].id == row.id, "نفس الصف الأصلي بالظبط"
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(Enrollment).where(Enrollment.user_id == student.id))
            await cleanup_db.execute(delete(UserAchievement).where(UserAchievement.user_id == student.id))
            if definition_id:
                await cleanup_db.execute(delete(AchievementDefinition).where(AchievementDefinition.id == definition_id))
            await cleanup_db.execute(delete(Course).where(Course.id.in_([course_1.id, course_2.id])))
            await cleanup_db.execute(delete(OrganizationEntity).where(OrganizationEntity.id == org.id))
            await cleanup_db.execute(delete(User).where(User.id == student.id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_full_dispatch_path_grants_achievement(db):
    student = await _create_user(db, "p_regtest_ach_training_full")
    org = await _create_org_entity(db)
    course = await _create_course(db, org.id)
    await db.commit()
    student_id = student.id

    academy_service = AcademyService(db, TENANT_ID)
    achievement_service = AchievementService(db, TENANT_ID)
    definition_id = None
    try:
        definition = await achievement_service.create_definition(
            AchievementDefinitionCreate(
                name="أول خطوة (dispatch)",
                description="إنجاز اختباري لمسار dispatch الكامل",
                category=AchievementCategory.TRAINING,
                trigger_type=AchievementTriggerType.AUTO_EVENT,
                trigger_event_name=COURSE_COMPLETED_EVENT_NAME,
            ),
            created_by=student_id,
        )
        definition_id = definition.id

        captured_events = []
        original_publish = academy_service.event_bus.publish

        async def _spy_publish(event_name, payload):
            captured_events.append((event_name, payload))
            return await original_publish(event_name, payload)

        academy_service.event_bus.publish = _spy_publish

        await academy_service.enroll_in_course(student_id, course.id, payment_method="FREE")
        with patch.object(celery_app, "send_task"):
            await academy_service.update_progress(student_id, course.id, 100.0)

        assert len(captured_events) == 1
        event_name, payload = captured_events[0]
        assert event_name == COURSE_COMPLETED_EVENT_NAME

        # محاكاة الـworker — نفس نمط test_achievement_network_tracking_implementation.py
        await engine.dispose()
        await asyncio.to_thread(dispatch_critical_event_task.run, event_name, payload)
        await engine.dispose()

        achievements = await _get_user_achievements(student_id, definition_id)
        assert len(achievements) == 1
        assert achievements[0].granted_by is None
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(Enrollment).where(Enrollment.user_id == student_id))
            await cleanup_db.execute(delete(UserAchievement).where(UserAchievement.user_id == student_id))
            if definition_id:
                await cleanup_db.execute(delete(AchievementDefinition).where(AchievementDefinition.id == definition_id))
            await cleanup_db.execute(delete(Course).where(Course.id == course.id))
            await cleanup_db.execute(delete(OrganizationEntity).where(OrganizationEntity.id == org.id))
            await cleanup_db.execute(delete(User).where(User.id == student_id))
            await cleanup_db.commit()
