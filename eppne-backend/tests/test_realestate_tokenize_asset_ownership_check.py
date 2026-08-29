"""
regression test لجلسة `realestate-buyfraction-amount-trust-check` (اكتشاف
جانبي #2 من التقرير الأصلي).
تقرير الجلسة: .claude/reports/realestate-buyfraction-amount-trust-check-session-log.md

السبب الجذري (كان): `RealEstateService.tokenize_asset()` كانت بتقبل
`unit_id` وتنشئ `AssetTokenization` (بسعر سهم يحدده الـcaller بالكامل عبر
`share_price_mrusdt`) من غير أي تحقق إن الـcaller فعلاً مالك الوحدة (عبر
سلسلة unit → development → land_asset → owner_id). الراوتر
(`router.py`) كمان ما كانش بيمرر current_user.id للسيرفس أصلًا. أي
مستخدم authenticated كان يقدر يعمل tokenize لأي unit_id بأي سعر سهم.

الإصلاح: أضيف باراميتر `initiator_id` لـ`tokenize_asset` (يتمرر من
الراوتر كـ`current_user.id`)، وتحقق ownership صريح جوه السيرفس — بنفس
النمط المستخدَم في `buy_fractional_ownership`/`rent_unit` (استدعاء
`_get_land_owner_for_unit` ومقارنة `owner.id` بـ`initiator_id`). لو
المقارنة فشلت: `PermissionDeniedError` (→ 403)، صفر إنشاء لأي
AssetTokenization.
"""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import delete, select

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels
from app.core.database import AsyncSessionLocal
from app.core.errors import PermissionDeniedError

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.realestate.service import RealEstateService
from app.domains.realestate.repository import RealEstateRepository
from app.domains.realestate.models import (
    LandAsset, RealEstateDevelopment, PropertyUnit, AssetTokenization,
    PropertyType, ZoningCategory, LegalStatus,
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
    )
    return unit, development, land


async def _cleanup(unit_id, development_id, land_id, user_ids):
    async with AsyncSessionLocal() as cleanup_db:
        await cleanup_db.execute(delete(AssetTokenization).where(AssetTokenization.unit_id == unit_id))
        await cleanup_db.execute(delete(PropertyUnit).where(PropertyUnit.id == unit_id))
        await cleanup_db.execute(delete(RealEstateDevelopment).where(RealEstateDevelopment.id == development_id))
        await cleanup_db.execute(delete(LandAsset).where(LandAsset.id == land_id))
        await cleanup_db.execute(delete(User).where(User.id.in_(user_ids)))
        await cleanup_db.commit()


# ============================================================
# 1) المسار الشرعي — المالك الحقيقي بيعمل tokenize لوحدته → لازم ينجح
# ============================================================

@pytest.mark.asyncio
async def test_tokenize_asset_succeeds_for_real_owner(db, monkeypatch):
    """ملاحظة: بنعمل monkeypatch لـ`_check_saas_limits` هنا فقط عشان نتجاوز
    بوابة SaaS مسبقة ومنفصلة تمامًا عن هذا الإصلاح — خطة الاشتراك الحالية
    لـtenant_id=1 (throwaway/regtest) ما فيهاش feature
    "real_estate_tokenization" مفعّلة، فأي استدعاء حقيقي لـtokenize_asset
    (سواء من المالك أو من مهاجم) كان هيترفض من بوابة الـSaaS **قبل** ما
    يوصل لتحقق الـownership أصلًا — ده كان هيخلي اختبار الهجوم false
    positive (بينجح لسبب غلط: بوابة SaaS، مش الإصلاح الفعلي). صفر لمس على
    saas/service.py أو بيانات الاشتراك؛ الـmonkeypatch بيعزل تحقق
    الـownership بس عشان نتأكد إنه هو اللي بيحدد النتيجة فعليًا."""
    async def _skip_saas_check(self, tenant_id, feature="real_estate"):
        return None

    monkeypatch.setattr(RealEstateService, "_check_saas_limits", _skip_saas_check)

    real_owner = await _create_user(db, "p_regtest_tokow_owner")
    unit, development, land = await _create_owned_unit(db, owner_id=real_owner.id)
    unit_id, development_id, land_id = unit.id, development.id, land.id
    user_ids = [real_owner.id]

    service = RealEstateService(db)
    try:
        tokenization = await service.tokenize_asset(
            tenant_id=TENANT_ID, unit_id=unit_id,
            total_shares=1000, share_price=Decimal("10"),
            initiator_id=real_owner.id,
        )
        assert tokenization is not None
        assert tokenization.unit_id == unit_id

        # تأكيد مستقل من الـDB — التجزئة فعلاً اتسجلت
        async with AsyncSessionLocal() as verify_db:
            result = await verify_db.execute(
                select(AssetTokenization).where(AssetTokenization.id == tokenization.id)
            )
            saved = result.scalar_one()
            assert saved.unit_id == unit_id
            assert saved.total_shares == 1000
    finally:
        await _cleanup(unit_id, development_id, land_id, user_ids)


# ============================================================
# 2) مسار الهجوم — مستخدم تاني بيحاول يعمل tokenize لوحدة مش بتاعته
#    → لازم يترفض بـPermissionDeniedError (403)، مش يعدي بصمت
# ============================================================

@pytest.mark.asyncio
async def test_tokenize_asset_rejects_non_owner_with_403(db, monkeypatch):
    """نفس الـmonkeypatch لـ`_check_saas_limits` من الاختبار أعلاه، وبنفس
    السبب: بدونه، بوابة الـSaaS كانت هترفض الطلب **قبل** ما يوصل لتحقق
    الـownership، فالاختبار كان هينجح لسبب غلط (false positive). هنا كمان
    بنتأكد من *نص* رسالة الاستثناء عشان نضمن إن الرفض جاي فعليًا من تحقق
    الـownership الجديد ("ليس لديك صلاحية تجزئة هذه الوحدة")، مش من أي
    بوابة تانية."""
    async def _skip_saas_check(self, tenant_id, feature="real_estate"):
        return None

    monkeypatch.setattr(RealEstateService, "_check_saas_limits", _skip_saas_check)

    real_owner = await _create_user(db, "p_regtest_tokow_realowner")
    attacker = await _create_user(db, "p_regtest_tokow_attacker")
    unit, development, land = await _create_owned_unit(db, owner_id=real_owner.id)
    unit_id, development_id, land_id = unit.id, development.id, land.id
    user_ids = [real_owner.id, attacker.id]

    service = RealEstateService(db)
    try:
        with pytest.raises(PermissionDeniedError, match="ليس لديك صلاحية تجزئة هذه الوحدة"):
            await service.tokenize_asset(
                tenant_id=TENANT_ID, unit_id=unit_id,
                total_shares=1_000_000, share_price=Decimal("0.01"),
                initiator_id=attacker.id,
            )

        # تأكيد مستقل من الـDB — مفيش أي AssetTokenization اتسجلت للمهاجم
        async with AsyncSessionLocal() as verify_db:
            result = await verify_db.execute(
                select(AssetTokenization).where(AssetTokenization.unit_id == unit_id)
            )
            assert result.scalar_one_or_none() is None
    finally:
        await _cleanup(unit_id, development_id, land_id, user_ids)
