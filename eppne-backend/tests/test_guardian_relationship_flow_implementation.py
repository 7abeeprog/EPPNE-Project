"""
regression test لجلسة `guardian-relationship-flow-implementation`
(2026-09-16) — المرحلة الثانية (منطق التدفق) لعلاقة ولي أمر↔طالب، فوق
أساس [[project_guardian_relationship_foundation_implementation]]
(migration 056 + models/schemas/repository). يغطي `GuardianService`
بالكامل عبر استدعاءات مباشرة (بلا HTTP client — نفس نمط باقي regression
tests بالمشروع)، فوق DB حقيقية بلا mocks. راجع:
.claude/reports/guardian-flow-implementation-planning-session-log.md

يغطي: بحث تطابق تام، إنشاء طلب، موافقة راشد (self-verify فوري)،
موافقة قاصر (→ PENDING_ADMIN_REVIEW + تنبيه أدمنز فعلي، متحقَّق منه عبر
جدول notifications)، مراجعة أدمن (VERIFIED)، رفض الطالب، تكرار الطلب،
تفويض خاطئ (ward مختلف)، وتحكّم الطالب في الرؤية (upsert + قيد الحالة
VERIFIED).
"""
import uuid
from datetime import date

import pytest
from sqlalchemy import delete, select

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.core.enums import SystemRole
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError, AlreadyExistsError

from app.domains.identity.service import UserService
from app.domains.identity.repository import UserRepository
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.communications.models import Notification

from app.domains.guardian.service import GuardianService
from app.domains.guardian.models import (
    GuardianRelationship, GuardianVisibilitySetting,
    GuardianRelationshipType, GuardianRelationshipStatus, GuardianVisibilitySector,
)

TENANT_ID = 1
ADULT_BIRTH_DATE = date(1990, 1, 1)
MINOR_BIRTH_DATE = date.today().replace(year=date.today().year - 10)


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


async def _promote_to_super_admin(db, user_id: int) -> None:
    await UserRepository(db).update(user_id, TENANT_ID, system_role=SystemRole.SUPER_ADMIN)


async def _cleanup(user_ids, relationship_id=None):
    async with AsyncSessionLocal() as cleanup_db:
        if relationship_id:
            # ⚠️ get_tenant_admins() بترجع *كل* SUPER_ADMIN/EXECUTIVE_DIRECTOR
            # الحقيقيين في tenant_id=1 — واكتشفنا فعليًا وقت التطوير إن فيه
            # 24 حساب throwaway قديم من جلسات تانية تمامًا (p_ctor_*, TEST_*)
            # لسه شايل system_role=SUPER_ADMIN من قبل، غير مرتبط بهذه
            # الجلسة إطلاقًا (راجع تقرير الجلسة). التنظيف هنا لازم يمسح كل
            # إشعار مرتبط بهذه العلاقة (بغض النظر مين استلمه)، مش بس
            # user_ids اللي الاختبار نفسه أنشأهم — وإلا كل تشغيلة تسيب
            # صفوف notifications يتيمة على تلك الحسابات القديمة للأبد.
            await cleanup_db.execute(
                delete(Notification).where(
                    Notification.idempotency_key.like(f"GUARDIAN-ADMIN-REVIEW-{relationship_id}-%")
                )
            )
            await cleanup_db.execute(
                delete(GuardianVisibilitySetting).where(
                    GuardianVisibilitySetting.guardian_relationship_id == relationship_id
                )
            )
            await cleanup_db.execute(delete(GuardianRelationship).where(GuardianRelationship.id == relationship_id))
        await cleanup_db.execute(delete(Notification).where(Notification.user_id.in_(user_ids)))
        await cleanup_db.execute(delete(User).where(User.id.in_(user_ids)))
        await cleanup_db.commit()


# ============================================================
# 1) بحث تطابق تام — نجاح + عدم وجود + تحقق مدخلات
# ============================================================

@pytest.mark.asyncio
async def test_find_user_exact_match_not_found_and_validation(db):
    ward = await _create_user(db, "p_regtest_flow_find")
    ward_id = ward.id
    service = GuardianService(db, TENANT_ID)
    try:
        found = await service.find_user(email=ward.email, username=None)
        assert found.id == ward_id

        found2 = await service.find_user(email=None, username=ward.username)
        assert found2.id == ward_id

        with pytest.raises(NotFoundError):
            await service.find_user(email=f"nonexistent_{_suffix()}@eppne.com", username=None)

        with pytest.raises(ValidationError):
            await service.find_user(email=None, username=None)

        with pytest.raises(ValidationError):
            await service.find_user(email=ward.email, username=ward.username)
    finally:
        await _cleanup([ward_id])


# ============================================================
# 2) الطالب راشد → موافقة فورية VERIFIED + إعدادات رؤية افتراضية +
#    تحكّم الطالب في الرؤية بعدها
# ============================================================

@pytest.mark.asyncio
async def test_adult_ward_self_verifies_and_controls_visibility(db):
    guardian = await _create_user(db, "p_regtest_flow_guardian_adult")
    ward = await _create_user(db, "p_regtest_flow_ward_adult")
    guardian_id, ward_id = guardian.id, ward.id

    service = GuardianService(db, TENANT_ID)
    relationship_id = None
    try:
        relationship = await service.create_relationship_request(
            guardian_user_id=guardian_id, ward_user_id=ward_id,
            relationship_type=GuardianRelationshipType.FATHER,
        )
        relationship_id = relationship.id
        assert relationship.status == GuardianRelationshipStatus.PENDING_WARD_APPROVAL

        approved = await service.approve_relationship(
            relationship_id=relationship_id, ward_user_id=ward_id,
            ward_birth_date_provided=ADULT_BIRTH_DATE,
        )
        assert approved.status == GuardianRelationshipStatus.VERIFIED
        assert approved.ward_birth_date_provided == ADULT_BIRTH_DATE
        assert approved.verified_at is not None
        assert approved.verified_by is None  # self-attested، بلا أدمن

        # إعدادات رؤية افتراضية اتنشأت تلقائيًا (كل قطاع True)
        settings = await service.repo.list_visibility_settings(relationship_id)
        assert len(settings) == 4
        assert all(s.is_visible for s in settings)

        # الطالب يقفل قطاع ACADEMY بس
        updated_settings = await service.update_visibility(
            relationship_id=relationship_id, ward_user_id=ward_id,
            settings=[{"sector": GuardianVisibilitySector.ACADEMY, "is_visible": False}],
        )
        academy_setting = next(s for s in updated_settings if s.sector == GuardianVisibilitySector.ACADEMY)
        others = [s for s in updated_settings if s.sector != GuardianVisibilitySector.ACADEMY]
        assert academy_setting.is_visible is False
        assert all(s.is_visible for s in others)
        assert len(updated_settings) == 4  # upsert، مش صف جديد إضافي
    finally:
        await _cleanup([guardian_id, ward_id], relationship_id)


# ============================================================
# 3) الطالب قاصر → PENDING_ADMIN_REVIEW + تنبيه فعلي لكل الأدمنز →
#    مراجعة الأدمن VERIFIED
# ============================================================

@pytest.mark.asyncio
async def test_minor_ward_goes_to_admin_review_notifies_admins_then_verified(db):
    guardian = await _create_user(db, "p_regtest_flow_guardian_minor")
    ward = await _create_user(db, "p_regtest_flow_ward_minor")
    admin = await _create_user(db, "p_regtest_flow_admin")
    guardian_id, ward_id, admin_id = guardian.id, ward.id, admin.id
    await _promote_to_super_admin(db, admin_id)

    service = GuardianService(db, TENANT_ID)
    relationship_id = None
    try:
        relationship = await service.create_relationship_request(
            guardian_user_id=guardian_id, ward_user_id=ward_id,
            relationship_type=GuardianRelationshipType.MOTHER,
        )
        relationship_id = relationship.id

        approved = await service.approve_relationship(
            relationship_id=relationship_id, ward_user_id=ward_id,
            ward_birth_date_provided=MINOR_BIRTH_DATE,
        )
        assert approved.status == GuardianRelationshipStatus.PENDING_ADMIN_REVIEW
        assert approved.ward_birth_date_provided == MINOR_BIRTH_DATE

        # تحقق فعلي من DB إن الأدمن اتبعتله إشعار حقيقي (مش mock)
        result = await db.execute(
            select(Notification).where(
                Notification.user_id == admin_id,
                Notification.idempotency_key == f"GUARDIAN-ADMIN-REVIEW-{relationship_id}-{admin_id}",
            )
        )
        notification = result.scalar_one_or_none()
        assert notification is not None
        assert "مراجعة" in notification.title

        # صفر إعدادات رؤية قبل VERIFIED
        settings_before = await service.repo.list_visibility_settings(relationship_id)
        assert len(settings_before) == 0

        reviewed = await service.review_relationship(
            relationship_id=relationship_id, admin_id=admin_id,
            status=GuardianRelationshipStatus.VERIFIED, rejection_reason=None,
        )
        assert reviewed.status == GuardianRelationshipStatus.VERIFIED
        assert reviewed.verified_by == admin_id
        assert reviewed.verified_at is not None

        settings_after = await service.repo.list_visibility_settings(relationship_id)
        assert len(settings_after) == 4
    finally:
        await _cleanup([guardian_id, ward_id, admin_id], relationship_id)


# ============================================================
# 4) رفض الطالب — REJECTED + معالجة مزدوجة ممنوعة
# ============================================================

@pytest.mark.asyncio
async def test_ward_reject_flow_and_double_processing_blocked(db):
    guardian = await _create_user(db, "p_regtest_flow_guardian_reject")
    ward = await _create_user(db, "p_regtest_flow_ward_reject")
    guardian_id, ward_id = guardian.id, ward.id

    service = GuardianService(db, TENANT_ID)
    relationship_id = None
    try:
        relationship = await service.create_relationship_request(
            guardian_user_id=guardian_id, ward_user_id=ward_id,
            relationship_type=GuardianRelationshipType.GUARDIAN,
        )
        relationship_id = relationship.id

        rejected = await service.reject_relationship(
            relationship_id=relationship_id, ward_user_id=ward_id,
            rejection_reason="مش عايز الربط ده",
        )
        assert rejected.status == GuardianRelationshipStatus.REJECTED
        assert rejected.rejection_reason == "مش عايز الربط ده"

        with pytest.raises(ValidationError):
            await service.approve_relationship(
                relationship_id=relationship_id, ward_user_id=ward_id,
                ward_birth_date_provided=ADULT_BIRTH_DATE,
            )
        with pytest.raises(ValidationError):
            await service.reject_relationship(
                relationship_id=relationship_id, ward_user_id=ward_id, rejection_reason=None,
            )
    finally:
        await _cleanup([guardian_id, ward_id], relationship_id)


# ============================================================
# 5) تكرار نفس زوج (guardian, ward) — AlreadyExistsError
# ============================================================

@pytest.mark.asyncio
async def test_duplicate_relationship_request_rejected(db):
    guardian = await _create_user(db, "p_regtest_flow_guardian_dup")
    ward = await _create_user(db, "p_regtest_flow_ward_dup")
    guardian_id, ward_id = guardian.id, ward.id

    service = GuardianService(db, TENANT_ID)
    relationship_id = None
    try:
        first = await service.create_relationship_request(
            guardian_user_id=guardian_id, ward_user_id=ward_id,
            relationship_type=GuardianRelationshipType.FATHER,
        )
        relationship_id = first.id

        with pytest.raises(AlreadyExistsError):
            await service.create_relationship_request(
                guardian_user_id=guardian_id, ward_user_id=ward_id,
                relationship_type=GuardianRelationshipType.GUARDIAN,
            )
    finally:
        await _cleanup([guardian_id, ward_id], relationship_id)


# ============================================================
# 6) تفويض خاطئ — مستخدم مش الطالب المستهدف يحاول يوافق/يرفض
# ============================================================

@pytest.mark.asyncio
async def test_wrong_user_cannot_approve_or_reject(db):
    guardian = await _create_user(db, "p_regtest_flow_guardian_wrong")
    ward = await _create_user(db, "p_regtest_flow_ward_wrong")
    stranger = await _create_user(db, "p_regtest_flow_stranger")
    guardian_id, ward_id, stranger_id = guardian.id, ward.id, stranger.id

    service = GuardianService(db, TENANT_ID)
    relationship_id = None
    try:
        relationship = await service.create_relationship_request(
            guardian_user_id=guardian_id, ward_user_id=ward_id,
            relationship_type=GuardianRelationshipType.FATHER,
        )
        relationship_id = relationship.id

        with pytest.raises(PermissionDeniedError):
            await service.approve_relationship(
                relationship_id=relationship_id, ward_user_id=stranger_id,
                ward_birth_date_provided=ADULT_BIRTH_DATE,
            )
        with pytest.raises(PermissionDeniedError):
            await service.reject_relationship(
                relationship_id=relationship_id, ward_user_id=stranger_id, rejection_reason=None,
            )

        # لسه PENDING_WARD_APPROVAL — محاولة المراجعة الإدارية المبكرة تترفض
        with pytest.raises(ValidationError):
            await service.review_relationship(
                relationship_id=relationship_id, admin_id=guardian_id,
                status=GuardianRelationshipStatus.VERIFIED, rejection_reason=None,
            )

        # ومحاولة تحكّم الطالب في الرؤية قبل VERIFIED كمان تترفض
        with pytest.raises(ValidationError):
            await service.update_visibility(
                relationship_id=relationship_id, ward_user_id=ward_id,
                settings=[{"sector": GuardianVisibilitySector.HEALTH, "is_visible": False}],
            )
    finally:
        await _cleanup([guardian_id, ward_id, stranger_id], relationship_id)
