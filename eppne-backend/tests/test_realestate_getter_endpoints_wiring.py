"""
regression test لجلسة `realestate-hooks-layer-design-decision` (2026-08-31).
تقرير الجلسة: .claude/reports/realestate-design-decision-session-log.md

السياق: 3 دوال كانت مطلوبة من الفرونت إند (`getPropertyOwnerships`,
`getSmartContractStatus`, `getAssetTokenization`) عبر
`hooks/realestate/*.ts` لم يكن لها أي service method أو router endpoint،
رغم أن `RealEstateRepository` كانت تملك الميثودز الجاهزة بالفعل
(`get_ownerships_by_unit`, `get_smart_contract`, `get_tokenization_by_unit`)
بدون أي وصلة. هذا الاختبار يتحقق حيًا (DB حقيقية، صفر mock) من الوصلات
الجديدة الثلاث المضافة في `service.py`:
`get_unit_ownerships`, `get_asset_tokenization`, `get_smart_contract_status`.
"""
import uuid
from decimal import Decimal
from datetime import datetime

import pytest
from sqlalchemy import delete

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels
from app.core.database import AsyncSessionLocal
from app.core.errors import NotFoundError

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.realestate.service import RealEstateService
from app.domains.realestate.repository import RealEstateRepository
from app.domains.realestate.models import (
    LandAsset, RealEstateDevelopment, PropertyUnit, PropertyOwnership,
    AssetTokenization, SmartContractEngine, PropertyType, ZoningCategory,
    LegalStatus, ContractType,
)

TENANT_ID = 1
OTHER_TENANT_ID = 2


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


async def _create_unit(db, *, owner_id: int, tenant_id: int = TENANT_ID):
    re_repo = RealEstateRepository(db)
    suffix = _suffix()
    land = await re_repo.create_land_asset(
        tenant_id=tenant_id, owner_id=owner_id,
        plot_number=f"REGTEST-PLOT-{suffix}", area_sqm=Decimal("500"),
        gps_polygon={"type": "Point", "coordinates": [0, 0]},
        zoning=ZoningCategory.RESIDENTIAL, legal_status=LegalStatus.REGISTERED,
    )
    development = await re_repo.create_development(
        tenant_id=tenant_id, land_asset_id=land.id,
        name=f"REGTEST-DEV-{suffix}", development_type="RESIDENTIAL",
    )
    unit = await re_repo.create_unit(
        tenant_id=tenant_id, development_id=development.id,
        unit_number=f"REGTEST-UNIT-{suffix}", area_sqm=Decimal("100"),
        property_type=PropertyType.APARTMENT,
        is_available_for_rent=False, is_available_for_sale=False,
    )
    return unit, development, land


async def _cleanup(*, unit_id, development_id, land_id, user_ids,
                    ownership_id=None, tokenization_id=None, contract_id=None):
    async with AsyncSessionLocal() as cleanup_db:
        if ownership_id:
            await cleanup_db.execute(delete(PropertyOwnership).where(PropertyOwnership.id == ownership_id))
        if tokenization_id:
            await cleanup_db.execute(delete(AssetTokenization).where(AssetTokenization.id == tokenization_id))
        if contract_id:
            await cleanup_db.execute(delete(SmartContractEngine).where(SmartContractEngine.id == contract_id))
        await cleanup_db.execute(delete(PropertyUnit).where(PropertyUnit.id == unit_id))
        await cleanup_db.execute(delete(RealEstateDevelopment).where(RealEstateDevelopment.id == development_id))
        await cleanup_db.execute(delete(LandAsset).where(LandAsset.id == land_id))
        await cleanup_db.execute(delete(User).where(User.id.in_(user_ids)))
        await cleanup_db.commit()


# ============================================================
# 1) get_unit_ownerships
# ============================================================

@pytest.mark.asyncio
async def test_get_unit_ownerships_returns_real_records(db):
    owner = await _create_user(db, "p_regtest_getown_owner")
    buyer = await _create_user(db, "p_regtest_getown_buyer")
    unit, development, land = await _create_unit(db, owner_id=owner.id)
    unit_id, development_id, land_id = unit.id, development.id, land.id

    re_repo = RealEstateRepository(db)
    ownership = await re_repo.create_ownership(
        tenant_id=TENANT_ID, unit_id=unit_id, owner_user_id=buyer.id,
        ownership_percentage=Decimal("25"), acquisition_date=datetime.utcnow(),
    )
    await db.commit()

    service = RealEstateService(db)
    try:
        result = await service.get_unit_ownerships(unit_id, tenant_id=TENANT_ID)
        assert len(result) == 1
        assert result[0].id == ownership.id
        assert result[0].owner_user_id == buyer.id
        assert result[0].ownership_percentage == Decimal("25")

        # تحقق حي إضافي: tenant_id غلط → NotFoundError (الوحدة موجودة لكن بمستأجر آخر)
        with pytest.raises(NotFoundError):
            await service.get_unit_ownerships(unit_id, tenant_id=OTHER_TENANT_ID)
    finally:
        await _cleanup(
            unit_id=unit_id, development_id=development_id, land_id=land_id,
            user_ids=[owner.id, buyer.id], ownership_id=ownership.id,
        )


# ============================================================
# 2) get_asset_tokenization
# ============================================================

@pytest.mark.asyncio
async def test_get_asset_tokenization_none_then_real_record(db):
    owner = await _create_user(db, "p_regtest_gettok_owner")
    unit, development, land = await _create_unit(db, owner_id=owner.id)
    unit_id, development_id, land_id = unit.id, development.id, land.id

    service = RealEstateService(db)
    tokenization_id = None
    try:
        # قبل أي تجزئة: None وليس خطأ (نفس منطق الفرونت إند: "غير مجزأ حاليًا")
        result_before = await service.get_asset_tokenization(unit_id, tenant_id=TENANT_ID)
        assert result_before is None

        re_repo = RealEstateRepository(db)
        tokenization = await re_repo.create_tokenization(
            tenant_id=TENANT_ID, unit_id=unit_id, total_shares=500,
            share_price_mrusdt=Decimal("2.5"), minimum_investment_shares=1,
            token_symbol=f"REGTEST-{unit_id}",
        )
        tokenization_id = tokenization.id

        result_after = await service.get_asset_tokenization(unit_id, tenant_id=TENANT_ID)
        assert result_after is not None
        assert result_after.id == tokenization.id
        assert result_after.total_shares == 500
    finally:
        await _cleanup(
            unit_id=unit_id, development_id=development_id, land_id=land_id,
            user_ids=[owner.id], tokenization_id=tokenization_id,
        )


# ============================================================
# 3) get_smart_contract_status
# ============================================================

@pytest.mark.asyncio
async def test_get_smart_contract_status_real_record_and_not_found(db):
    re_repo = RealEstateRepository(db)
    contract = await re_repo.create_smart_contract(
        tenant_id=TENANT_ID, contract_type=ContractType.SALE, reference_id=1,
        contract_metadata={"note": "regtest"}, blockchain_tx_hash=None,
        execution_status="PENDING", executed_at=None,
    )
    contract_id = contract.id

    service = RealEstateService(db)
    try:
        result = await service.get_smart_contract_status(contract_id, tenant_id=TENANT_ID)
        assert result.id == contract_id
        assert result.execution_status == "PENDING"

        # معرف غير موجود → NotFoundError
        with pytest.raises(NotFoundError):
            await service.get_smart_contract_status(999_999_999, tenant_id=TENANT_ID)

        # نفس المعرف لكن tenant_id غلط → NotFoundError (تأكيد الـtenant scoping)
        with pytest.raises(NotFoundError):
            await service.get_smart_contract_status(contract_id, tenant_id=OTHER_TENANT_ID)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(SmartContractEngine).where(SmartContractEngine.id == contract_id))
            await cleanup_db.commit()
