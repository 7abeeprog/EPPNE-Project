"""
regression test لجلسة `realestate-hooks-layer-design-decision` (2026-08-31).
تقرير الجلسة: .claude/reports/realestate-design-decision-session-log.md

يتحقق حيًا (DB حقيقية، صفر mock) من `RealEstateService.update_property_unit`
و`delete_property_unit` — أول عملية تعديل/حذف عامة لوحدة عقارية في الدومين
كله، مبنية على نفس نمط فحص الملكية المستخدَم فعليًا في
`tokenize_asset`/`rent_unit` (`_get_land_owner_for_unit`). كل اختبار بمساري
شرعي (المالك الحقيقي) وهجوم (مستخدم غير مالك) — نفس منهجية
`test_realestate_tokenize_asset_ownership_check.py`.
"""
import uuid
from decimal import Decimal
from datetime import datetime

import pytest
from sqlalchemy import delete, select

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.core.errors import PermissionDeniedError, ValidationError

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.realestate.service import RealEstateService
from app.domains.realestate.repository import RealEstateRepository
from app.domains.realestate.models import (
    LandAsset, RealEstateDevelopment, PropertyUnit, PropertyOwnership,
    PropertyType, PropertyStatus, ZoningCategory, LegalStatus,
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


async def _create_owned_unit(db, *, owner_id: int):
    re_repo = RealEstateRepository(db)
    suffix = _suffix()
    land = await re_repo.create_land_asset(
        tenant_id=TENANT_ID, owner_id=owner_id,
        plot_number=f"REGTEST-PLOT-{suffix}", area_sqm=Decimal("500"),
        gps_polygon={"type": "Point", "coordinates": [0, 0]},
        zoning=ZoningCategory.RESIDENTIAL, legal_status=LegalStatus.REGISTERED,
    )
    development = await re_repo.create_development(
        tenant_id=TENANT_ID, land_asset_id=land.id,
        name=f"REGTEST-DEV-{suffix}", development_type="RESIDENTIAL",
    )
    unit = await re_repo.create_unit(
        tenant_id=TENANT_ID, development_id=development.id,
        unit_number=f"REGTEST-UNIT-{suffix}", area_sqm=Decimal("100"),
        property_type=PropertyType.APARTMENT,
        is_available_for_rent=False, is_available_for_sale=False,
        title="عنوان أصلي", status=PropertyStatus.AVAILABLE,
    )
    return unit, development, land


async def _cleanup(*, unit_id, development_id, land_id, user_ids, ownership_id=None):
    async with AsyncSessionLocal() as cleanup_db:
        if ownership_id:
            await cleanup_db.execute(delete(PropertyOwnership).where(PropertyOwnership.id == ownership_id))
        await cleanup_db.execute(delete(PropertyUnit).where(PropertyUnit.id == unit_id))
        await cleanup_db.execute(delete(RealEstateDevelopment).where(RealEstateDevelopment.id == development_id))
        await cleanup_db.execute(delete(LandAsset).where(LandAsset.id == land_id))
        await cleanup_db.execute(delete(User).where(User.id.in_(user_ids)))
        await cleanup_db.commit()


# ============================================================
# updateProperty (#4)
# ============================================================

@pytest.mark.asyncio
async def test_update_property_unit_succeeds_for_real_owner(db):
    real_owner = await _create_user(db, "p_regtest_upd_owner")
    unit, development, land = await _create_owned_unit(db, owner_id=real_owner.id)
    unit_id, development_id, land_id = unit.id, development.id, land.id

    service = RealEstateService(db)
    try:
        updated = await service.update_property_unit(
            unit_id, tenant_id=TENANT_ID, updater_id=real_owner.id,
            data={"title": "عنوان جديد بعد التعديل", "sale_price_mrusdt": Decimal("150000")},
        )
        assert updated.title == "عنوان جديد بعد التعديل"
        assert updated.sale_price_mrusdt == Decimal("150000")

        async with AsyncSessionLocal() as verify_db:
            result = await verify_db.execute(select(PropertyUnit).where(PropertyUnit.id == unit_id))
            saved = result.scalar_one()
            assert saved.title == "عنوان جديد بعد التعديل"
    finally:
        await _cleanup(unit_id=unit_id, development_id=development_id, land_id=land_id, user_ids=[real_owner.id])


@pytest.mark.asyncio
async def test_update_property_unit_rejects_non_owner_with_403(db):
    real_owner = await _create_user(db, "p_regtest_upd_realowner")
    attacker = await _create_user(db, "p_regtest_upd_attacker")
    unit, development, land = await _create_owned_unit(db, owner_id=real_owner.id)
    unit_id, development_id, land_id = unit.id, development.id, land.id

    service = RealEstateService(db)
    try:
        with pytest.raises(PermissionDeniedError, match="ليس لديك صلاحية تعديل هذه الوحدة"):
            await service.update_property_unit(
                unit_id, tenant_id=TENANT_ID, updater_id=attacker.id,
                data={"title": "استولى المهاجم على العنوان"},
            )

        async with AsyncSessionLocal() as verify_db:
            result = await verify_db.execute(select(PropertyUnit).where(PropertyUnit.id == unit_id))
            saved = result.scalar_one()
            assert saved.title == "عنوان أصلي"  # لم يتغيّر
    finally:
        await _cleanup(unit_id=unit_id, development_id=development_id, land_id=land_id,
                        user_ids=[real_owner.id, attacker.id])


# ============================================================
# deleteProperty (#5)
# ============================================================

@pytest.mark.asyncio
async def test_delete_property_unit_succeeds_for_real_owner_with_no_ownerships(db):
    real_owner = await _create_user(db, "p_regtest_del_owner")
    unit, development, land = await _create_owned_unit(db, owner_id=real_owner.id)
    unit_id, development_id, land_id = unit.id, development.id, land.id

    service = RealEstateService(db)
    try:
        await service.delete_property_unit(unit_id, tenant_id=TENANT_ID, deleter_id=real_owner.id)

        async with AsyncSessionLocal() as verify_db:
            result = await verify_db.execute(select(PropertyUnit).where(PropertyUnit.id == unit_id))
            saved = result.scalar_one()
            assert saved.is_deleted is True
            assert saved.deleted_at is not None
    finally:
        await _cleanup(unit_id=unit_id, development_id=development_id, land_id=land_id, user_ids=[real_owner.id])


@pytest.mark.asyncio
async def test_delete_property_unit_rejects_non_owner_with_403(db):
    real_owner = await _create_user(db, "p_regtest_del_realowner")
    attacker = await _create_user(db, "p_regtest_del_attacker")
    unit, development, land = await _create_owned_unit(db, owner_id=real_owner.id)
    unit_id, development_id, land_id = unit.id, development.id, land.id

    service = RealEstateService(db)
    try:
        with pytest.raises(PermissionDeniedError, match="ليس لديك صلاحية حذف هذه الوحدة"):
            await service.delete_property_unit(unit_id, tenant_id=TENANT_ID, deleter_id=attacker.id)

        async with AsyncSessionLocal() as verify_db:
            result = await verify_db.execute(select(PropertyUnit).where(PropertyUnit.id == unit_id))
            saved = result.scalar_one()
            assert saved.is_deleted is False  # لم يُحذف
    finally:
        await _cleanup(unit_id=unit_id, development_id=development_id, land_id=land_id,
                        user_ids=[real_owner.id, attacker.id])


@pytest.mark.asyncio
async def test_delete_property_unit_blocked_when_active_ownership_exists(db):
    real_owner = await _create_user(db, "p_regtest_del_blocked_owner")
    buyer = await _create_user(db, "p_regtest_del_blocked_buyer")
    unit, development, land = await _create_owned_unit(db, owner_id=real_owner.id)
    unit_id, development_id, land_id = unit.id, development.id, land.id

    re_repo = RealEstateRepository(db)
    ownership = await re_repo.create_ownership(
        tenant_id=TENANT_ID, unit_id=unit_id, owner_user_id=buyer.id,
        ownership_percentage=Decimal("30"), acquisition_date=datetime.utcnow(),
    )
    await db.commit()

    service = RealEstateService(db)
    try:
        with pytest.raises(ValidationError, match="لا يمكن حذف وحدة عندها ملكيات جزئية فعّالة"):
            await service.delete_property_unit(unit_id, tenant_id=TENANT_ID, deleter_id=real_owner.id)

        async with AsyncSessionLocal() as verify_db:
            result = await verify_db.execute(select(PropertyUnit).where(PropertyUnit.id == unit_id))
            saved = result.scalar_one()
            assert saved.is_deleted is False  # الحذف اتمنع فعليًا
    finally:
        await _cleanup(unit_id=unit_id, development_id=development_id, land_id=land_id,
                        user_ids=[real_owner.id, buyer.id], ownership_id=ownership.id)
