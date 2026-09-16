"""
regression test لجلسة `health-entity-membership-implementation` (2026-09-14)
— تنفيذ نمط EntityMembership (insurance/transport/tourism_sports) على
`create_facility` فقط في health، بناءً على فحص read-only سابق:
`.claude/reports/health-entity-membership-planning-session-log.md`.

**خارج النطاق صراحة (لم يُلمَس):** get_or_create_profile (`tenant_id or 1`
fallback)، list_facilities (فلترة tenant بعد الجلب في بايثون).

الأدوار المسموحة: OWNER, EXECUTIVE_DIRECTOR (نفس insurance/transport/
tourism_sports بالحرف).

يغطي `create_facility` فقط — عضو مسموح ينجح، غير عضو يترفض بـ
PermissionDeniedError (→403 عبر core/errors.py)، + تأكيد
ondelete='SET NULL' الجديد على health_facilities.entity_id (migration 052)
— نفس شكل test_tourism_sports_entity_membership_full_implementation.py
بالضبط.
"""
import uuid

import pytest
from sqlalchemy import delete, select

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.core.errors import PermissionDeniedError

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.sovereign_entities.models import SovereignEntity, SovereignEntityType
from app.core.models import EntityMembership, EntityMembershipRole

from app.domains.health.service import HealthService, ENTITY_TYPE
from app.domains.health.repository import HealthRepository
from app.domains.health.models import HealthFacility, FacilityCategory

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


async def _create_sovereign_entity(db, creator_id: int) -> SovereignEntity:
    suffix = _suffix()
    entity = SovereignEntity(
        tenant_id=TENANT_ID,
        name=f"REGTEST-HEALTHFAC-MEMBERSHIP-ENTITY-{suffix}",
        entity_type=SovereignEntityType.ENTERPRISE,
        country_of_origin="EG",
        official_email=f"regtest-healthfac-membership-entity-{suffix}@eppne.com",
        created_by=creator_id,
    )
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return entity


async def _add_membership(db, *, entity_id: int, user_id: int, role: EntityMembershipRole) -> None:
    db.add(EntityMembership(
        entity_type=ENTITY_TYPE, entity_id=entity_id,
        user_id=user_id, tenant_id=TENANT_ID, role=role,
    ))
    await db.commit()


# ============================================================
# 1) create_facility — عضو (OWNER) ينجح، غير عضو يترفض
# ============================================================

@pytest.mark.asyncio
async def test_create_facility_owner_succeeds_non_member_rejected(db):
    owner = await _create_user(db, "p_regtest_healthfacmem_owner")
    outsider = await _create_user(db, "p_regtest_healthfacmem_outsider")
    entity = await _create_sovereign_entity(db, owner.id)
    await _add_membership(db, entity_id=entity.id, user_id=owner.id, role=EntityMembershipRole.OWNER)

    service = HealthService(db)
    facility_ids = []
    try:
        facility = await service.create_facility(owner.id, TENANT_ID, {
            "name": f"REGTEST-HEALTHFAC-OWNER-{_suffix()}",
            "facility_category": FacilityCategory.CLINIC,
            "specialties": ["general"],
            "facility_wallet_address": None,
            "entity_id": entity.id,
        })
        facility_ids.append(facility.id)
        assert facility.entity_id == entity.id

        with pytest.raises(PermissionDeniedError):
            await service.create_facility(outsider.id, TENANT_ID, {
                "name": f"REGTEST-HEALTHFAC-OUTSIDER-{_suffix()}",
                "facility_category": FacilityCategory.CLINIC,
                "specialties": ["general"],
                "facility_wallet_address": None,
                "entity_id": entity.id,
            })
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            if facility_ids:
                await cleanup_db.execute(delete(HealthFacility).where(HealthFacility.id.in_(facility_ids)))
            await cleanup_db.execute(delete(EntityMembership).where(
                EntityMembership.entity_type == ENTITY_TYPE,
                EntityMembership.entity_id == entity.id,
                EntityMembership.user_id == owner.id,
            ))
            await cleanup_db.execute(delete(SovereignEntity).where(SovereignEntity.id == entity.id))
            await cleanup_db.execute(delete(User).where(User.id.in_([owner.id, outsider.id])))
            await cleanup_db.commit()


# ============================================================
# 2) EXECUTIVE_DIRECTOR أيضًا مسموح (نفس insurance/transport/tourism_sports بالحرف)
# ============================================================

@pytest.mark.asyncio
async def test_create_facility_executive_director_succeeds(db):
    director = await _create_user(db, "p_regtest_healthfacmem_director")
    entity = await _create_sovereign_entity(db, director.id)
    await _add_membership(db, entity_id=entity.id, user_id=director.id, role=EntityMembershipRole.EXECUTIVE_DIRECTOR)

    service = HealthService(db)
    facility_ids = []
    try:
        facility = await service.create_facility(director.id, TENANT_ID, {
            "name": f"REGTEST-HEALTHFAC-DIRECTOR-{_suffix()}",
            "facility_category": FacilityCategory.CLINIC,
            "specialties": ["general"],
            "facility_wallet_address": None,
            "entity_id": entity.id,
        })
        facility_ids.append(facility.id)
        assert facility.entity_id == entity.id
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            if facility_ids:
                await cleanup_db.execute(delete(HealthFacility).where(HealthFacility.id.in_(facility_ids)))
            await cleanup_db.execute(delete(EntityMembership).where(
                EntityMembership.entity_type == ENTITY_TYPE,
                EntityMembership.entity_id == entity.id,
                EntityMembership.user_id == director.id,
            ))
            await cleanup_db.execute(delete(SovereignEntity).where(SovereignEntity.id == entity.id))
            await cleanup_db.execute(delete(User).where(User.id == director.id))
            await cleanup_db.commit()


# ============================================================
# 3) حذف الكيان المالك → SET NULL على health_facilities.entity_id
#    (مش CASCADE) — المنشأة throwaway تفضل موجودة
# ============================================================

@pytest.mark.asyncio
async def test_facility_entity_deletion_sets_null_not_cascade(db):
    creator = await _create_user(db, "p_regtest_healthfacmem_setnull_creator")
    entity = await _create_sovereign_entity(db, creator.id)

    repo = HealthRepository(db)
    suffix = _suffix()
    facility = await repo.create_facility(
        tenant_id=TENANT_ID, entity_id=entity.id,
        name=f"REGTEST-HEALTHFAC-{suffix}", facility_category=FacilityCategory.CLINIC,
    )
    facility_id = facility.id

    try:
        # ON DELETE SET NULL بيتنفَّذ جوّه Postgres مباشرة عند الـDELETE —
        # مش عبر الـORM (نفس ملاحظة insurance/transport/tourism_sports gap-fix).
        await db.execute(delete(SovereignEntity).where(SovereignEntity.id == entity.id))
        await db.commit()

        async with AsyncSessionLocal() as verify_db:
            refreshed = (await verify_db.execute(
                select(HealthFacility).where(HealthFacility.id == facility_id)
            )).scalar_one_or_none()
        assert refreshed is not None, "المنشأة لازم تفضل موجودة (SET NULL مش CASCADE)"
        assert refreshed.entity_id is None
    finally:
        await db.execute(delete(HealthFacility).where(HealthFacility.id == facility_id))
        await db.execute(delete(User).where(User.id == creator.id))
        await db.commit()
