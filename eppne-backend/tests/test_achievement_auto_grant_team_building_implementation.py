"""
regression test لجلسة `achievement-auto-grant-team-building` (2026-09-15)
— ربط `AchievementService.update_bootcamp_network_stats` بمنح
`UserAchievement` تلقائيًا لما `bootcamp_network_size` سلف معيّن يتجاوز
`trigger_threshold` تعريف TEAM_BUILDING نشط. راجع:
.claude/reports/achievement-auto-grant-team-building-session-log.md

يغطي:
1) سلسلة أ→ب→ج→د (referred_by_user_id)، كل واحد (ب، ج، د) يسجّل في
   بوتكامب throwaway بالتتابع، وبعد كل تسجيل بننادي
   update_bootcamp_network_stats مباشرة (محاكاة اللي
   dispatch_critical_event_task هيعمله فعليًا — الربط ده نفسه اتأكَّد
   حيًا خلاص في جلسة achievement-network-tracking-implementation).
   بعد تسجيل د (التالت في السلسلة، أ مش من ضمن اللي بيسجّلوا لأنه
   الجذر ومالوش راعٍ): عداد أ يوصل 3 → أ يتمنح الإنجاز تلقائيًا
   (granted_by=None). ب (عداده 2) وج (عداده 1) لسه ملهمش الإنجاز.
2) idempotency: تسجيل تاني لـد في بوتكامب مختلف → عداد أ يتزوّد لـ4
   (فوق العتبة تاني) → أ مايتمنحش نسخة تانية (القيد الفريد، بلا أي
   استثناء). بالإضافي: عداد ب بيوصل 3 في نفس الجولة دي لأول مرة →
   ب بيتمنح الإنجاز صح (سلوك متوقَّع، مش تكرار).
"""
import uuid

import pytest
from sqlalchemy import delete, select

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.academy.service import AcademyService
from app.domains.academy.models import OrganizationEntity, Bootcamp, Course, Enrollment

from app.domains.achievements.service import AchievementService, BOOTCAMP_ENROLLMENT_EVENT_NAME
from app.domains.achievements.schemas import AchievementDefinitionCreate
from app.domains.achievements.models import (
    AchievementDefinition, UserAchievement, UserNetworkStats,
    AchievementCategory, AchievementTriggerType,
)

TENANT_ID = 1
THRESHOLD = 3  # صغيرة عمدًا (بدل 10) عشان الاختبار يكون عملي وسريع


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
        name=f"REGTEST-ACH-AUTOGRANT-ORG-{_suffix()}",
        entity_type="ACADEMY",
    )
    db.add(entity)
    await db.flush()
    return entity


async def _create_bootcamp(db, org_entity_id: int) -> Bootcamp:
    bootcamp = Bootcamp(
        org_entity_id=org_entity_id,
        title=f"REGTEST-ACH-AUTOGRANT-BOOTCAMP-{_suffix()}",
    )
    db.add(bootcamp)
    await db.flush()
    return bootcamp


async def _create_course(db, org_entity_id: int, bootcamp_id: int) -> Course:
    course = Course(
        tenant_id=TENANT_ID,
        org_entity_id=org_entity_id,
        bootcamp_id=bootcamp_id,
        title=f"REGTEST-ACH-AUTOGRANT-COURSE-{_suffix()}",
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


async def _get_network_size(user_id: int):
    async with AsyncSessionLocal() as verify_db:
        result = await verify_db.execute(
            select(UserNetworkStats.bootcamp_network_size).where(UserNetworkStats.user_id == user_id)
        )
        return result.scalar_one_or_none()


@pytest.mark.asyncio
async def test_auto_grant_fires_exactly_when_threshold_crossed_and_is_idempotent(db):
    user_a = await _create_user(db, "p_regtest_ach_autogrant_a")
    user_b = await _create_user(db, "p_regtest_ach_autogrant_b")
    user_c = await _create_user(db, "p_regtest_ach_autogrant_c")
    user_d = await _create_user(db, "p_regtest_ach_autogrant_d")
    user_b.referred_by_user_id = user_a.id
    user_c.referred_by_user_id = user_b.id
    user_d.referred_by_user_id = user_c.id
    a_id, b_id, c_id, d_id = user_a.id, user_b.id, user_c.id, user_d.id

    org = await _create_org_entity(db)
    bootcamp = await _create_bootcamp(db, org.id)
    course_1 = await _create_course(db, org.id, bootcamp.id)
    course_2 = await _create_course(db, org.id, bootcamp.id)
    await db.commit()

    achievement_service = AchievementService(db, TENANT_ID)
    definition_id = None
    try:
        # ---- Seed: تعريف TEAM_BUILDING حقيقي بعتبة صغيرة (3) ----
        definition = await achievement_service.create_definition(
            AchievementDefinitionCreate(
                name=f"REGTEST-TEAM-BUILDER-{_suffix()}",
                description="إنجاز اختباري لجلسة achievement-auto-grant-team-building",
                category=AchievementCategory.TEAM_BUILDING,
                trigger_type=AchievementTriggerType.AUTO_EVENT,
                trigger_event_name=BOOTCAMP_ENROLLMENT_EVENT_NAME,
                trigger_threshold=THRESHOLD,
            ),
            created_by=a_id,
        )
        definition_id = definition.id
        assert definition.is_active is True

        academy_service = AcademyService(db, TENANT_ID)

        # ---- ب يسجّل → عداد أ = 1 (تحت العتبة) ----
        await academy_service.enroll_in_course(b_id, course_1.id, payment_method="FREE")
        await achievement_service.update_bootcamp_network_stats(b_id, TENANT_ID)
        assert await _get_network_size(a_id) == 1
        assert await _get_user_achievements(a_id, definition_id) == []

        # ---- ج يسجّل → عداد ب = 1، عداد أ = 2 (لسه تحت العتبة) ----
        await academy_service.enroll_in_course(c_id, course_1.id, payment_method="FREE")
        await achievement_service.update_bootcamp_network_stats(c_id, TENANT_ID)
        assert await _get_network_size(b_id) == 1
        assert await _get_network_size(a_id) == 2
        assert await _get_user_achievements(a_id, definition_id) == []
        assert await _get_user_achievements(b_id, definition_id) == []

        # ---- د يسجّل (التسجيل التالت) → عداد ج=1، ب=2، أ=3 → أ يتجاوز العتبة ----
        await academy_service.enroll_in_course(d_id, course_1.id, payment_method="FREE")
        await achievement_service.update_bootcamp_network_stats(d_id, TENANT_ID)
        assert await _get_network_size(c_id) == 1
        assert await _get_network_size(b_id) == 2
        assert await _get_network_size(a_id) == 3

        a_achievements = await _get_user_achievements(a_id, definition_id)
        assert len(a_achievements) == 1, "أ لازم يتمنح الإنجاز تلقائيًا فور ما عداده يوصل 3"
        granted = a_achievements[0]
        assert granted.granted_by is None, "منح تلقائي — مفيش مشرف بشري وراه"
        assert granted.source_event_name == BOOTCAMP_ENROLLMENT_EVENT_NAME
        assert granted.source_payload == {"network_size": 3, "ancestor_level": 3}

        # ب (عداده 2) وج (عداده 1) لسه تحت العتبة — مفيش منح
        assert await _get_user_achievements(b_id, definition_id) == []
        assert await _get_user_achievements(c_id, definition_id) == []

        # ================================================================
        # idempotency: د يسجّل تاني في بوتكامب مختلف → عداد أ يتزوّد لـ4
        # (فوق العتبة تاني) — أ مايتمنحش نسخة تانية. عداد ب بيوصل 3 في
        # نفس الجولة دي لأول مرة → ب بيتمنح الإنجاز (سلوك صح، مش تكرار).
        # ================================================================
        await academy_service.enroll_in_course(d_id, course_2.id, payment_method="FREE")
        await achievement_service.update_bootcamp_network_stats(d_id, TENANT_ID)

        assert await _get_network_size(c_id) == 2
        assert await _get_network_size(b_id) == 3
        assert await _get_network_size(a_id) == 4

        a_achievements_after = await _get_user_achievements(a_id, definition_id)
        assert len(a_achievements_after) == 1, "أ مايتمنحش الإنجاز مرتين — القيد الفريد لازم يمنع التكرار بصمت"
        assert a_achievements_after[0].id == granted.id, "نفس الصف الأصلي بالظبط، مش صف جديد"

        b_achievements_after = await _get_user_achievements(b_id, definition_id)
        assert len(b_achievements_after) == 1, "ب لازم يتمنح الإنجاز دلوقتي — عداده وصل للعتبة لأول مرة"
        assert b_achievements_after[0].granted_by is None
        assert b_achievements_after[0].source_payload == {"network_size": 3, "ancestor_level": 2}

        assert await _get_user_achievements(c_id, definition_id) == [], "ج لسه تحت العتبة (عداده 2)"
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(Enrollment).where(Enrollment.user_id.in_([b_id, c_id, d_id])))
            await cleanup_db.execute(delete(UserAchievement).where(UserAchievement.user_id.in_([a_id, b_id, c_id, d_id])))
            await cleanup_db.execute(delete(UserNetworkStats).where(UserNetworkStats.user_id.in_([a_id, b_id, c_id, d_id])))
            if definition_id:
                await cleanup_db.execute(delete(AchievementDefinition).where(AchievementDefinition.id == definition_id))
            await cleanup_db.execute(delete(Course).where(Course.id.in_([course_1.id, course_2.id])))
            await cleanup_db.execute(delete(Bootcamp).where(Bootcamp.id == bootcamp.id))
            await cleanup_db.execute(delete(OrganizationEntity).where(OrganizationEntity.id == org.id))
            await cleanup_db.execute(delete(User).where(User.id.in_([a_id, b_id, c_id, d_id])))
            await cleanup_db.commit()
