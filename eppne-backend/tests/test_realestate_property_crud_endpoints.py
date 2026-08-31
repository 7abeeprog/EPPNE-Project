"""
regression test لجلسة `realestate-hooks-layer-design-decision` (2026-08-31).
تقرير الجلسة: .claude/reports/realestate-design-decision-session-log.md

يتحقق حيًا (DB حقيقية، صفر mock) من:
- migration `043_add_marketing_fields_to_property_units` (الأعمدة التسويقية
  الخمسة + عمود `status` كـEnum جديد `propertystatus`).
- `RealEstateService.create_property_unit` بالحقول التسويقية الجديدة
  (تدفّق تلقائي عبر `data.model_dump()` الموجود بالفعل — صفر تعديل على
  الدالة نفسها).
- `RealEstateService.list_property_units` (الوصلة الجديدة لـ#1 `getProperties`).
- `RealEstateService.get_property_unit` (الوصلة الجديدة لـ#2 `getProperty`).
"""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import delete

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.core.errors import NotFoundError

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.realestate.service import RealEstateService
from app.domains.realestate.repository import RealEstateRepository
from app.domains.realestate.models import (
    LandAsset, RealEstateDevelopment, PropertyUnit, PropertyType,
    PropertyStatus, ZoningCategory, LegalStatus,
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


async def _create_land_and_dev(db, *, owner_id: int, tenant_id: int = TENANT_ID):
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
    return development, land


async def _cleanup(*, unit_ids, development_id, land_id, user_ids):
    async with AsyncSessionLocal() as cleanup_db:
        await cleanup_db.execute(delete(PropertyUnit).where(PropertyUnit.id.in_(unit_ids)))
        await cleanup_db.execute(delete(RealEstateDevelopment).where(RealEstateDevelopment.id == development_id))
        await cleanup_db.execute(delete(LandAsset).where(LandAsset.id == land_id))
        await cleanup_db.execute(delete(User).where(User.id.in_(user_ids)))
        await cleanup_db.commit()


@pytest.mark.asyncio
async def test_create_property_unit_with_marketing_fields_and_default_status(db, monkeypatch):
    """#3 createProperty: تأكيد إن الحقول التسويقية الجديدة بتتخزن فعليًا
    عبر نفس الدالة الموجودة (create_property_unit)، وإن status الافتراضي
    AVAILABLE بيتطبّق تلقائيًا لو الـcaller ما بعتوش."""
    async def _skip_saas_check(self, tenant_id, feature="real_estate"):
        return None
    monkeypatch.setattr(RealEstateService, "_check_saas_limits", _skip_saas_check)

    owner = await _create_user(db, "p_regtest_propcrud_owner")
    development, land = await _create_land_and_dev(db, owner_id=owner.id)
    unit_ids = []
    try:
        service = RealEstateService(db)
        unit = await service.create_property_unit(
            tenant_id=TENANT_ID,
            data={
                "development_id": development.id,
                "unit_number": f"REGTEST-U-{_suffix()}",
                "area_sqm": Decimal("80"),
                "property_type": PropertyType.APARTMENT,
                "title": "شقة تجريبية مطلة على البحر",
                "description": "وصف تجريبي throwaway",
                "location": "الإسكندرية",
                "cover_image_url": "https://example.com/cover.jpg",
            },
        )
        unit_ids.append(unit.id)

        async with AsyncSessionLocal() as verify_db:
            from sqlalchemy import select
            result = await verify_db.execute(select(PropertyUnit).where(PropertyUnit.id == unit.id))
            saved = result.scalar_one()
            assert saved.title == "شقة تجريبية مطلة على البحر"
            assert saved.location == "الإسكندرية"
            assert saved.status == PropertyStatus.AVAILABLE  # الافتراضي بدون تمرير صريح
    finally:
        await _cleanup(unit_ids=unit_ids, development_id=development.id, land_id=land.id, user_ids=[owner.id])


@pytest.mark.asyncio
async def test_list_and_get_property_unit_live(db, monkeypatch):
    """#1 getProperties + #2 getProperty: قائمة عامة (بدون فرض for_sale)
    + جلب فردي بالمعرف، مع تحقق tenant scoping فعلي على get_property_unit."""
    async def _skip_saas_check(self, tenant_id, feature="real_estate"):
        return None
    monkeypatch.setattr(RealEstateService, "_check_saas_limits", _skip_saas_check)

    owner = await _create_user(db, "p_regtest_propcrud_list_owner")
    development, land = await _create_land_and_dev(db, owner_id=owner.id)
    unit_ids = []
    try:
        service = RealEstateService(db)
        # وحدة غير متاحة للبيع ولا للإيجار عمدًا — list_units_for_sale الحالية
        # ما كانتش هتجيبها، list_property_units الجديدة لازم تجيبها لأنها عامة
        unit = await service.create_property_unit(
            tenant_id=TENANT_ID,
            data={
                "development_id": development.id,
                "unit_number": f"REGTEST-U-{_suffix()}",
                "area_sqm": Decimal("60"),
                "property_type": PropertyType.OFFICE,
                "is_available_for_sale": False,
                "is_available_for_rent": False,
            },
        )
        unit_ids.append(unit.id)

        units = await service.list_property_units(TENANT_ID, development_id=development.id)
        assert any(u.id == unit.id for u in units)

        # فلترة حسب property_type
        office_units = await service.list_property_units(TENANT_ID, property_type=PropertyType.OFFICE, development_id=development.id)
        assert any(u.id == unit.id for u in office_units)
        apartment_units = await service.list_property_units(TENANT_ID, property_type=PropertyType.APARTMENT, development_id=development.id)
        assert not any(u.id == unit.id for u in apartment_units)

        fetched = await service.get_property_unit(unit.id, tenant_id=TENANT_ID)
        assert fetched.id == unit.id

        with pytest.raises(NotFoundError):
            await service.get_property_unit(unit.id, tenant_id=OTHER_TENANT_ID)
    finally:
        await _cleanup(unit_ids=unit_ids, development_id=development.id, land_id=land.id, user_ids=[owner.id])
