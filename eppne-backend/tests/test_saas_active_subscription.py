"""
regression test لجلسة `saas-control-service-get-active-subscription-fix`
(Backlog #9، الإكمال).
تقرير الجلسة الأصلية: .claude/reports/saas-control-service-fix-session-log.md

السبب الجذري (كان): `SaaSControlService.get_active_subscription(tenant_id)`
غير موجودة إطلاقًا (لم تُكتب من الأساس) — مستخدَمة من 8 دومينات بنفس
التوقيع، فتكراش `AttributeError` فورًا داخل `_check_saas_limits` في كل
واحدة منهم.

الإصلاح المُطبَّق:
1. `SaaSRepository.get_any_active_subscription(tenant_id)` (جديدة) —
   اشتراك واحد شامل نشط/تجريبي للـtenant، بغض النظر عن الخدمة.
2. `SaaSControlService.get_active_subscription(tenant_id)` (جديدة) —
   wrapper صرف حولها.
3. **اكتشاف إضافي مُصلَح في نفس الجلسة:** `subscription.features` غير
   موجودة على `TenantSubscription` أصلًا (موجودة على `ServicePlan` فقط عبر
   `subscription.plan`)، **و**`features` مصممة كـ`List[str]` مش
   `Dict[str,bool]`. صُحِّح الوصول في الثمانية دومينات:
   `subscription.plan.features or []` + `feature not in features` (بدل
   `subscription.features.get(feature, False)`)، مع فحص دفاعي إضافي
   `if not subscription.plan: raise PermissionDeniedError(...)`.

هذا الملف يغطي الأربعة دوال اللي اتحقق منها حيًا في الجلسة الأصلية
(`realestate.rent_unit`, `realestate.buy_fractional_ownership`,
`insurance.subscribe`, `insurance.review_claim`) — بنفس مستوى التحقق
الموثَّق لكل واحدة (قسم 14.1 من التقرير):

| الدالة | المستوى الموثَّق |
|---|---|
| `realestate.rent_unit` | ✅ تحقق حي كامل، نجاح تام |
| `insurance.subscribe` | ✅ تحقق حي كامل للمسار المالي (commit+create_subscription) |
| `realestate.buy_fractional_ownership` | 🟡 تحقق حي جزئي (#9 مؤكَّدة، الباقي محجوب ببج مسبق) |
| `insurance.review_claim` | 🟡 تحقق حي جزئي (#9 مؤكَّدة، الباقي محجوب بـ`insurance-review-claim-issuer-entity-id-reviewer-id-conflict` — Backlog #1 اتصلح في جلسة `user-repository-get-by-id-audit` وبقى غير ظاهر في هذا المسار لأن هذه الطبقة الأسبق بتحجبه) |

**منهجية التحقق لكل دالة:** استدعاء حي حقيقي (بلا `monkeypatch` على
`_check_saas_limits` نفسها — هذا بالظبط جوهر ما بنتحقق منه، بعكس منهجية
جلسات سابقة كانت بتتجاوز كراشات وقائية غير مرتبطة). نجاح `_check_saas_limits`
الحقيقية (صفر `AttributeError`) **هو الإثبات المباشر لإصلاح #9**، بغض النظر
عمّا يحصل بعده في الدالة.

**بخصوص `create_invoice()` تحديدًا:** الثمانية دوال المُصلَحة في #11b (ومنهم
`rent_unit`/`subscribe`) بتستدعي `InvoicingService.create_invoice()` بعد
`commit()`. اكتُشف في جلسة `realestate-insurance-savepoint-fix`
(`tests/test_realestate_insurance_savepoint.py`, وثَّق في `PROGRESS_LOG.md`)
إن هذا الاستدعاء بيفشل حاليًا لـ`tenant_id=1` ببج غير مرتبط تمامًا
(`invoicing-generate-invoice-number-count-based-collision`). **هذا الملف
بيتفادى البج ده عمدًا** (`monkeypatch` على `InvoicingService.create_invoice`
كـno-op بسيط) — مش لأنه جزء من #9، لكن عشان نعزل التحقق هنا على منطق #9
تحديدًا بلا تلوّث من بج تاني موثَّق مسبقًا في جلسة منفصلة، متسقًا مع قاعدة
"المنطق المُحقَّق منه فعليًا فقط" لكل جلسة على حدة.

**بخصوص `buy_fractional_ownership`/`review_claim`:** التقرير الأصلي وثَّق
إنهم بيوصلوا لـ`_check_saas_limits` بنجاح (إثبات #9) لكن بيكراشوا بعدها
ببجات مسبقة منفصلة تمامًا:
- `buy_fractional_ownership`: `AIAgentsService.execute_agent_action()` بتتنادى
  بمعامل `tenant_id=` زايد (Backlog #16 — هذا الموضع تحديدًا مُستثنى عمدًا من
  إصلاح #16 لسبب منفصل: `commit()` جواها هيتعارض مع `begin_nested()` المحيط،
  موثَّق كبند `ai-agents-execute-action-commit-inside-begin-nested`). **تأكَّدت
  أنه لسه موجود فعليًا بالقراءة المباشرة وقت كتابة هذا الملف.**
- `review_claim` (مسار `approve=True`): `UserRepository.get_by_id()` بتتنادى
  بمعامل واحد بس (`user_id`) رغم إن التوقيع الفعلي بيطلب `tenant_id` إجباريًا
  كمان (Backlog #1، `user-repository-get-by-id-audit`). **تأكَّدت أنه لسه
  موجود فعليًا بالقراءة المباشرة وقت كتابة هذا الملف.**

هذان البجان **خارج نطاق #9 تمامًا** — الاختباران هنا بيستخدموا
`pytest.raises` بمطابقة نص الخطأ المحدَّد (نفس النص الموثَّق حيًا في التقرير
الأصلي)، لإثبات إن الاستدعاء **وصل فعليًا** لهذه النقطة (يعني عدّى
`_check_saas_limits` بنجاح) قبل ما يفشل، مع تأكيد إضافي إن التراجع نظيف
(صفر أثر جزئي على القرص) — بنفس منهجية التقرير الأصلي بالحرف.

**استكمال الجلسة [2026-08-19] بعد إعادة تشغيل الجهاز:** الملف كان مكتوبًا
بالكامل تقريبًا قبل الهنج (كان موجودًا untracked باسم
`tests/test_saas_active_subscription_fix.py`، تاريخ إنشاء الملف نفسه مؤكَّد
[2026-08-19 04:54] أسبق من بداية جلسة الاستئناف هذه — لم يُكتب في هذه
الجلسة). عند استئناف الجلسة، اختبار `review_claim` كان بيفشل
بـ`ForeignKeyViolationError`، وكشف الفحص **بج production حقيقي منفصل تمامًا
عن #9** (راجع docstring الاختبار نفسه + بند
`insurance-review-claim-issuer-entity-id-reviewer-id-conflict` الجديد في
`PROGRESS_LOG.md`) — الاختبار عُدِّل ليتجاوزه عمدًا (مش يصلحه) عشان يوصل
لهدفه الأصلي. تم بعدها نقل الملف لاسمه النهائي المتوافق مع تسمية باقي ملفات
الجلسة (`test_invitations_savepoint_leak.py`,
`test_realestate_insurance_savepoint.py`) — صفر تغيير على منطق التحقق
الأصلي بتاع #9 نفسه، وصفر لمس على أي كود إنتاج.
"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, delete

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User
from app.domains.identity.repository import WalletRepository
from app.domains.finance.models import Wallet, Transaction, AuditLog
from app.domains.invoicing.service import InvoicingService

from app.domains.realestate.service import RealEstateService
from app.domains.realestate.repository import RealEstateRepository
from app.domains.realestate.models import (
    RealEstateDevelopment, PropertyUnit, RentalContract, PropertyOwnership, PropertyType,
)

from app.domains.insurance.service import InsuranceService
from app.domains.insurance.repository import InsuranceRepository
from app.domains.insurance.models import (
    InsurancePolicy, InsuranceSubscription, InsuranceClaim,
    PolicyType, PremiumCycle, ClaimStatus,
)
from app.core.errors import PermissionDeniedError

TENANT_ID = 1
# land_assets id=1 و sovereign_entities_v2 id=4 — صفوف throwaway موجودة
# بالفعل تحت tenant_id=1 من جلسات تحقق سابقة (قراءة فقط، صفر تعديل/حذف).
EXISTING_LAND_ASSET_ID = 1
EXISTING_ISSUER_ENTITY_ID = 4


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_funded_user(db, prefix: str, mr_usdt: Decimal = Decimal("0")) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    user = await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )
    if mr_usdt > 0:
        wallet_repo = WalletRepository(db)
        wallet = await wallet_repo.get_by_user_id(user.id, TENANT_ID)
        assert wallet is not None
        await wallet_repo.update_balances(wallet.id, {"MR_USDT": float(mr_usdt)})
    return user


async def _cleanup_users_and_finance(db, user_ids):
    """تنظيف عام: Transaction/AuditLog (بسبب finance.transfer المحتمل) ثم
    Wallet/User. بيفلتر بـsender_id/user_id ضمن user_ids بس — صفر لمس على
    المستقبِلين المشتركين (زي entity_4@eppne.com) المُعاد استخدامهم قراءة
    فقط من جلسات سابقة."""
    if not user_ids:
        return
    await db.execute(delete(Transaction).where(Transaction.sender_id.in_(user_ids)))
    await db.execute(delete(AuditLog).where(AuditLog.user_id.in_(user_ids)))
    await db.execute(delete(Wallet).where(Wallet.user_id.in_(user_ids)))
    await db.execute(delete(User).where(User.id.in_(user_ids)))
    await db.commit()


async def _noop_create_invoice(self, **kwargs):
    """تجاوز عمدي لبج `invoicing-generate-invoice-number-count-based-collision`
    (موثَّق في PROGRESS_LOG.md، مُكتشَف ومُختبَر في ملف منفصل تمامًا) — هذا
    الملف بيركّز على منطق #9 فقط، مش على منطق الفوترة."""
    return None


# ============================================================
# 1) realestate.rent_unit — ✅ تحقق حي كامل
# ============================================================

@pytest.mark.asyncio
async def test_realestate_rent_unit_saas_check_passes(db, monkeypatch):
    """`_check_saas_limits` الحقيقية (بلا monkeypatch عليها) لازم تعدي بنجاح
    وتوصل الدالة لنجاح كامل — نفس مستوى التقرير الأصلي (قسم 13.1/14.1،
    الصف 1)."""
    monkeypatch.setattr(InvoicingService, "create_invoice", _noop_create_invoice)

    re_repo = RealEstateRepository(db)
    development = await re_repo.create_development(
        tenant_id=TENANT_ID, land_asset_id=EXISTING_LAND_ASSET_ID,
        name=f"REGTEST-SAAS9-DEV-{_suffix()}", development_type="RESIDENTIAL",
    )
    unit = await re_repo.create_unit(
        tenant_id=TENANT_ID, development_id=development.id,
        unit_number=f"REGTEST-SAAS9-UNIT-{_suffix()}", area_sqm=Decimal("100"),
        property_type=PropertyType.APARTMENT,
        is_available_for_rent=True, is_available_for_sale=False,
    )
    unit_id = unit.id
    development_id = development.id
    landlord = await _create_funded_user(db, "p_regtest_saas9_re_landlord")
    tenant_user = await _create_funded_user(db, "p_regtest_saas9_re_tenant")
    user_ids = [landlord.id, tenant_user.id]
    service = RealEstateService(db)

    try:
        contract = await service.rent_unit(
            landlord_id=landlord.id, tenant_id=TENANT_ID, unit_id=unit_id,
            tenant_user_id=tenant_user.id, monthly_rent=Decimal("50"),
            start_date=datetime.utcnow(), end_date=datetime.utcnow() + timedelta(days=365),
            idempotency_key=f"REGTEST-SAAS9-RENT-{_suffix()}",
        )
        assert contract is not None

        refreshed = (await db.execute(
            select(RentalContract).where(RentalContract.id == contract.id)
        )).scalar_one_or_none()
        assert refreshed is not None, "العقد المتوقع مش موجود على القرص — دليل مباشر إن #9 بتعمل صح"
        assert refreshed.tenant_user_id == tenant_user.id
    finally:
        await db.execute(delete(RentalContract).where(RentalContract.unit_id == unit_id))
        await db.execute(delete(PropertyUnit).where(PropertyUnit.id == unit_id))
        await db.execute(delete(RealEstateDevelopment).where(RealEstateDevelopment.id == development_id))
        await db.commit()
        await _cleanup_users_and_finance(db, user_ids)


# ============================================================
# 2) insurance.subscribe — ✅ تحقق حي كامل للمسار المالي
# ============================================================

@pytest.mark.asyncio
async def test_insurance_subscribe_saas_check_passes(db, monkeypatch):
    """`_check_saas_limits` الحقيقية لازم تعدي بنجاح، والمسار المالي
    الكامل (التحويل + إنشاء الاشتراك) يلتزم على القرص — نفس مستوى التقرير
    الأصلي (قسم 13.2/14.1، الصف 2)."""
    monkeypatch.setattr(InvoicingService, "create_invoice", _noop_create_invoice)

    ins_repo = InsuranceRepository(db)
    buyer = await _create_funded_user(db, "p_regtest_saas9_ins_sub", Decimal("1000"))
    policy = await ins_repo.create_policy(
        tenant_id=TENANT_ID, issuer_entity_id=EXISTING_ISSUER_ENTITY_ID,
        name=f"REGTEST-SAAS9-POLICY-{_suffix()}", policy_type=PolicyType.ACCIDENT,
        base_premium_mrusdt=Decimal("20"), premium_cycle=PremiumCycle.MONTHLY,
        max_coverage_limit_mrusdt=Decimal("1000"), is_active=True,
        created_by=buyer.id,
    )
    await db.commit()  # create_policy() flush-only
    policy_id = policy.id
    user_ids = [buyer.id]
    service = InsuranceService(db)

    try:
        subscription = await service.subscribe(
            user_id=buyer.id, tenant_id=TENANT_ID,
            data={
                "policy_id": policy_id, "subscriber_user_id": buyer.id,
                "start_date": datetime.utcnow(),
            },
            idempotency_key=f"REGTEST-SAAS9-SUB-{_suffix()}",
        )
        assert subscription is not None

        refreshed = (await db.execute(
            select(InsuranceSubscription).where(InsuranceSubscription.id == subscription.id)
        )).scalar_one_or_none()
        assert refreshed is not None, "الاشتراك المتوقع مش موجود على القرص — دليل مباشر إن #9 بتعمل صح"
        assert refreshed.status == "ACTIVE"

        wallet = await WalletRepository(db).get_by_user_id(buyer.id, TENANT_ID)
        assert wallet is not None
        assert Decimal(str(wallet.balances.get("MR_USDT"))) == Decimal("980"), (
            "دفع القسط لازم يكون التزم فعليًا (خُصم القسط 20 من 1000)"
        )
    finally:
        await db.execute(delete(InsuranceSubscription).where(InsuranceSubscription.policy_id == policy_id))
        await db.execute(delete(InsurancePolicy).where(InsurancePolicy.id == policy_id))
        await db.commit()
        await _cleanup_users_and_finance(db, user_ids)


# ============================================================
# 3) realestate.buy_fractional_ownership — 🟡 تحقق حي جزئي
# ============================================================

@pytest.mark.asyncio
async def test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug(db):
    """`_check_saas_limits` الحقيقية لازم تعدي بنجاح (تصل الدالة لمنطقها
    الداخلي)، ثم تكراش بالبج المسبق المُوثَّق تحديدًا (Backlog #16، معامل
    `tenant_id=` زايد على `execute_agent_action`) — نفس مستوى التقرير
    الأصلي (قسم 13.1/14.1، الصف 3). لو الاستثناء كان عن subscription/
    features/AttributeError بدل ده، ده رجوع لباج #9 نفسه."""
    re_repo = RealEstateRepository(db)
    development = await re_repo.create_development(
        tenant_id=TENANT_ID, land_asset_id=EXISTING_LAND_ASSET_ID,
        name=f"REGTEST-SAAS9-DEV2-{_suffix()}", development_type="RESIDENTIAL",
    )
    unit = await re_repo.create_unit(
        tenant_id=TENANT_ID, development_id=development.id,
        unit_number=f"REGTEST-SAAS9-UNIT2-{_suffix()}", area_sqm=Decimal("100"),
        property_type=PropertyType.APARTMENT,
        is_available_for_sale=True, is_available_for_rent=False,
        sale_price_mrusdt=Decimal("500"),
    )
    unit_id = unit.id
    development_id = development.id
    buyer = await _create_funded_user(db, "p_regtest_saas9_re_buyer")
    user_ids = [buyer.id]
    service = RealEstateService(db)

    try:
        with pytest.raises(TypeError, match="tenant_id"):
            await service.buy_fractional_ownership(
                buyer_id=buyer.id, tenant_id=TENANT_ID, unit_id=unit_id,
                percentage=Decimal("10"),
                idempotency_key=f"REGTEST-SAAS9-BUY-{_suffix()}",
            )

        # تراجع نظيف — صفر أثر جزئي (المورد لم يُنشأ، المحفظة لم تُلمس)
        ownership_count = (await db.execute(
            select(PropertyOwnership).where(PropertyOwnership.owner_user_id == buyer.id)
        )).scalars().all()
        assert len(ownership_count) == 0, "صفر ownership كان المتوقع — الكراش قبل الوصول لـfinance.transfer أصلًا"
    finally:
        await db.execute(delete(PropertyOwnership).where(PropertyOwnership.unit_id == unit_id))
        await db.execute(delete(PropertyUnit).where(PropertyUnit.id == unit_id))
        await db.execute(delete(RealEstateDevelopment).where(RealEstateDevelopment.id == development_id))
        await db.commit()
        await _cleanup_users_and_finance(db, user_ids)


# ============================================================
# 4) insurance.review_claim — 🟡 تحقق حي جزئي
# ============================================================

@pytest.mark.asyncio
async def test_insurance_review_claim_saas_check_passes_then_hits_known_bug(db):
    """`_check_saas_limits` الحقيقية لازم تعدي بنجاح، ثم تكراش بالبج المسبق
    المُوثَّق تحديدًا — نفس مستوى التقرير الأصلي (قسم 13.1/14.1، الصف 4).

    **⚠️ تحديث [جلسة `user-repository-get-by-id-audit`، Backlog #1]:**
    الاختبار ده كان أصلًا بيعتمد على `pytest.raises(TypeError, match="tenant_id")`
    كدليل غير مباشر على الوصول لنفس النقطة — يعني `UserRepository.get_by_id()`
    اتنادت بمعامل واحد بس رغم إن توقيعها الحقيقي بيطلب `tenant_id` إجباريًا
    (Backlog #1). **البج ده اتصلح فعليًا في جلسة `user-repository-get-by-id-audit`**
    (`.claude/reports/user-repository-get-by-id-audit-session-log.md`،
    القسم 12.1 — `insurance/service.py:57-64`)، فبقى التوقُّع القديم باطل:
    الكود دلوقتي بيعدي `get_by_id` بنجاح تام. **حُدِّث الاختبار ليعتمد على
    الطبقة التالية الحقيقية المؤكَّدة حيًا** بدل الطبقة القديمة المُصلَحة —
    راجع الفقرة التالية.

    **🔴 اكتشاف بج production حقيقي [2026-08-19] (مش غلطة بيانات throwaway):**
    الكود الأصلي (قبل هنج VS Code) كان بيمرر `reviewer.id` (يوزر throwaway
    عادي) كـ`issuer_entity_id` عند إنشاء البوليصة، فكسر `ForeignKeyViolationError`
    فورًا — `InsurancePolicy.issuer_entity_id` FK حقيقي على
    `sovereign_entities_v2.id`، مش على `users.id`. لكن الفحص بالقراءة كشف
    حاجة أعمق: `InsuranceService.review_claim()` (`insurance/service.py:431`)
    بتقارن `policy.issuer_entity_id` (نطاق `sovereign_entities_v2.id`) مباشرة
    بـ`reviewer_id` — و`insurance/router.py:195` بيمرر `reviewer_id=
    current_user.id` (نطاق `users.id` مختلف تمامًا) في الاستدعاء الحقيقي من
    الـAPI. **يعني أي `superuser` حقيقي هيفشل بـ`PermissionDeniedError`
    "Not authorized to review this claim" دايمًا تقريبًا عند محاولة مراجعة
    أي مطالبة تأمين حقيقية** — ميزة إنتاجية كاملة معطَّلة. مُوثَّق كبند Backlog
    منفصل جديد (`insurance-review-claim-issuer-entity-id-reviewer-id-conflict`)
    في `PROGRESS_LOG.md`، **صفر لمس على `insurance/service.py` هنا** (خارج
    نطاق #9 تمامًا).

    **الاختبار المُحدَّث [جلسة `user-repository-get-by-id-audit`] — يثبت
    البج الحقيقي بدل تجاوزه:** بعد إصلاح Backlog #1، الطبقة اللي كانت
    بتحجب هذا المسار اختفت — فبقى ممكن (وواجب) نختبر السيناريو الواقعي
    الفعلي مباشرة بدل الـtrick القديم. `EXISTING_ISSUER_ENTITY_ID` لسه
    مُستخدَمة كـ`issuer_entity_id` عند إنشاء البوليصة (صف throwaway موجود
    فعلًا، قراءة فقط)، **لكن `reviewer_id` بقى `claimant.id`** — قيمة
    حقيقية من نطاق `users.id` (بالظبط زي `current_user.id` الممرَّرة من
    `insurance/router.py:195` في الاستدعاء الحقيقي من الـAPI)، **مختلفة
    عمدًا عن `EXISTING_ISSUER_ENTITY_ID`** — فالفحص المكسور (سطر 431)
    هيفشل **بشكل واقعي وحقيقي هذه المرة**، مش بالصدفة كالسابق. هذا يثبت
    حيًا بالضبط السيناريو الموثَّق: أي مراجع حقيقي (`users.id`) هيترفض
    دايمًا لأن `policy.issuer_entity_id` (نطاق `sovereign_entities_v2.id`)
    مش نفس النطاق أصلًا."""
    ins_repo = InsuranceRepository(db)
    claimant = await _create_funded_user(db, "p_regtest_saas9_ins_claimant")
    user_ids = [claimant.id]

    policy = await ins_repo.create_policy(
        tenant_id=TENANT_ID, issuer_entity_id=EXISTING_ISSUER_ENTITY_ID,
        name=f"REGTEST-SAAS9-POLICY2-{_suffix()}", policy_type=PolicyType.ACCIDENT,
        base_premium_mrusdt=Decimal("20"), premium_cycle=PremiumCycle.MONTHLY,
        max_coverage_limit_mrusdt=Decimal("1000"), is_active=True,
        created_by=claimant.id,
    )
    subscription = await ins_repo.create_subscription(
        tenant_id=TENANT_ID, policy_id=policy.id, subscriber_user_id=claimant.id,
        start_date=datetime.utcnow(), status="ACTIVE",
        policy_nft_id=f"INS-REGTEST-{_suffix()}", subscription_tx_hash=f"SUB-REGTEST-{_suffix()}",
    )
    claim = await ins_repo.create_claim(
        tenant_id=TENANT_ID, subscription_id=subscription.id, claimant_user_id=claimant.id,
        incident_date=datetime.utcnow(), incident_description="Regression test incident",
        claimed_amount_mrusdt=Decimal("100"), status=ClaimStatus.SUBMITTED,
    )
    await db.commit()  # create_policy/create_subscription/create_claim كلهم flush-only
    policy_id = policy.id
    subscription_id = subscription.id
    claim_id = claim.id
    service = InsuranceService(db)

    try:
        with pytest.raises(PermissionDeniedError, match="Not authorized to review this claim"):
            await service.review_claim(
                claim_id=claim_id, reviewer_id=claimant.id, tenant_id=TENANT_ID,
                approve=True,
                idempotency_key=f"REGTEST-SAAS9-CLAIM-{_suffix()}",
            )

        # تراجع نظيف — صفر أثر جزئي
        refreshed_claim = (await db.execute(
            select(InsuranceClaim).where(InsuranceClaim.id == claim_id)
        )).scalar_one_or_none()
        assert refreshed_claim is not None
        assert refreshed_claim.status == ClaimStatus.SUBMITTED, (
            "حالة المطالبة لازم تفضل SUBMITTED — الكراش قبل الوصول لـupdate_claim أصلًا"
        )
        assert refreshed_claim.payout_tx_hash is None
    finally:
        await db.execute(delete(InsuranceClaim).where(InsuranceClaim.id == claim_id))
        await db.execute(delete(InsuranceSubscription).where(InsuranceSubscription.id == subscription_id))
        await db.execute(delete(InsurancePolicy).where(InsurancePolicy.id == policy_id))
        await db.commit()
        await _cleanup_users_and_finance(db, user_ids)
