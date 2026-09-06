"""
Phase 9 (رسمية) — جلسة `referral-affiliate-unified-system-implementation`.
تقرير الجلسة الكامل (تصميم + تنفيذ Phases 0-8 + كل قرار):
.claude/reports/referral-affiliate-unified-implementation-session-log.md
.claude/reports/referral-affiliate-unified-implementation-phase0-execution-session-log.md

يغطي 5 سيناريوهات معتمدة صراحة من المستخدم:
1. الأساسي: referrer -> referred -> عمولة (مستوى 1) عبر
   `distribute_commissions_for_sale_event` مباشرة.
2. سلة commerce بمنتجات من نطاقين مختلفين في نفس الطلب — تأكيد تقسيم
   العمولة حسب نطاق كل منتج (قرار معتمد صراحة) عبر
   `distribute_commissions_for_order`.
3. تفعيل affiliate كخدمة SaaS — Phase 7 hook
   (`SaaSControlService._activate_affiliate_default_scope_if_needed`)
   مُختبَر مباشرة (Option 3 المعتمد من المستخدم — بدون لمس
   `get_plan_by_id` المكسورة بباج منفصل تمامًا، راجع
   .claude/reports/saas-get-plan-by-id-security-tradeoff-note.md).
   الاشتراك يُزرع مباشرة عبر SaaSRepository (نفس نمط
   test_saas_cancel_subscription_silent_write.py الموجود).
4. عينة من الـ12 دومين: zamakana (المرجع القياسي) + digital_twin
   (حالة خاصة — تمرير affiliate_code مباشرة بلا referred_by_user_id
   مُسجَّل مسبقًا).
5. حالة عدم تفعيل SaaS للـtenant (scope_id يرجع None) — تأكيد التخطي
   الصامت الآمن بلا كسر العملية الأساسية ولا استثناء غير متوقَّع.

منهجية التحقق (بنفس معيار test_saas_cancel_subscription_silent_write.py
وtest_entity_membership_foundation.py): كل تأكيد نهائي عبر
`AsyncSessionLocal()` مستقلة تمامًا، ليس نفس الـsession اللي نفَّذت
العملية — لأن SELECT داخل نفس الترانزاكشن ممكن يشوف كتابة flush()-only
معلَّقة حتى لو الـcommit() ناقص فعليًا في مكان ما.

تنظيف throwaway مؤكَّد بـCOUNT(*)=0 بعد كل اختبار (try/finally).
"""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select, delete, func

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash

from app.domains.identity.models import User
from app.domains.academy.models import AcademyTenant
from app.domains.affiliate.service import AffiliateService
from app.domains.affiliate.repository import AffiliateRepository
from app.domains.affiliate.models import (
    AffiliateScope,
    AffiliateScopeMember,
    ReferralTree,
    Commission,
    CommissionTier,
    AffiliateProfile,
)
from app.domains.commerce.models import StoreProfile, Product, Order, OrderItem
from app.domains.saas.service import SaaSControlService
from app.domains.saas.repository import SaaSRepository
from app.domains.zamakana.service import ZamakanaService
from app.domains.digital_twin.service import DigitalTwinService

TENANT_ID = 16  # throwaway tenant موجود بالفعل، عنده اشتراك ACTIVE سابق
                # على خدمة affiliate (اكتُشف في Phase 0 من هذه الجلسة)


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, tenant_id: int, prefix: str) -> User:
    suffix = _suffix()
    user = User(
        tenant_id=tenant_id,
        username=f"{prefix}_{suffix}",
        email=f"{prefix}_{suffix}@test.local",
        hashed_password=get_password_hash("Throwaway123!"),
    )
    db.add(user)
    await db.flush()
    return user


async def _cleanup_users(db, user_ids: list[int]) -> None:
    """يحذف المستخدمين — الـCASCADE على affiliate_profiles.user_id,
    referral_trees.referrer_id/referred_id, affiliate_commissions.user_id
    ينظّف كل البيانات المرتبطة تلقائيًا."""
    if not user_ids:
        return
    await db.execute(delete(User).where(User.id.in_(user_ids)))
    await db.commit()


async def _cleanup_scopes(db, scope_ids: list[int]) -> None:
    """لازم تُستدعى بعد _cleanup_users (Commission.scope_id هو RESTRICT،
    لازم العمولات المرتبطة تتحذف أولًا عبر cascade حذف اليوزرز)."""
    if not scope_ids:
        return
    await db.execute(delete(AffiliateScope).where(AffiliateScope.id.in_(scope_ids)))
    await db.commit()


async def _independent_count(model, **filters) -> int:
    async with AsyncSessionLocal() as independent_db:
        query = select(func.count()).select_from(model)
        for col, val in filters.items():
            query = query.where(getattr(model, col) == val)
        result = await independent_db.execute(query)
        return result.scalar() or 0


# ============================================================
# سيناريو 1: الأساسي — referrer -> referred -> عمولة مستوى 1
# ============================================================

@pytest.mark.asyncio
async def test_basic_referral_creates_level1_commission(db):
    affiliate = AffiliateService(db, TENANT_ID)
    repo = AffiliateRepository(db)

    referrer = await _create_user(db, TENANT_ID, "p9_basic_ref")
    referred = await _create_user(db, TENANT_ID, "p9_basic_red")
    referred.referred_by_user_id = referrer.id
    await db.flush()

    try:
        scope_id = await affiliate.get_default_scope_id()
        assert scope_id is not None, (
            "tenant_id=16 المفروض عنده ENTITY_WIDE scope بالفعل من Phase 0 "
            "— لو رجعت None يبقى تنظيف قديم مسح الـscope بالغلط"
        )

        tiers = await repo.get_commission_tiers(TENANT_ID)
        assert tiers is not None, "tenant_id=16 المفروض عنده CommissionTier GLOBAL افتراضي بالفعل"
        expected_rate = tiers.level_1_pct

        profile = await affiliate.get_or_create_profile(referrer.id)
        assert profile.is_active is True

        tree, created = await affiliate.ensure_referral_link(referrer.id, referred.id, scope_id)
        assert created is True
        assert tree is not None
        assert tree.depth == 1

        # ensure_referral_link idempotent — نداء تاني ميعملش صف جديد
        tree2, created2 = await affiliate.ensure_referral_link(referrer.id, referred.id, scope_id)
        assert created2 is False
        assert tree2.id == tree.id

        commissions = await affiliate.distribute_commissions_for_sale_event(
            referred_user_id=referred.id,
            scope_id=scope_id,
            sale_amount=Decimal("100.00"),
            source_type="TEST_P9_BASIC",
        )

        assert len(commissions) == 1
        c = commissions[0]
        assert c.referral_level == 1
        assert c.scope_id == scope_id
        assert c.source_type == "TEST_P9_BASIC"
        assert c.commission_amount == (Decimal("100.00") * expected_rate / Decimal(100))

        # تحقق مستقل — نفس فلسفة test_saas_cancel_subscription_silent_write.py
        async with AsyncSessionLocal() as independent_db:
            row = (await independent_db.execute(
                select(Commission).where(Commission.id == c.id)
            )).scalar_one_or_none()
            assert row is not None
            assert row.source_type == "TEST_P9_BASIC"
            assert row.scope_id == scope_id

            tree_row = (await independent_db.execute(
                select(ReferralTree).where(ReferralTree.id == tree.id)
            )).scalar_one_or_none()
            assert tree_row is not None
            assert tree_row.entity_type == "SCOPE"
            assert tree_row.entity_id == scope_id
    finally:
        await _cleanup_users(db, [referrer.id, referred.id])
        assert await _independent_count(Commission, user_id=referrer.id) == 0
        assert await _independent_count(ReferralTree, referrer_id=referrer.id) == 0
        assert await _independent_count(AffiliateProfile, user_id=referrer.id) == 0


# ============================================================
# سيناريو 2: سلة بمنتجات من نطاقين مختلفين — تقسيم العمولة حسب النطاق
# ============================================================

@pytest.mark.asyncio
async def test_mixed_cart_splits_commission_by_product_scope(db):
    affiliate = AffiliateService(db, TENANT_ID)
    repo = AffiliateRepository(db)
    suffix = _suffix()

    referrer = await _create_user(db, TENANT_ID, "p9_mix_ref")
    referred = await _create_user(db, TENANT_ID, "p9_mix_red")
    referred.referred_by_user_id = referrer.id
    await db.flush()

    store = StoreProfile(tenant_id=TENANT_ID, name=f"P9-STORE-{suffix}", is_active=True)
    db.add(store)
    await db.flush()

    product_a = Product(
        store_id=store.id, title=f"P9-A-{suffix}", product_type="DIGITAL",
        base_price_mrusdt=Decimal("100.00"),
    )
    product_b = Product(
        store_id=store.id, title=f"P9-B-{suffix}", product_type="DIGITAL",
        base_price_mrusdt=Decimal("50.00"),
    )
    db.add_all([product_a, product_b])
    await db.flush()

    scope_ids: list[int] = []
    try:
        # نطاقان منفصلان بنسب مختلفة تمامًا (20% مقابل 5%) لتمييز أي
        # تسرّب/خلط بين النطاقين في الاختبار بوضوح
        scope_a = await affiliate.create_scope(name=f"P9 Scope A {suffix}", scope_type="SINGLE_PRODUCT")
        scope_b = await affiliate.create_scope(name=f"P9 Scope B {suffix}", scope_type="SINGLE_PRODUCT")
        scope_ids = [scope_a.id, scope_b.id]

        await affiliate.add_scope_member(scope_a.id, "PRODUCT", product_a.id)
        await affiliate.add_scope_member(scope_b.id, "PRODUCT", product_b.id)

        await repo.create_commission_tier(
            tenant_id=TENANT_ID, entity_type="SCOPE", target_scope_id=scope_a.id,
            level_1_pct=Decimal("20.0"),
        )
        await repo.create_commission_tier(
            tenant_id=TENANT_ID, entity_type="SCOPE", target_scope_id=scope_b.id,
            level_1_pct=Decimal("5.0"),
        )

        order = Order(
            store_id=store.id, customer_id=referred.id, tenant_id=TENANT_ID,
            total_amount_mrusdt=Decimal("150.00"), status="PAID",
            idempotency_key=f"p9-mix-order-{suffix}",
        )
        db.add(order)
        await db.flush()

        item_a = OrderItem(
            order_id=order.id, product_id=product_a.id,
            quantity=1, unit_price_mrusdt=Decimal("100.00"), total_price_mrusdt=Decimal("100.00"),
        )
        item_b = OrderItem(
            order_id=order.id, product_id=product_b.id,
            quantity=1, unit_price_mrusdt=Decimal("50.00"), total_price_mrusdt=Decimal("50.00"),
        )
        db.add_all([item_a, item_b])
        await db.flush()

        profile = await affiliate.get_or_create_profile(referrer.id)

        commissions = await affiliate.distribute_commissions_for_order(
            order.id, affiliate_code=profile.referral_code,
        )

        assert len(commissions) == 2, "المفروض عمولة واحدة لكل منتج (نطاقين مختلفين)، مش عمولة واحدة مجمَّعة"

        by_scope = {c.scope_id: c for c in commissions}
        assert scope_a.id in by_scope and scope_b.id in by_scope

        c_a = by_scope[scope_a.id]
        c_b = by_scope[scope_b.id]
        assert c_a.commission_amount == Decimal("100.00") * Decimal("20.0") / Decimal(100)  # = 20.00
        assert c_b.commission_amount == Decimal("50.00") * Decimal("5.0") / Decimal(100)    # = 2.50
        assert c_a.source_type == "COMMERCE_ORDER"
        assert c_a.order_id == order.id
        assert c_a.product_id == product_a.id
        assert c_b.product_id == product_b.id

        # نطاقان منفصلان تمامًا لنفس (referrer, referred) — قرار "لا تتداخل"
        trees_count = await _independent_count(ReferralTree, referred_id=referred.id)
        assert trees_count == 2, "لازم يكون فيه صفَّا ReferralTree منفصلان — واحد لكل scope، لا تداخل"
    finally:
        await db.execute(delete(OrderItem).where(OrderItem.order_id == order.id))
        await db.commit()
        await db.execute(delete(Order).where(Order.id == order.id))
        await db.commit()
        await _cleanup_users(db, [referrer.id, referred.id])
        await _cleanup_scopes(db, scope_ids)
        await db.execute(delete(Product).where(Product.id.in_([product_a.id, product_b.id])))
        await db.commit()
        await db.execute(delete(StoreProfile).where(StoreProfile.id == store.id))
        await db.commit()

        assert await _independent_count(Commission, order_id=order.id) == 0
        assert await _independent_count(AffiliateScope, id=scope_a.id) == 0
        assert await _independent_count(AffiliateScope, id=scope_b.id) == 0


# ============================================================
# سيناريو 3: تفعيل affiliate كخدمة SaaS — Phase 7 hook
# ============================================================

async def _create_throwaway_tenant(db) -> AcademyTenant:
    """admin_id يشير لمستخدم موجود بالفعل (أي مستخدم — مجرد FK، بلا أي
    صلاحية فعلية تُمنح له على الـtenant الجديد). نفس نمط
    scripts/seed_tenant.py (يعيد استخدام إداري موجود بدل دورة بيضة-دجاجة)."""
    existing_admin = (await db.execute(select(User.id).limit(1))).scalar_one()
    suffix = _suffix()
    tenant = AcademyTenant(
        name=f"P9-TENANT-{suffix}", domain=f"p9-{suffix}.test.local",
        admin_id=existing_admin, is_active=True,
    )
    db.add(tenant)
    await db.flush()
    return tenant


@pytest.mark.asyncio
async def test_saas_subscription_activates_default_affiliate_scope(db):
    saas_repo = SaaSRepository(db)
    tenant = await _create_throwaway_tenant(db)
    subscription_id = None

    try:
        affiliate_service = AffiliateService(db, tenant.id)
        assert await affiliate_service.get_default_scope_id() is None, (
            "tenant جديد تمامًا لازم يبدأ بلا أي scope — لو رجع id يبقى في تسريب من tenant تاني"
        )

        # الخدمة الحقيقية 'affiliate' من seed migration 045 — بلا لمس
        # get_plan_by_id المكسورة، عبر get_service_by_code/get_plan_by_code
        # السليمتين (Option 3 المعتمد من المستخدم)
        affiliate_catalog_service = await saas_repo.get_service_by_code("affiliate")
        assert affiliate_catalog_service is not None, (
            "صف saas_service_catalog(code='affiliate') المفروض موجود من seed migration 045"
        )
        default_plan = await saas_repo.get_plan_by_code(affiliate_catalog_service.id, "default")
        assert default_plan is not None, (
            "خطة saas_service_plans(code='default') تحت خدمة affiliate المفروضة موجودة من نفس الـseed"
        )

        subscription = await saas_repo.create_subscription(
            tenant_id=tenant.id, plan_id=default_plan.id, status="ACTIVE",
            idempotency_key=f"P9-SUB-{tenant.id}-{_suffix()}",
        )
        await db.commit()
        subscription_id = subscription.id

        # --- استدعاء الـhook مباشرة (Option 3) ---
        saas_service = SaaSControlService(db, tenant.id)
        await saas_service._activate_affiliate_default_scope_if_needed(affiliate_catalog_service.id)

        scope_id = await affiliate_service.get_default_scope_id()
        assert scope_id is not None, "الـhook لازم ينشئ ENTITY_WIDE scope تلقائيًا بعد أول اشتراك affiliate"

        async with AsyncSessionLocal() as independent_db:
            scope_row = (await independent_db.execute(
                select(AffiliateScope).where(AffiliateScope.id == scope_id)
            )).scalar_one_or_none()
            assert scope_row is not None
            assert scope_row.tenant_id == tenant.id
            assert scope_row.scope_type == "ENTITY_WIDE"
            assert scope_row.name == "كل مبيعات المستأجر"

        # idempotency: نداء تاني للـhook — صفر تكرار (partial unique index
        # على tenant_id WHERE scope_type='ENTITY_WIDE' كان سيرفض أي محاولة
        # duplicate بـIntegrityError لو الكود مش idempotent فعليًا)
        await saas_service._activate_affiliate_default_scope_if_needed(affiliate_catalog_service.id)
        scope_id_again = await affiliate_service.get_default_scope_id()
        assert scope_id_again == scope_id
        assert await _independent_count(AffiliateScope, tenant_id=tenant.id, scope_type="ENTITY_WIDE") == 1
    finally:
        await db.execute(delete(AffiliateScope).where(AffiliateScope.tenant_id == tenant.id))
        await db.commit()
        if subscription_id:
            from app.domains.saas.models import TenantSubscription
            await db.execute(delete(TenantSubscription).where(TenantSubscription.id == subscription_id))
            await db.commit()
        await db.execute(delete(AcademyTenant).where(AcademyTenant.id == tenant.id))
        await db.commit()

        assert await _independent_count(AffiliateScope, tenant_id=tenant.id) == 0
        assert await _independent_count(AcademyTenant, id=tenant.id) == 0


# ============================================================
# سيناريو 4.أ: زامكانة (مرجع قياسي للـ12 دومين)
# ============================================================

@pytest.mark.asyncio
async def test_zamakana_domain_flow_registers_commission_via_real_call_site(db):
    affiliate = AffiliateService(db, TENANT_ID)
    repo = AffiliateRepository(db)

    referrer = await _create_user(db, TENANT_ID, "p9_zk_ref")
    referred = await _create_user(db, TENANT_ID, "p9_zk_red")
    referred.referred_by_user_id = referrer.id
    await db.flush()

    try:
        await affiliate.get_or_create_profile(referrer.id)
        tiers = await repo.get_commission_tiers(TENANT_ID)
        assert tiers is not None
        expected_rate = tiers.level_1_pct

        zamakana_service = ZamakanaService(db)
        # نفس الاستدعاء الحرفي من zamakana/service.py:90 (NODE_CREATED)
        await zamakana_service._register_affiliate_commission(referred.id, TENANT_ID, "NODE_CREATED")

        async with AsyncSessionLocal() as independent_db:
            row = (await independent_db.execute(
                select(Commission).where(
                    Commission.user_id == referrer.id, Commission.source_type == "ZAMAKANA",
                )
            )).scalar_one_or_none()
            assert row is not None, "المفروض _register_affiliate_commission أنشأت عمولة حقيقية عبر المسار الفعلي للدومين"
            assert row.commission_amount == Decimal("2.00") * expected_rate / Decimal(100)
            assert row.referral_level == 1

            tree_row = (await independent_db.execute(
                select(ReferralTree).where(
                    ReferralTree.referrer_id == referrer.id, ReferralTree.referred_id == referred.id,
                )
            )).scalar_one_or_none()
            assert tree_row is not None, "المفروض ensure_referral_link اتنادت من جوه _register_affiliate_commission"
    finally:
        await _cleanup_users(db, [referrer.id, referred.id])
        assert await _independent_count(Commission, user_id=referrer.id) == 0


# ============================================================
# سيناريو 4.ب: digital_twin (حالة خاصة — affiliate_code مباشر بلا referred_by_user_id)
# ============================================================

@pytest.mark.asyncio
async def test_digital_twin_affiliate_code_direct_path_without_stored_referral(db):
    affiliate = AffiliateService(db, TENANT_ID)
    repo = AffiliateRepository(db)

    referrer = await _create_user(db, TENANT_ID, "p9_dt_ref")
    cold_user = await _create_user(db, TENANT_ID, "p9_dt_cold")
    # عمدًا: cold_user.referred_by_user_id يبقى None — يحاكي مستخدم بلا
    # أي رابط إحالة مُسجَّل مسبقًا، يقدّم كود إحالة وقت الحدث نفسه فقط
    await db.flush()
    assert cold_user.referred_by_user_id is None

    try:
        profile = await affiliate.get_or_create_profile(referrer.id)
        tiers = await repo.get_commission_tiers(TENANT_ID)
        assert tiers is not None
        expected_rate = tiers.level_1_pct

        twin_service = DigitalTwinService(db)
        # نفس الاستدعاء الحرفي من digital_twin/service.py — TWIN_CREATION
        # ثابتة 5.00، مع affiliate_code بدل referred_by_user_id
        await twin_service._register_affiliate_commission(
            user_id=cold_user.id, tenant_id=TENANT_ID, action_type="TWIN_CREATION",
            amount=Decimal("0.0"), affiliate_code=profile.referral_code,
        )

        async with AsyncSessionLocal() as independent_db:
            row = (await independent_db.execute(
                select(Commission).where(
                    Commission.user_id == referrer.id, Commission.source_type == "DIGITAL_TWIN",
                )
            )).scalar_one_or_none()
            assert row is not None, "المفروض المسار البديل (affiliate_code مباشر) عمل نفس عمل referred_by_user_id"
            assert row.commission_amount == Decimal("5.00") * expected_rate / Decimal(100)

            tree_row = (await independent_db.execute(
                select(ReferralTree).where(
                    ReferralTree.referrer_id == referrer.id, ReferralTree.referred_id == cold_user.id,
                )
            )).scalar_one_or_none()
            assert tree_row is not None, "المفروض اتربط referral link جديد on-the-fly من الكود، رغم عدم وجود referred_by_user_id مسبقًا"
    finally:
        await _cleanup_users(db, [referrer.id, cold_user.id])
        assert await _independent_count(Commission, user_id=referrer.id) == 0


# ============================================================
# سيناريو 5: عدم تفعيل SaaS (scope_id=None) — تخطٍّ صامت آمن
# ============================================================

@pytest.mark.asyncio
async def test_no_active_affiliate_service_skips_silently_without_breaking_flow(db):
    tenant = await _create_throwaway_tenant(db)  # صفر scopes، صفر تفعيل SaaS

    referrer = await _create_user(db, tenant.id, "p9_noscope_ref")
    referred = await _create_user(db, tenant.id, "p9_noscope_red")
    referred.referred_by_user_id = referrer.id
    await db.flush()

    try:
        affiliate = AffiliateService(db, tenant.id)
        assert await affiliate.get_default_scope_id() is None

        zamakana_service = ZamakanaService(db)
        # لا يجب أن يرمي أي استثناء — نفس ضمان try/except الأصلي في كل
        # الـ12 دومين، حتى لو resolve_scope_id_for_member رجعت None
        await zamakana_service._register_affiliate_commission(referred.id, tenant.id, "NODE_CREATED")

        assert await _independent_count(Commission, user_id=referrer.id) == 0, (
            "المفروض صفر عمولة — لا scope متاح يعني تخطٍّ صامت، مش إنشاء عمولة بلا scope_id (NOT NULL)"
        )
        assert await _independent_count(ReferralTree, referrer_id=referrer.id) == 0, (
            "المفروض صفر ReferralTree كمان — ensure_referral_link ميتناداش أصلاً لو scope_id=None"
        )
    finally:
        await _cleanup_users(db, [referrer.id, referred.id])
        await db.execute(delete(AcademyTenant).where(AcademyTenant.id == tenant.id))
        await db.commit()
        assert await _independent_count(AcademyTenant, id=tenant.id) == 0
