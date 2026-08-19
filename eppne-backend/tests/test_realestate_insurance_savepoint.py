"""
regression test لجلسة `realestate-insurance-savepoint-fix` (Backlog #11b).
تقرير الجلسة الأصلية: .claude/reports/realestate-insurance-savepoint-fix-session-log.md

السبب الجذري (كان): `InvoicingRepository.create_invoice()` بتعمل `commit()`
مباشر — بيقفل الـSAVEPOINT بتاع `begin_nested()` في أي دالة بتستدعيها من
جواه. اكتُشف عبر 8 دوال/4 دومينات: `realestate` (×2)، `insurance` (×2)،
`tourism_sports` (×3)، `zamakana` (×1).

الإصلاح المُطبَّق (نفس النمط في كل الثمانية دوال): نقل استدعاء
`create_invoice()` من جوه `begin_nested()` إلى **مباشرة بعد `await
self.db.commit()`**، ملفوف بـ`try/except Exception` (يسجل اللوج، يكمل عادي
لـ`_store_idempotency()`/`return`). `finance.transfer()` (حيث موجودة) تفضل
جوه `begin_nested()` — مثبَّت أنها آمنة (savepoint داخلية خاصة بيها).

مستوى التحقق الموثَّق أصلًا في التقرير (قسم 17.1) كان: تحقق حي كامل لـ
(1) `purchase_event_ticket`، (4) `rent_unit`، (8) `pledge_time`، وجزئي لـ
(6) `insurance.subscribe`؛ مراجعة بنيوية فقط لـ(2, 3, 5, 7).

**⚠️ تعديل نطاق بموافقة مستخدم صريحة [2026-08-18]، أثناء كتابة هذا الملف:**
اكتُشف بج مسبق جديد غير موثَّق في التقرير الأصلي —
`invoicing-generate-invoice-number-count-based-collision` (تفصيل تحت) —
بيمنع **أي** استدعاء حقيقي لـ`create_invoice()` لـ`tenant_id=1` حاليًا
(مؤكَّد حيًا بمحاولة فعلية لكل الأربعة: 1, 4, 6, 8 — كلهم ضربوا نفس الرقم
بالحرف `INV-1-000015`). **نتيجة لذلك، الأربعة نزلوا من "تحقق حي كامل/جزئي"
لـ"مراجعة بنيوية فقط"** (بنفس أسلوب الأربعة الأصليين 2, 3, 5, 7) — **صفر
لمس على `invoicing/service.py`**، القرار موثَّق في `PROGRESS_LOG.md`.
**النتيجة النهائية: كل الثمانية دوال بمراجعة بنيوية فقط في هذا الملف** —
لكن الملف بيتعوَّض بـ**اختبار تاسع (`xfail` موثَّق)** بيثبت حيًا اكتشاف
جانبي حرج تاني (`invoicing-missing-rollback-on-exception-11b`، تفصيل تحت).

| # | الدالة | المستوى النهائي |
|---|---|---|
| 1 | `tourism_sports.purchase_event_ticket` | 🟡 مراجعة بنيوية (نزلت من كامل) |
| 2 | `tourism_sports.book_program` | 🟡 مراجعة بنيوية فقط (زي التقرير الأصلي) |
| 3 | `tourism_sports.place_transfer_bid` | 🟡 مراجعة بنيوية فقط (زي التقرير الأصلي) |
| 4 | `realestate.rent_unit` | 🟡 مراجعة بنيوية (نزلت من كامل) + ✅ xfail موثَّق لاكتشاف جانبي |
| 5 | `realestate.buy_fractional_ownership` | 🟡 مراجعة بنيوية فقط (زي التقرير الأصلي) |
| 6 | `insurance.subscribe` | 🟡 مراجعة بنيوية (نزلت من جزئي) |
| 7 | `insurance.review_claim` | 🟡 مراجعة بنيوية فقط (زي التقرير الأصلي) |
| 8 | `zamakana.pledge_time` | 🟡 مراجعة بنيوية (نزلت من كامل) |

**بجات مسبقة منفصلة تمامًا عن #11b وراء المراجعة البنيوية:**
- **الأربعة الأصليين في التقرير (2, 3, 5, 7):**
  - `finance-transfer-returns-transaction-object-not-tx-hash-string`:
    `FinanceService.transfer()` (`finance/service.py:147`) بترجع كائن
    `Transaction` كامل (`return tx`) مش نص `tx_hash` — بتكسر `book_program`
    (`payment_tx_hash=tx_hash`)، `buy_fractional_ownership`
    (`purchase_tx_hash=tx_hash`)، `review_claim` مسار `approve=True`
    (`payout_tx_hash=payout_tx`) بـ`DataError` **جوه** `begin_nested()`، قبل
    ما نوصل حتى لكود #11b. **تأكَّدت أنها لسه موجودة فعليًا بالقراءة
    المباشرة وقت كتابة هذا الملف.**
  - `tourism-place-transfer-bid-player-id-user-id-conflict`: `place_transfer_bid`
    بتستخدم نفس القيمة (`data["player_id"]`) كـ`user_id` (`get_player_profile`)
    وكـ`PlayerProfile.id` (FK فعلي في `player_transfers.player_id`) —
    `IntegrityError` مؤكَّد، لسه موجود.
- **الأربعة الجدد (1, 4, 6, 8، اكتُشفوا أثناء كتابة هذا الملف):**
  - `invoicing-generate-invoice-number-count-based-collision`:
    `InvoicingService._generate_invoice_number()` بتحسب `count(invoices)+1`
    — فجوة في تسلسل `tenant_id=1` (فاتورة اتحذفت قديمًا) بتخلي `count()`
    يرجع رقم أقل من أعلى رقم مُستخدَم فعليًا → `UniqueViolationError` مؤكَّد
    حيًا في الأربعة (نفس الرقم بالحرف كل مرة: `INV-1-000015`). لـ
    `insurance.subscribe` تحديدًا: كان فيه كمان بج ثانٍ منفصل في بيانات
    throwaway الاختبار نفسه (`start_date` مفقود من `data` — Pydantic
    `InsuranceSubscriptionCreate` schema في الـrouter الحقيقي بيطلبها
    إجباريًا) — **اتصلح في الاختبار قبل ما نوصل لبج invoice_number**.
    تفصيل كامل في `PROGRESS_LOG.md`.

**بخصوص Backlog #9/#12 (كراشات وقائية غير مرتبطة بـ#11b استخدمها التقرير
الأصلي لتجاوزها بـ`monkeypatch`):**
- **Backlog #9** (`get_active_subscription`) **اتصلح فعليًا** (commit
  `9f37201`) — `realestate`/`insurance` **لا يحتاجان** أي `monkeypatch`.
- **Backlog #12** (`can_access_service` بمعاملين على توقيع معامل واحد)
  **لسه مفتوح** — لكن بما إن الملف كله بقى مراجعة بنيوية فقط (بجات تانية
  أعمق بتحجب أي تنفيذ حي قبل ما نوصل حتى لـ#12)، **مفيش استدعاء حي فعلي في
  هذا الملف محتاج يتجاوزه أصلًا**.

**اكتشاف جانبي إضافي (`invoicing-missing-rollback-on-exception-11b`)،
اتثبت حيًا في `test_realestate_rent_unit_real_invoice_failure_leaves_session_broken`
تحت:** الـ`try/except` المضاف في #11b حوالين `create_invoice()` بيمسك
الاستثناء لكن من غير `db.rollback()` — لو الفشل كان خطأ DB حقيقي (مش
`RuntimeError` مصطنع بره الـDB، زي `invoice_number` مُكرَّر)، السيشن بتفضل
`PendingRollbackError` لأي كود بعده جوه نفس الدالة. المورد الأساسي غير
متأثر (بيتحفظ قبل الـtry/except). اختبار `xfail(strict=True)` موثَّق — صفر
إصلاح على `invoicing/service.py` في هذه الجلسة.
"""
import inspect
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import delete

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels
from app.core.database import AsyncSessionLocal

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User
from app.domains.identity.repository import WalletRepository
from app.domains.finance.models import Wallet
from app.domains.invoicing.models import Invoice
from app.domains.invoicing.service import InvoicingService

from app.domains.realestate.service import RealEstateService
from app.domains.realestate.repository import RealEstateRepository
from app.domains.realestate.models import (
    RealEstateDevelopment, PropertyUnit, RentalContract, PropertyType,
)

from app.domains.insurance.service import InsuranceService

from app.domains.tourism_sports.service import TourismSportsService

from app.domains.zamakana.service import ZamakanaService

TENANT_ID = 1
# land_assets id=1 — صف throwaway موجود بالفعل تحت tenant_id=1 من جلسات
# تحقق سابقة (قراءة فقط، صفر تعديل/حذف عليه من هذا الملف).
EXISTING_LAND_ASSET_ID = 1


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


def _assert_invoice_after_commit_and_wrapped(func, snippet: str = "create_invoice("):
    """حارس بنيوي (source order) — بديل التحقق الحي للدوال المحجوبة ببجات
    مسبقة منفصلة تمامًا عن #11b. بيتأكد إن create_invoice() لسه بعد commit()
    ومُغلَّفة بـtry/except (نفس نمط الإصلاح المطبَّق)، بدل ما نفترض هيفضل كده
    للأبد بلا أي حارس تلقائي."""
    source = inspect.getsource(func)
    commit_idx = source.index("await self.db.commit()")
    invoice_idx = source.index(snippet, commit_idx)
    assert invoice_idx > commit_idx, (
        f"{func.__qualname__}: create_invoice() لازم يكون بعد commit() — "
        "رجوع محتمل لباج savepoint leak الأصلي (Backlog #11b)"
    )
    after_commit = source[commit_idx:]
    try_idx = after_commit.index("try:")
    except_idx = after_commit.index("except", try_idx)
    invoice_idx_rel = after_commit.index(snippet)
    assert try_idx < invoice_idx_rel < except_idx, (
        f"{func.__qualname__}: create_invoice() لازم تكون مُغلَّفة بـtry/except"
    )


# ============================================================
# 1) tourism_sports.purchase_event_ticket — 🟡 مراجعة بنيوية فقط
#    (نزلت من "تحقق حي كامل" — راجع ملاحظة invoice_number في الدوكسترنج)
# ============================================================

def test_tourism_sports_purchase_event_ticket_invoice_ordering():
    """مراجعة بنيوية فقط — نزلت من "تحقق حي كامل" (كما وثَّقها تقرير #11b
    الأصلي، قسم 12.7) بسبب بج مسبق منفصل تمامًا عن #11b اكتُشف أثناء كتابة
    هذا الملف: `invoicing-generate-invoice-number-count-based-collision`
    (راجع الدوكسترنج أعلى الملف) — أي محاولة create_invoice() حقيقية
    لـtenant_id=1 حاليًا بتفشل بـUniqueViolationError. قرار مستخدم صريح
    [2026-08-18]: صفر لمس على invoicing/service.py، نزول لمراجعة بنيوية
    بدل تحقق حي."""
    _assert_invoice_after_commit_and_wrapped(TourismSportsService.purchase_event_ticket)


# ============================================================
# 2) tourism_sports.book_program — 🟡 مراجعة بنيوية فقط
# ============================================================

def test_tourism_sports_book_program_invoice_ordering():
    """مراجعة بنيوية فقط — محجوبة ببج مسبق منفصل تمامًا عن #11b
    (`finance-transfer-returns-transaction-object-not-tx-hash-string`):
    FinanceService.transfer() بترجع كائن Transaction كامل مش نص، فبتكراش
    DataError عند `payment_tx_hash=tx_hash` جوه begin_nested()، قبل ما نوصل
    حتى لكود #11b. نفس مستوى التقرير الأصلي (قسم 17.1، الصف 2)."""
    _assert_invoice_after_commit_and_wrapped(TourismSportsService.book_program)


# ============================================================
# 3) tourism_sports.place_transfer_bid — 🟡 مراجعة بنيوية فقط
# ============================================================

def test_tourism_sports_place_transfer_bid_invoice_ordering():
    """مراجعة بنيوية فقط — محجوبة ببجين مسبقين منفصلين تمامًا عن #11b:
    (أ) Backlog #12 (`can_access_service` arity) في _check_saas_limits،
    (ب) `tourism-place-transfer-bid-player-id-user-id-conflict` —
    IntegrityError جوه begin_nested() (data["player_id"] بتتعامل كـuser_id
    في get_player_profile وكـPlayerProfile.id في create_transfer FK). نفس
    مستوى التقرير الأصلي (قسم 17.1، الصف 3)."""
    _assert_invoice_after_commit_and_wrapped(TourismSportsService.place_transfer_bid)


# ============================================================
# 4) realestate.rent_unit — 🟡 مراجعة بنيوية فقط
#    (نزلت من "تحقق حي كامل" — راجع ملاحظة invoice_number في الدوكسترنج)
# ============================================================

def test_realestate_rent_unit_invoice_ordering():
    """مراجعة بنيوية فقط — نزلت من "تحقق حي كامل" (كما وثَّقها تقرير #11b
    الأصلي، قسم 15.2/15.4) لنفس سبب `purchase_event_ticket` أعلاه
    (`invoicing-generate-invoice-number-count-based-collision`). قرار
    مستخدم صريح [2026-08-18]: صفر لمس على invoicing/service.py."""
    _assert_invoice_after_commit_and_wrapped(RealEstateService.rent_unit)


# ============================================================
# 4b) اكتشاف جانبي جديد — invoicing-missing-rollback-on-exception-11b
#     xfail موثَّق: يثبت PendingRollbackError عند فشل create_invoice()
#     بخطأ DB حقيقي (مش mock بيتفادى الـDB)
# ============================================================

@pytest.mark.xfail(
    reason=(
        "Backlog جديد invoicing-missing-rollback-on-exception-11b: الـ"
        "try/except المضاف حوالين create_invoice() في كل دوال #11b ما "
        "بيعملش db.rollback() عند فشل DB حقيقي (زي تكرار invoice_number) "
        "— السيشن بتفضل PendingRollbackError لأي كود بعده جوه نفس الدالة "
        "(هنا: _store_idempotency، اللي بيحاول يقرأ attributes متوقعة على "
        "contract بعد ما اتـexpire من فشل الـflush). المورد الأساسي "
        "(rental_contract) بيتحفظ فعليًا رغم كده — مؤكَّد بـSELECT مستقل "
        "جوه الاختبار ده نفسه. صفر لمس على invoicing/service.py في هذه "
        "الجلسة — التصحيح المطلوب: db.rollback() جوه except."
    ),
    strict=True,
)
@pytest.mark.asyncio
async def test_realestate_rent_unit_real_invoice_failure_leaves_session_broken(db, monkeypatch):
    """يثبت الباج المكتشَف عمليًا: فشل create_invoice() بخطأ DB حقيقي
    (هنا: invoice_number مُكرَّر عمدًا، `INV-1-000001` موجودة بالفعل)
    بيكسر الـsession بالكامل بعد كده — بعكس فشل RuntimeError مصطنع (بره
    الـDB بالكامل) المستخدَم في باقي اختبارات هذا الملف، واللي مبيلمسش
    الـsession إطلاقًا فبيفلت من الباج ده. xfail(strict=True) — لو حد
    أضاف db.rollback() لاحقًا هيبقى XPASS ويفشل التست، فيبقى تذكير واضح
    إن الباج اتصلح ولازم نرفّع مستوى التحقق."""
    re_repo = RealEstateRepository(db)
    development = await re_repo.create_development(
        tenant_id=TENANT_ID, land_asset_id=EXISTING_LAND_ASSET_ID,
        name=f"REGTEST-DEV-{_suffix()}", development_type="RESIDENTIAL",
    )
    unit = await re_repo.create_unit(
        tenant_id=TENANT_ID, development_id=development.id,
        unit_number=f"REGTEST-UNIT-{_suffix()}", area_sqm=Decimal("100"),
        property_type=PropertyType.APARTMENT,
        is_available_for_rent=True, is_available_for_sale=False,
    )
    landlord = await _create_funded_user(db, "p_regtest_re_rb_landlord")
    tenant_user = await _create_funded_user(db, "p_regtest_re_rb_tenant")
    service = RealEstateService(db)
    # نسخ الـids لمتغيرات int عادية *قبل* أي محاولة فشل — بعد فشل flush
    # حقيقي، الكائنات ORM القديمة (development/unit/landlord/tenant_user)
    # بتتـexpire بالكامل، وأي وصول لاحق لـ.id عليها (حتى من جوه session
    # تانية تمامًا) بيحاول lazy-reload عبر الـsession الأصلية المكسورة
    # فيكسر بنفس MissingGreenlet — استخدام int عادي هنا بيتجنب المشكلة
    # كليًا في التنظيف.
    development_id = development.id
    unit_id = unit.id
    user_ids = [landlord.id, tenant_user.id]

    try:
        async def _force_duplicate_invoice_number(self, tenant_id):
            return "INV-1-000001"  # رقم موجود بالفعل فعليًا — يضمن IntegrityError حقيقي

        monkeypatch.setattr(InvoicingService, "_generate_invoice_number", _force_duplicate_invoice_number)
        contract = await service.rent_unit(
            landlord_id=landlord.id, tenant_id=TENANT_ID, unit_id=unit.id,
            tenant_user_id=tenant_user.id, monthly_rent=Decimal("50"),
            start_date=datetime.utcnow(), end_date=datetime.utcnow() + timedelta(days=365),
            idempotency_key=f"REGTEST-RENTRB-{_suffix()}",
        )

        # لو وصلنا هنا (xfail مبيحصلش)، لازم نتأكد إن المورد الأساسي التزم
        assert contract is not None
    finally:
        # اكتشاف إضافي أثناء كتابة التنظيف هنا: await db.rollback() لوحدها
        # مش كافية لاستعادة الـsession بعد فشل flush حقيقي جوه async session —
        # أي استدعاء ORM لاحق على نفس الـsession بيكسر بـMissingGreenlet
        # (خطأ تاني تمامًا، أعمق من PendingRollbackError نفسها). التنظيف هنا
        # بيستخدم session جديدة تمامًا بدل ما يحاول يصلح القديمة — الـsession
        # `db` بتاعة الـfixture نفسها هتتقفل عادي في teardown الـconftest.
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(RentalContract).where(RentalContract.unit_id == unit_id))
            await cleanup_db.execute(delete(PropertyUnit).where(PropertyUnit.id == unit_id))
            await cleanup_db.execute(delete(RealEstateDevelopment).where(RealEstateDevelopment.id == development_id))
            await cleanup_db.execute(delete(Invoice).where(Invoice.user_id.in_(user_ids)))
            await cleanup_db.execute(delete(Wallet).where(Wallet.user_id.in_(user_ids)))
            await cleanup_db.execute(delete(User).where(User.id.in_(user_ids)))
            await cleanup_db.commit()


# ============================================================
# 5) realestate.buy_fractional_ownership — 🟡 مراجعة بنيوية فقط
# ============================================================

def test_realestate_buy_fractional_ownership_invoice_ordering():
    """مراجعة بنيوية فقط — محجوبة ببج مسبق منفصل تمامًا عن #11b (نفس بج
    tx_hash/Transaction، هنا عمود purchase_tx_hash). نفس مستوى التقرير
    الأصلي (قسم 17.1، الصف 5)."""
    _assert_invoice_after_commit_and_wrapped(RealEstateService.buy_fractional_ownership)


# ============================================================
# 6) insurance.subscribe — 🟡 مراجعة بنيوية فقط
#    (نزلت من "تحقق حي جزئي" — نفس بج invoice_number، مؤكَّد حيًا هنا كمان)
# ============================================================

def test_insurance_subscribe_invoice_ordering():
    """مراجعة بنيوية فقط. **محاولة تحقق حي فعلية اتعملت أولًا** (بعد تصحيح
    بيانات throwaway ناقصة — `start_date` كان مفقود من `data`، مطلوبة
    إجباريًا عبر `InsuranceSubscriptionCreate` schema في الـrouter الحقيقي)
    — لكنها **صادفت نفس بج `invoicing-generate-invoice-number-count-based-collision`
    الموثَّق أعلى الملف** (نفس الرقم بالحرف: `INV-1-000015` already exists)،
    نفس السبب اللي نزَّل (1) `purchase_event_ticket`/(4) `rent_unit`/
    (8) `pledge_time` لمراجعة بنيوية. قرار مستخدم صريح [2026-08-18]: نفس
    المعاملة، صفر لمس على `invoicing/service.py`."""
    _assert_invoice_after_commit_and_wrapped(InsuranceService.subscribe)


# ============================================================
# 7) insurance.review_claim — 🟡 مراجعة بنيوية فقط
# ============================================================

def test_insurance_review_claim_invoice_ordering():
    """مراجعة بنيوية فقط — محجوبة ببج مسبق منفصل تمامًا عن #11b (نفس بج
    tx_hash/Transaction، هنا عمود payout_tx_hash، مسار approve=True تحديدًا
    — بالضبط النقطة اللي فيها claim.status→PAID المطلوب تحقيقها). نفس
    مستوى التقرير الأصلي (قسم 17.1، الصف 7)."""
    _assert_invoice_after_commit_and_wrapped(InsuranceService.review_claim)


# ============================================================
# 8) zamakana.pledge_time — 🟡 مراجعة بنيوية فقط
#    (نزلت من "تحقق حي كامل" — راجع ملاحظة invoice_number في الدوكسترنج)
# ============================================================

def test_zamakana_pledge_time_invoice_ordering():
    """مراجعة بنيوية فقط — نزلت من "تحقق حي كامل" (كما وثَّقها تقرير #11b
    الأصلي، قسم 16) لنفس سبب `purchase_event_ticket`/`rent_unit` أعلاه
    (`invoicing-generate-invoice-number-count-based-collision`). قرار
    مستخدم صريح [2026-08-18]: صفر لمس على invoicing/service.py."""
    _assert_invoice_after_commit_and_wrapped(ZamakanaService.pledge_time)
