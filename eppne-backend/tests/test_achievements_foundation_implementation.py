"""
regression test لجلسة `achievements-foundation-implementation` (2026-09-15)
— أساس نظام الإنجازات (migration 054 + دومين app/domains/achievements/
جديد بالكامل): achievement_definitions, user_achievements,
user_network_stats. صفر منطق شبكة/AUTO_EVENT فعلي في هذه المرحلة —
المنح يدوي بس (SUPER_ADMIN)، راجع:
.claude/reports/achievements-foundation-implementation-session-log.md

يغطي: إنشاء تعريف، منح يدوي لمستخدم، عرض إنجازات المستخدم، ورفض
المنح المكرر (نفس user_id + achievement_definition_id مرتين) بسبب القيد
الفريد ix_user_achievements_unique_user_definition — سواء عبر الـpre-check
في الخدمة (AlreadyExistsError، الحالة الشائعة) أو عبر IntegrityError مباشرة
لو الصف اتحقن يدويًا وتخطّى الـpre-check (تأكيد إن القيد نفسه موجود وفعّال
على مستوى DB، مش مجرد فحص تطبيقي).
"""
import uuid

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.core.errors import AlreadyExistsError, NotFoundError

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.achievements.service import AchievementService
from app.domains.achievements.schemas import AchievementDefinitionCreate
from app.domains.achievements.models import (
    AchievementDefinition, UserAchievement, AchievementCategory, AchievementTriggerType,
)

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


def _definition_payload(name: str) -> AchievementDefinitionCreate:
    return AchievementDefinitionCreate(
        name=name,
        description="إنجاز اختباري لجلسة achievements-foundation-implementation",
        category=AchievementCategory.TRAINING,
        points_value=50,
    )


# ============================================================
# 1) إنشاء تعريف → منح يدوي → عرض إنجازات المستخدم
# ============================================================

@pytest.mark.asyncio
async def test_create_definition_grant_and_list_user_achievements(db):
    admin = await _create_user(db, "p_regtest_ach_admin")
    member = await _create_user(db, "p_regtest_ach_member")

    service = AchievementService(db, TENANT_ID)
    definition_id = None
    try:
        definition = await service.create_definition(
            _definition_payload(f"REGTEST-ACHIEVEMENT-{_suffix()}"),
            created_by=admin.id,
        )
        definition_id = definition.id
        assert definition.tenant_id == TENANT_ID
        assert definition.category == AchievementCategory.TRAINING
        assert definition.trigger_type == AchievementTriggerType.MANUAL
        assert definition.is_active is True
        assert definition.created_by == admin.id

        # القائمة الإدارية بترجع التعريف الجديد
        definitions = await service.list_definitions()
        assert any(d.id == definition.id for d in definitions)

        # منح يدوي
        granted = await service.grant_achievement(
            user_id=member.id,
            achievement_definition_id=definition.id,
            granted_by=admin.id,
        )
        assert granted.user_id == member.id
        assert granted.achievement_definition_id == definition.id
        assert granted.granted_by == admin.id
        assert granted.source_event_name is None
        assert granted.source_payload is None

        # عرض إنجازات المستخدم
        member_achievements = await service.get_user_achievements(member.id)
        assert len(member_achievements) == 1
        assert member_achievements[0].id == granted.id
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(UserAchievement).where(UserAchievement.user_id == member.id))
            if definition_id:
                await cleanup_db.execute(delete(AchievementDefinition).where(AchievementDefinition.id == definition_id))
            await cleanup_db.execute(delete(User).where(User.id.in_([admin.id, member.id])))
            await cleanup_db.commit()


# ============================================================
# 2) رفض المنح المكرر — نفس (user_id, achievement_definition_id) مرتين
# ============================================================

@pytest.mark.asyncio
async def test_duplicate_grant_rejected_by_unique_constraint(db):
    admin = await _create_user(db, "p_regtest_ach_dup_admin")
    member = await _create_user(db, "p_regtest_ach_dup_member")
    # نلتقط الـids كقيم Python عادية فورًا — الـ`await db.rollback()` تحت
    # بيـexpire كل كائنات الـsession، وأي وصول لاحق لـmember.id/admin.id
    # (خاصية ORM) بعد الـrollback بيحاول lazy-refresh ضمني برّه سياق
    # greenlet فيفشل بـMissingGreenlet (نفس الباج الموثَّق في
    # transport/service.py — راجع تعليق مشابه هناك). القيم الخام الملتقطة
    # هنا آمنة تمامًا للاستخدام بعد كده بلا أي IO إضافي.
    admin_id, member_id = admin.id, member.id

    service = AchievementService(db, TENANT_ID)
    definition_id = None
    try:
        definition = await service.create_definition(
            _definition_payload(f"REGTEST-ACHIEVEMENT-DUP-{_suffix()}"),
            created_by=admin_id,
        )
        definition_id = definition.id

        first = await service.grant_achievement(
            user_id=member_id, achievement_definition_id=definition_id, granted_by=admin_id,
        )
        assert first.id is not None

        # المنح الثاني لنفس (user_id, achievement_definition_id) لازم يترفض
        # بوضوح — الخدمة بتفحص pre-check أولًا (AlreadyExistsError)، وده
        # اللي المستخدم النهائي هيشوفه دايمًا عبر الـendpoint.
        with pytest.raises(AlreadyExistsError):
            await service.grant_achievement(
                user_id=member_id, achievement_definition_id=definition_id, granted_by=admin_id,
            )

        # تأكيد إن القيد الفريد نفسه (مش بس الـpre-check التطبيقي) هو اللي
        # بيمنع فعليًا على مستوى DB — نحاول حقن صف مكرر مباشرة عبر الـrepo
        # (متخطّين الـpre-check عمدًا) ونتأكد إن IntegrityError بتتقذف فعلًا.
        with pytest.raises(IntegrityError):
            await service.repo.create_user_achievement(
                tenant_id=TENANT_ID,
                user_id=member_id,
                achievement_definition_id=definition_id,
                granted_by=admin_id,
                source_event_name=None,
                source_payload=None,
            )
        await db.rollback()

        # المستخدم لسه عنده إنجاز واحد بس (مش اتنين)
        member_achievements = await service.get_user_achievements(member_id)
        assert len(member_achievements) == 1
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(UserAchievement).where(UserAchievement.user_id == member_id))
            if definition_id:
                await cleanup_db.execute(delete(AchievementDefinition).where(AchievementDefinition.id == definition_id))
            await cleanup_db.execute(delete(User).where(User.id.in_([admin_id, member_id])))
            await cleanup_db.commit()


# ============================================================
# 3) منح لتعريف غير موجود / مستخدم غير موجود → NotFoundError واضح
# ============================================================

@pytest.mark.asyncio
async def test_grant_nonexistent_definition_or_user_raises_not_found(db):
    admin = await _create_user(db, "p_regtest_ach_nf_admin")
    member = await _create_user(db, "p_regtest_ach_nf_member")

    service = AchievementService(db, TENANT_ID)
    definition_id = None
    try:
        with pytest.raises(NotFoundError):
            await service.grant_achievement(
                user_id=member.id, achievement_definition_id=999_999_999, granted_by=admin.id,
            )

        definition = await service.create_definition(
            _definition_payload(f"REGTEST-ACHIEVEMENT-NF-{_suffix()}"),
            created_by=admin.id,
        )
        definition_id = definition.id

        with pytest.raises(NotFoundError):
            await service.grant_achievement(
                user_id=999_999_999, achievement_definition_id=definition.id, granted_by=admin.id,
            )
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            if definition_id:
                await cleanup_db.execute(delete(AchievementDefinition).where(AchievementDefinition.id == definition_id))
            await cleanup_db.execute(delete(User).where(User.id.in_([admin.id, member.id])))
            await cleanup_db.commit()
