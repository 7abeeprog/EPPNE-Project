"""
regression test لجلسة `guardian-relationship-foundation-implementation`
(2026-09-16) — أساس علاقة ولي أمر↔طالب (migration 056 + دومين
app/domains/guardian/ جديد بالكامل): guardian_relationships,
guardian_visibility_settings. صفر منطق تدفق (طلب/موافقة/رفض/تحقق إداري)
فعلي في هذه المرحلة — إنشاء مباشر عبر الـrepository فقط، بلا service
ولا router بعد. راجع:
.claude/reports/guardian-relationship-foundation-implementation-session-log.md

يغطي: إنشاء GuardianRelationship + 4 صفوف GuardianVisibilitySetting (كل
قطاعات GuardianVisibilitySector)، وتأكيد القيدين الفريدين شغالين فعليًا
على مستوى DB (مش مجرد افتراض من الـschema):
- uq_guardian_ward: (guardian_user_id, ward_user_id)
- uq_guardian_visibility_relationship_sector: (guardian_relationship_id, sector)
"""
import uuid

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.guardian.repository import GuardianRepository
from app.domains.guardian.models import (
    GuardianRelationship, GuardianVisibilitySetting,
    GuardianRelationshipType, GuardianRelationshipStatus, GuardianVisibilitySector,
)

TENANT_ID = 1
ALL_SECTORS = [
    GuardianVisibilitySector.ACADEMY,
    GuardianVisibilitySector.SOCIAL,
    GuardianVisibilitySector.TRANSPORT,
    GuardianVisibilitySector.HEALTH,
]


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


# ============================================================
# 1) إنشاء العلاقة + 4 صفوف رؤية (سطر واحد لكل قطاع) — القيمة الافتراضية
#    للحالة PENDING_WARD_APPROVAL
# ============================================================

@pytest.mark.asyncio
async def test_create_relationship_and_visibility_settings_for_all_sectors(db):
    guardian = await _create_user(db, "p_regtest_guardian")
    ward = await _create_user(db, "p_regtest_ward")

    repo = GuardianRepository(db)
    relationship_id = None
    try:
        relationship = await repo.create_relationship(
            tenant_id=TENANT_ID,
            guardian_user_id=guardian.id,
            ward_user_id=ward.id,
            relationship_type=GuardianRelationshipType.FATHER,
            initiated_by_user_id=guardian.id,
        )
        relationship_id = relationship.id
        # commit إجباري هنا — INSERT في guardian_relationships بياخد قفل
        # FOR KEY SHARE على صفوف users المُشار إليها (guardian/ward) لحد ما
        # الترانزاكشن الحالية تتقفل. من غير commit، DELETE FROM users في
        # الـfinally (عبر session منفصلة) بيتعلّق (deadlock) لحد ما نفس
        # الـtest function يخلص أصلًا — وهو ده اللي بيستنى الـfinally عشان
        # يخلص. راجع تفاصيل الاكتشاف في تقرير الجلسة.
        await db.commit()

        assert relationship.tenant_id == TENANT_ID
        assert relationship.guardian_user_id == guardian.id
        assert relationship.ward_user_id == ward.id
        assert relationship.relationship_type == GuardianRelationshipType.FATHER
        # الحالة الافتراضية — صفر منطق تدفق يغيّرها في هذه المرحلة
        assert relationship.status == GuardianRelationshipStatus.PENDING_WARD_APPROVAL
        assert relationship.ward_birth_date_provided is None
        assert relationship.verified_by is None
        assert relationship.verified_at is None

        for sector in ALL_SECTORS:
            setting = await repo.create_visibility_setting(
                guardian_relationship_id=relationship.id,
                sector=sector,
            )
            assert setting.guardian_relationship_id == relationship.id
            assert setting.sector == sector
            assert setting.is_visible is True
        await db.commit()

        settings = await repo.list_visibility_settings(relationship.id)
        assert len(settings) == 4
        assert {s.sector for s in settings} == set(ALL_SECTORS)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            if relationship_id:
                await cleanup_db.execute(
                    delete(GuardianVisibilitySetting).where(
                        GuardianVisibilitySetting.guardian_relationship_id == relationship_id
                    )
                )
                await cleanup_db.execute(
                    delete(GuardianRelationship).where(GuardianRelationship.id == relationship_id)
                )
            await cleanup_db.execute(delete(User).where(User.id.in_([guardian.id, ward.id])))
            await cleanup_db.commit()


# ============================================================
# 2) القيد الفريد uq_guardian_ward — نفس (guardian_user_id, ward_user_id)
#    مرتين لازم يترفض على مستوى DB
# ============================================================

@pytest.mark.asyncio
async def test_duplicate_guardian_ward_pair_rejected_by_unique_constraint(db):
    guardian = await _create_user(db, "p_regtest_guardian_dup")
    ward = await _create_user(db, "p_regtest_ward_dup")
    # التقاط الـids كقيم Python عادية فورًا — نفس سبب توثيق نمط achievements
    # (await db.rollback() تحت بيـexpire كل كائنات الـsession).
    guardian_id, ward_id = guardian.id, ward.id

    repo = GuardianRepository(db)
    relationship_id = None
    try:
        first = await repo.create_relationship(
            tenant_id=TENANT_ID,
            guardian_user_id=guardian_id,
            ward_user_id=ward_id,
            relationship_type=GuardianRelationshipType.MOTHER,
            initiated_by_user_id=guardian_id,
        )
        relationship_id = first.id
        # نفس سبب commit الإجباري في الاختبار الأول — قفل FOR KEY SHARE على
        # صفوف users لازم يتفكّ قبل أي DELETE من session منفصلة (finally).
        await db.commit()

        with pytest.raises(IntegrityError):
            await repo.create_relationship(
                tenant_id=TENANT_ID,
                guardian_user_id=guardian_id,
                ward_user_id=ward_id,
                relationship_type=GuardianRelationshipType.GUARDIAN,
                initiated_by_user_id=guardian_id,
            )
        await db.rollback()

        # لسه صف واحد بس فعليًا لنفس الزوج
        existing = await repo.get_relationship_by_guardian_and_ward(guardian_id, ward_id)
        assert existing is not None
        assert existing.id == relationship_id
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            if relationship_id:
                await cleanup_db.execute(
                    delete(GuardianRelationship).where(GuardianRelationship.id == relationship_id)
                )
            await cleanup_db.execute(delete(User).where(User.id.in_([guardian_id, ward_id])))
            await cleanup_db.commit()


# ============================================================
# 3) القيد الفريد uq_guardian_visibility_relationship_sector — نفس
#    (guardian_relationship_id, sector) مرتين لازم يترفض على مستوى DB
# ============================================================

@pytest.mark.asyncio
async def test_duplicate_visibility_sector_rejected_by_unique_constraint(db):
    guardian = await _create_user(db, "p_regtest_guardian_vis")
    ward = await _create_user(db, "p_regtest_ward_vis")
    guardian_id, ward_id = guardian.id, ward.id

    repo = GuardianRepository(db)
    relationship_id = None
    try:
        relationship = await repo.create_relationship(
            tenant_id=TENANT_ID,
            guardian_user_id=guardian_id,
            ward_user_id=ward_id,
            relationship_type=GuardianRelationshipType.GUARDIAN,
            initiated_by_user_id=guardian_id,
        )
        relationship_id = relationship.id
        # نفس سبب commit الإجباري في الاختبار الأول.
        await db.commit()

        await repo.create_visibility_setting(
            guardian_relationship_id=relationship_id,
            sector=GuardianVisibilitySector.ACADEMY,
        )
        await db.commit()

        with pytest.raises(IntegrityError):
            await repo.create_visibility_setting(
                guardian_relationship_id=relationship_id,
                sector=GuardianVisibilitySector.ACADEMY,
                is_visible=False,
            )
        await db.rollback()

        settings = await repo.list_visibility_settings(relationship_id)
        assert len(settings) == 1
        assert settings[0].sector == GuardianVisibilitySector.ACADEMY
        assert settings[0].is_visible is True
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            if relationship_id:
                await cleanup_db.execute(
                    delete(GuardianVisibilitySetting).where(
                        GuardianVisibilitySetting.guardian_relationship_id == relationship_id
                    )
                )
                await cleanup_db.execute(
                    delete(GuardianRelationship).where(GuardianRelationship.id == relationship_id)
                )
            await cleanup_db.execute(delete(User).where(User.id.in_([guardian_id, ward_id])))
            await cleanup_db.commit()
