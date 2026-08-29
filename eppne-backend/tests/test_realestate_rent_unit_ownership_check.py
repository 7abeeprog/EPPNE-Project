"""
regression test لجلسة `realestate-buyfraction-amount-trust-check` (اكتشاف
جانبي #1 من التقرير الأصلي).
تقرير الجلسة: .claude/reports/realestate-buyfraction-amount-trust-check-session-log.md

السبب الجذري (كان): `RealEstateService.rent_unit()` كانت بتقبل `landlord_id`
مباشرة من `current_user` اللي بيستدعي `POST /realestate/rentals`، من غير أي
تحقق إن المستخدم ده فعلاً مالك الوحدة (عبر سلسلة unit → development →
land_asset → owner_id). أي مستخدم authenticated كان يقدر يأجّر أي unit_id،
ينصب نفسه landlord، ويحدد monthly_rent_mrusdt كيفما شاء — وده كان بيولّد
invoice حقيقي ضد tenant_user_id.

الإصلاح: أضيف تحقق ownership صريح في `rent_unit` (service.py) بعد جلب
الـunit ومباشرة قبل إنشاء العقد — بنفس النمط المستخدَم بالفعل في
`buy_fractional_ownership` (استدعاء `_get_land_owner_for_unit` ومقارنة
`owner.id` بـ`landlord_id`). لو المقارنة فشلت: `PermissionDeniedError`
(→ 403)، صفر إنشاء لأي RentalContract.
"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import delete, select

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels
from app.core.database import AsyncSessionLocal
from app.core.errors import PermissionDeniedError

from app.domains.invoicing.service import InvoicingService
from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User
from app.domains.identity.repository import WalletRepository

from app.domains.realestate.service import RealEstateService
from app.domains.realestate.repository import RealEstateRepository
from app.domains.realestate.models import (
    LandAsset, RealEstateDevelopment, PropertyUnit, RentalContract,
    PropertyType, ZoningCategory, LegalStatus,
)
from app.domains.invoicing.models import Invoice

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


async def _create_owned_unit(db, *, owner_id: int) -> PropertyUnit:
    """يبني سلسلة land_asset(owner_id=owner_id) → development → unit جديدة
    بالكامل، عشان نتحكم بدقة في مين "المالك الفعلي" لكل اختبار."""
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
        is_available_for_rent=True, is_available_for_sale=False,
    )
    return unit, development, land


async def _cleanup(unit_id, development_id, land_id, user_ids):
    async with AsyncSessionLocal() as cleanup_db:
        await cleanup_db.execute(delete(RentalContract).where(RentalContract.unit_id == unit_id))
        await cleanup_db.execute(delete(PropertyUnit).where(PropertyUnit.id == unit_id))
        await cleanup_db.execute(delete(RealEstateDevelopment).where(RealEstateDevelopment.id == development_id))
        await cleanup_db.execute(delete(LandAsset).where(LandAsset.id == land_id))
        await cleanup_db.execute(delete(Invoice).where(Invoice.user_id.in_(user_ids)))
        await cleanup_db.execute(delete(User).where(User.id.in_(user_ids)))
        await cleanup_db.commit()


# ============================================================
# 1) المسار الشرعي — المالك الحقيقي بيأجّر وحدته → لازم ينجح
# ============================================================

@pytest.mark.asyncio
async def test_rent_unit_succeeds_for_real_owner(db, monkeypatch):
    """ملاحظة: بنعمل monkeypatch لـ`_generate_invoice_number` هنا فقط عشان
    نتجنب بج مسبق موثَّق تمامًا ومنفصل عن هذا الإصلاح
    (`invoicing-generate-invoice-number-count-based-collision`، موثَّق في
    test_realestate_insurance_savepoint.py) — بيمنع أي `create_invoice()`
    حقيقي لـtenant_id=1 حاليًا بتصادم unique constraint. صفر لمس على
    invoicing/service.py؛ الـmonkeypatch هنا بيولّد رقم فاتورة فريد بس،
    مش بيغيّر أي منطق تحت الاختبار (rent_unit نفسها، بما فيها تحقق
    الـownership الجديد، بتتنفذ حقيقي 100% بلا أي stub)."""
    async def _unique_invoice_number(self, tenant_id):
        return f"INV-REGTEST-RENTOW-{_suffix()}"

    monkeypatch.setattr(InvoicingService, "_generate_invoice_number", _unique_invoice_number)

    real_owner = await _create_user(db, "p_regtest_rentow_owner")
    tenant_user = await _create_user(db, "p_regtest_rentow_tenant")
    unit, development, land = await _create_owned_unit(db, owner_id=real_owner.id)
    unit_id, development_id, land_id = unit.id, development.id, land.id
    user_ids = [real_owner.id, tenant_user.id]

    service = RealEstateService(db)
    try:
        contract = await service.rent_unit(
            landlord_id=real_owner.id, tenant_id=TENANT_ID, unit_id=unit_id,
            tenant_user_id=tenant_user.id, monthly_rent=Decimal("50"),
            start_date=datetime.utcnow(), end_date=datetime.utcnow() + timedelta(days=365),
            idempotency_key=f"REGTEST-RENTOW-OK-{_suffix()}",
        )
        assert contract is not None
        assert contract.landlord_user_id == real_owner.id
        assert contract.unit_id == unit_id

        # تأكيد مستقل من الـDB — العقد فعلاً اتسجل
        async with AsyncSessionLocal() as verify_db:
            result = await verify_db.execute(
                select(RentalContract).where(RentalContract.id == contract.id)
            )
            saved = result.scalar_one()
            assert saved.landlord_user_id == real_owner.id
    finally:
        await _cleanup(unit_id, development_id, land_id, user_ids)


# ============================================================
# 2) مسار الهجوم — مستخدم تاني بيحاول يأجّر وحدة مش بتاعته → لازم يترفض
#    بـPermissionDeniedError (403)، مش يعدي بصمت
# ============================================================

@pytest.mark.asyncio
async def test_rent_unit_rejects_non_owner_with_403(db):
    real_owner = await _create_user(db, "p_regtest_rentow_realowner")
    attacker = await _create_user(db, "p_regtest_rentow_attacker")
    tenant_user = await _create_user(db, "p_regtest_rentow_victimtenant")
    unit, development, land = await _create_owned_unit(db, owner_id=real_owner.id)
    unit_id, development_id, land_id = unit.id, development.id, land.id
    user_ids = [real_owner.id, attacker.id, tenant_user.id]

    service = RealEstateService(db)
    try:
        with pytest.raises(PermissionDeniedError):
            await service.rent_unit(
                landlord_id=attacker.id, tenant_id=TENANT_ID, unit_id=unit_id,
                tenant_user_id=tenant_user.id, monthly_rent=Decimal("999999"),
                start_date=datetime.utcnow(), end_date=datetime.utcnow() + timedelta(days=365),
                idempotency_key=f"REGTEST-RENTOW-ATTACK-{_suffix()}",
            )

        # تأكيد مستقل من الـDB — مفيش أي RentalContract اتسجل للمهاجم
        async with AsyncSessionLocal() as verify_db:
            result = await verify_db.execute(
                select(RentalContract).where(
                    RentalContract.unit_id == unit_id,
                    RentalContract.landlord_user_id == attacker.id,
                )
            )
            assert result.scalar_one_or_none() is None
    finally:
        await _cleanup(unit_id, development_id, land_id, user_ids)
