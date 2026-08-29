# RealEstate — Amount Trust Check (buyFraction / tokenizeAsset)

**Session date:** 2026-08-29
**Type:** Investigation only — zero code edits until explicit approval
**Trigger:** Backlog priority review noticed `TokenizationExchange.tsx` computing
`(unit.sale_price_mrusdt * percentage) / 100` client-side. Question: does any
realestate endpoint trust a client-computed `amount` instead of recomputing it
server-side from DB values (Decimal)?

**Status:** IN PROGRESS

---

## Method

For each endpoint (buy_fractional_ownership / tokenizeAsset / rental /
revalue_land / any similar money-from-percentage-or-quantity logic):

1. Read `router.py` — what does the request schema accept?
2. Read `schemas.py` — is `amount` a client-supplied field, or are only raw
   inputs (percentage/quantity) accepted?
3. Read `service.py` — does the service recompute the amount from DB-sourced
   Decimal values, or does it use whatever came in the request body?
4. Classify: **SAFE** (server recomputes, ignores/rejects any client amount)
   or **DANGER** (server trusts a client-supplied final amount with no
   recomputation/validation against source-of-truth values).

If a DANGER case is found: STOP immediately, document it, do not proceed to
further endpoints until reviewed with the user.

---

## Findings log

### 1. `POST /realestate/units/{unit_id}/buy` — `buy_fractional_ownership` — **SAFE**

- **Schema** (`schemas.py:62-63`): `BuyFractionalOwnership` has exactly one field,
  `ownership_percentage: Decimal` (`gt=0, le=100`). **There is no `amount` field
  in this request model at all** — the client physically cannot send a final
  price.
- **Router** (`router.py:110-129`): passes only `percentage=data.ownership_percentage`
  into the service. No amount passed through.
- **Service** (`service.py:233-234`):
  ```python
  unit_price = cast(Decimal, unit.sale_price_mrusdt)   # DB-sourced Decimal
  cost = (unit_price * percentage) / Decimal(100)       # server-computed
  ```
  `unit.sale_price_mrusdt` comes from `self.repo.get_unit(unit_id)` (DB read),
  not from the request. `cost` is then what's actually transferred:
  `service.py:248` → `finance.transfer(..., amount=cost, ...)`, and what's
  invoiced: `service.py:297` → `invoicing.create_invoice(..., amount=cost, ...)`.
  The client-sent `percentage` is bounds-checked server-side too
  (`total_owned_dec + percentage > 100` → rejected, `service.py:230-231`).
- **Frontend cross-check** (`TokenizationExchange.tsx:96` + `services/realestate.ts:167-172`):
  the file that triggered this investigation does compute
  `(unit.sale_price_mrusdt * percentage) / 100` client-side (line 96), but
  it's used **only for on-screen display text** ("التكلفة: ..."). The actual
  mutation body sent to the backend (line 29) is
  `{ ownership_percentage: percentage }` — the computed number is never
  transmitted. Confirmed via the `BuyFractionalOwnership` type used by
  `RealEstateService.buyFraction` (`services/realestate.ts:167-171`), which
  has no `amount`/`cost` field.
- **Verdict: SAFE.** No amount is accepted from the client anywhere in this
  path; the server is the sole source of the charged amount, computed from a
  DB-read Decimal. The float-precision-abuse concern that motivated this
  investigation does not apply — the display-only frontend calculation never
  reaches the backend as authoritative data.

### 2. `POST /realestate/tokenize/{unit_id}` — `tokenize_asset` — **SAFE (different shape than feared, but see side-note)**

- **Schema** (`schemas.py:129-132`): `TokenizationCreate` = `total_shares: int`,
  `share_price_mrusdt: Decimal`, `minimum_investment_shares: int`. This is not
  a "computed final amount" field — it's the **offer terms** being defined for
  a brand-new tokenization record (there is no pre-existing share price in the
  DB to recompute from; this endpoint is what *sets* that price).
- **Service** (`service.py:458-489`): stores `total_shares`/`share_price` as
  given after confirming no tokenization already exists for the unit
  (`existing = await self.repo.get_tokenization_by_unit(...)`, `service.py:468-470`).
  No money moves in this call — no `finance.transfer`, no invoice creation.
  It only creates an `AssetTokenization` row.
- **No "buy tokenized shares" endpoint exists.** Searched
  `repository.py` for `buy_shares`/`invest_in_tokenization`/`purchase_shares`
  — none found. So there is currently no code path where a client sends a
  share quantity/percentage against an *existing* tokenization and the
  server (or client) computes a payment from it. If/when such a "buy shares"
  feature is added later, it must follow the same server-side-recompute
  pattern as `buy_fractional_ownership` above.
- **Verdict: SAFE for the amount-trust question as asked** — there is no
  client-supplied "final amount" being trusted, because this endpoint isn't a
  payment endpoint at all.
- **Side-note (authorization, not amount-trust — flagging, not acting):**
  `tokenize_asset` is reachable by any `get_current_active_user` (router.py:181-195,
  `Depends(get_current_active_user)`, not restricted to the unit/land owner or
  a superuser), and there's no ownership check against the unit in
  `service.py:458-489`. Any authenticated tenant user could tokenize any
  `unit_id` and set an arbitrary `share_price_mrusdt`. This is a distinct
  finding from the amount-trust question — not investigated further per the
  scope of this session; noting it so it isn't lost.

### 3. `PATCH /realestate/lands/{land_id}/revalue` — `revalue_land` — **SAFE by design**

- **Router** (`router.py:48-58`): `new_value: Decimal` accepted directly as a
  query param, but the endpoint is `Depends(get_current_superuser)` only.
  Client-supplied final value is expected and correct here — this endpoint's
  entire purpose is an admin declaring a new valuation, not a buyer paying a
  computed amount. No recomputation is applicable.

### 4. `POST /realestate/rentals` — `rent_unit` — **SAFE for amount-trust, but related authorization gap found — flagging only**

- **Schema** (`schemas.py:76-81`): `RentalContractCreate.monthly_rent_mrusdt: Decimal`
  (`gt=0`) is sent directly by the client and used as-is
  (`service.py:335`, `383`, `388`, `396`) for the contract and first invoice.
  This is **expected** in isolation — the landlord is supposed to set their
  own rent price, there's no "original value" to recompute from (unlike
  buy_fractional_ownership, where sale_price_mrusdt already exists on the
  unit as ground truth).
- **However:** `router.py:152` sets `landlord_id=user_id` from
  `current_user` (whoever calls the endpoint) with **no check that this user
  actually owns the unit or its underlying land/development**
  (`service.py:329-386` — `rent_unit` only checks
  `unit.is_available_for_rent`, never an ownership relationship). Combined
  with the client fully controlling `monthly_rent_mrusdt`, this means **any
  authenticated tenant user can call `POST /rentals` for any `unit_id`, name
  themself landlord, and set an arbitrary monthly rent**, which then drives a
  real invoice (`service.py:393-399`, `InvoicingService.create_invoice`)
  against `tenant_user_id`.
- **Verdict on the original amount-trust question: not the float-precision
  bug being hunted for** (no percentage-of-DB-value computation is being
  bypassed, since rent price has no authoritative source value to check
  against). **But this is a separate, real authorization/financial gap**
  (missing ownership check on `landlord_id`) surfaced incidentally while
  checking this endpoint's amount handling. Flagging per instructions — no
  code touched, awaiting review before deciding whether/how to fix.

### 5. `POST /realestate/smart-contracts` — `deploy_smart_contract` — **Not a payment path (informational only)**

- **Schema** (`schemas.py:145-180`): `contract_metadata` may contain
  `price`/`loan_amount`/`monthly_rent`/`lease_amount` depending on
  `contract_type`, but these are only presence-validated
  (`field_validator("contract_metadata")`, `schemas.py:150-180`) and then
  bleach-sanitized and stored as opaque JSON (`service.py:531-537`,
  `_sanitize_contract_metadata`). No `finance.transfer` or invoice call
  reads these values — the "amounts" inside are inert metadata attached to a
  simulated blockchain record (`_simulate_blockchain_deployment`,
  `service.py:604-610`, which just flips status to `CONFIRMED` after a 2s
  sleep). Restricted to `get_current_superuser` anyway. Not part of the
  amount-trust surface today; noting only in case this JSON is later wired
  into an actual transfer.

---

## Summary table

| Endpoint | Client sends | Server recomputes from DB? | Verdict |
|---|---|---|---|
| `POST /units/{id}/buy` (buy_fractional_ownership) | `ownership_percentage` only | Yes — `unit.sale_price_mrusdt * percentage / 100`, DB-sourced Decimal (`service.py:233-234`) | **SAFE** |
| `POST /tokenize/{id}` (tokenize_asset) | `total_shares`, `share_price_mrusdt` (offer terms, not a payment) | N/A — no payment occurs; sets new record | **SAFE** (amount-trust); auth gap noted separately |
| `PATCH /lands/{id}/revalue` | `new_value` | N/A — admin-declared value by design, superuser-only | **SAFE** |
| `POST /rentals` (rent_unit) | `monthly_rent_mrusdt` directly | No recomputation possible (no ground-truth rent value) — but **no ownership check on landlord_id** | **SAFE** (amount-trust as asked); **separate authorization gap found** |
| `POST /smart-contracts` | Arbitrary metadata incl. amount-like fields | N/A — not used in any transfer, superuser-only | Informational only |

## Overall conclusion

**No instance found of the feared bug** (client computing `sale_price * percentage / 100`
and the backend trusting that as a final chargeable `amount`). `buy_fractional_ownership`
— the exact endpoint named in the question — recomputes the cost server-side from a
DB-read `Decimal` and never accepts a client `amount` field; the frontend's local
`(unit.sale_price_mrusdt * percentage) / 100` in `TokenizationExchange.tsx:96` is
display-only and is not part of the request payload.

Two **separate, unrelated** issues were surfaced incidentally while reading these
files and are flagged for a follow-up decision (not investigated further, zero
code touched):
1. `tokenize_asset` has no ownership check — any active user can tokenize any unit.
2. `rent_unit` has no ownership check — any active user can create a rental
   contract for any unit as "landlord" and set an arbitrary monthly rent that
   drives a real invoice.

**STATUS (original amount-trust question): Investigation complete, buyFraction confirmed
SAFE — user reviewed and closed this question [2026-08-29].**

---

## URGENT — يتطلب إصلاح فوري

اكتشافين جانبيين (تفصيلهم فوق في قسمي 2 و4) اتقيّموا كـ**أخطر من السؤال
الأصلي** — بيسمحوا بتحكم غير مصرح به في موارد حقيقية/فواتير. قرار
المستخدم [2026-08-29]: نبدأ بـ`rent_unit` (الأخطر، بيولّد invoice حقيقي)،
بعدين `tokenize_asset` بنفس المنطق. صفر تنفيذ على أي حاجة تانية لحد ما
الاتنين يتقفلوا ويتحققوا حيًا.

### إصلاح #1 — `rent_unit` — ✅ CLOSED [2026-08-29]

**البج:** `router.py:152` كان بيمرر `landlord_id=user_id` (current_user اللي
بيستدعي الـendpoint) من غير أي تحقق إنه فعلاً مالك الوحدة. `service.py`
(قبل الإصلاح) كانت بتتأكد بس من `unit.is_available_for_rent` — أي مستخدم
authenticated كان يقدر يعمل `POST /realestate/rentals` لأي `unit_id`،
ينصب نفسه landlord، ويحدد `monthly_rent_mrusdt` كيفما شاء، وده بيولّد
invoice حقيقي ضد `tenant_user_id` (`service.py:392-399`).

**الإصلاح المُطبَّق** (`eppne-backend/app/domains/realestate/service.py`،
داخل `rent_unit`، مباشرة بعد جلب الـunit وقبل `create_rental_contract`):

```python
owner = await self._get_land_owner_for_unit(unit, tenant_id)
if cast(int, owner.id) != landlord_id:
    raise PermissionDeniedError("ليس لديك صلاحية تأجير هذه الوحدة")
```

نفس النمط المستخدَم بالفعل في `buy_fractional_ownership` (نفس الدالة
المساعدة `_get_land_owner_for_unit`، بتتبّع unit → development →
land_asset → owner_id). `PermissionDeniedError` → HTTP 403
(`core/errors.py:39-41`).

**التحقق الحي** — ملف اختبار جديد
`eppne-backend/tests/test_realestate_rent_unit_ownership_check.py`
(صفر mock على `rent_unit` نفسها أو على تحقق الـownership — قاعدة بيانات
حقيقية):

- `test_rent_unit_succeeds_for_real_owner`: بيبني سلسلة
  land_asset(owner_id=المالك الحقيقي) → development → unit جديدة بالكامل،
  وبيستدعي `rent_unit` بـ`landlord_id=` نفس المالك → **نجح**، العقد اتسجل
  فعليًا، اتأكد بـSELECT مستقل من DB (`landlord_user_id == real_owner.id`).
  **PASSED.**
- `test_rent_unit_rejects_non_owner_with_403`: نفس السلسلة، لكن
  `landlord_id=` مستخدم تاني (مهاجم، مش مالك الوحدة أبدًا) → **اترفض
  بـ`PermissionDeniedError`** (403). اتأكد بـSELECT مستقل من DB إن **مفيش**
  أي `RentalContract` اتسجل للمهاجم. **PASSED.**

  ```
  tests/test_realestate_rent_unit_ownership_check.py::test_rent_unit_succeeds_for_real_owner PASSED
  tests/test_realestate_rent_unit_ownership_check.py::test_rent_unit_rejects_non_owner_with_403 PASSED
  ================== 2 passed, 8 warnings in 63.09s ==================
  ```

**ملاحظة شفافية عن التحقق الحي:** المسار الشرعي صادف بج مسبق **موثَّق
تمامًا ومنفصل عن هذا الإصلاح** —
`invoicing-generate-invoice-number-count-based-collision` (موثَّق أصلًا في
`test_realestate_insurance_savepoint.py`، جلسة #11b) — بيمنع أي
`create_invoice()` حقيقي لـ`tenant_id=1` حاليًا (تصادم unique constraint
على `invoice_number`)، واللي بيولّد كمان بج ثانٍ موثَّق
(`invoicing-missing-rollback-on-exception-11b`، الـsession بتفضل
`PendingRollbackError` بعد فشل الفاتورة). **صفر لمس على
`invoicing/service.py`** — الاختبار الشرعي بيستخدم `monkeypatch` لـ
`InvoicingService._generate_invoice_number` بس (يرجّع رقم فريد)، عشان
يتجاوز البج غير المرتبط ده ويتحقق من دالة `rent_unit` نفسها (بما فيها
تحقق الـownership الجديد) حقيقي 100% بلا أي stub على الكود تحت الاختبار.
نفس النمط المستخدَم في ملف #11b (monkeypatch لنفس الدالة، لغرض عكسي هناك).

### إصلاح #2 — `tokenize_asset` — ✅ CLOSED [2026-08-29]

**البج:** `router.py` كانت بتستدعي `service.tokenize_asset(...)` من غير ما
تمرر `current_user.id` أصلًا. `service.py` (قبل الإصلاح) ما كانتش بتتحقق
من أي علاقة ownership بين الـcaller والوحدة — أي مستخدم authenticated
كان يقدر يعمل tokenize لأي `unit_id` بأي `share_price_mrusdt` يحدده هو.

**الإصلاح المُطبَّق:**
- `router.py:189-195` — بيمرر دلوقتي `initiator_id=cast(int, current_user.id)`.
- `service.py` (داخل `tokenize_asset`، بارامتر جديد `initiator_id: int`،
  مباشرة بعد `_check_saas_limits` وقبل فحص "already tokenized"):
  ```python
  unit = await self.repo.get_unit(unit_id)
  if not unit:
      raise NotFoundError("الوحدة غير موجودة")

  owner = await self._get_land_owner_for_unit(unit, tenant_id)
  if cast(int, owner.id) != initiator_id:
      raise PermissionDeniedError("ليس لديك صلاحية تجزئة هذه الوحدة")
  ```
  نفس النمط المستخدَم في `rent_unit`/`buy_fractional_ownership`.

**التحقق الحي** — ملف اختبار جديد
`eppne-backend/tests/test_realestate_tokenize_asset_ownership_check.py`:

- **مسار الهجوم (`test_tokenize_asset_rejects_non_owner_with_403`): ✅
  PASSED — تحقق حي كامل وقاطع.** مستخدم مش مالك الوحدة بيحاول
  `tokenize_asset` → اترفض بـ`PermissionDeniedError`، وأكدنا بالتحديد إن
  الرسالة هي **رسالة تحقق الـownership نفسها** ("ليس لديك صلاحية تجزئة
  هذه الوحدة") وليست رسالة بوابة تانية (`pytest.raises(...,
  match="ليس لديك صلاحية تجزئة هذه الوحدة")`) — ده مهم لأن فيه بوابة
  SaaS سابقة بترفض بنفس نوع الاستثناء (`PermissionDeniedError`) لسبب
  مختلف تمامًا (تفصيل تحت)، فلازم نتأكد إن الرفض جاي من تحقق الملكية
  الجديد فعليًا مش false positive. اتأكد كمان بـSELECT مستقل من DB إن
  مفيش `AssetTokenization` اتسجلت للمهاجم.

- **مسار الشرعية (`test_tokenize_asset_succeeds_for_real_owner`): 🟡
  تحقق حي جزئي فقط — اتوقف على بج تاني مكتشَف حديثًا، منفصل تمامًا عن هذا
  الإصلاح (تفصيل كامل تحت). المالك الحقيقي عدّى تحقق الـownership الجديد
  بنجاح (مفيش أي `PermissionDeniedError` من كودي)، لكن الاستدعاء فشل بعد
  كده بخطأ DB مختلف تمامًا قبل ما يوصل لـ`return`.**

**بوابتين سابقتين اتصادفوا أثناء التحقق الحي (اتعزلوا بـ`monkeypatch`
داخل الاختبار بس، صفر لمس على الكود الحقيقي):**

1. **بوابة SaaS (`_check_saas_limits`)** — خطة اشتراك `tenant_id=1`
   (throwaway/regtest) ما فيهاش feature `"real_estate_tokenization"`
   مفعّلة، فأي استدعاء حقيقي (مالك أو مهاجم) كان هيترفض من البوابة دي
   **قبل** ما يوصل لتحقق الـownership أصلًا — ده كان هيخلي اختبار
   الهجوم "ينجح" لسبب غلط (false positive). اتعزلت بـ`monkeypatch` لـ
   `RealEstateService._check_saas_limits` (no-op) في الاختبارين، عشان
   تحقق الـownership يبقى هو الفيصل الوحيد. صفر لمس على
   `saas/service.py` أو بيانات الاشتراك.

2. **🔴 بج جديد مكتشَف الآن، غير موثَّق سابقًا، ومنفصل تمامًا عن هذا
   الإصلاح — `token_symbol` عمود ضيق جدًا للقيمة اللي بتتولّد فعليًا:**
   - `models.py:244`: `token_symbol = Column(String(10), nullable=True)`
   - `service.py` (داخل `tokenize_asset`، قبل وبعد إصلاحي):
     `token_symbol=f"EPPNE-RE-{unit_id}-{uuid.uuid4().hex[:4].upper()}"`
     — الصيغة دي بتولّد نص **17+ حرف دايمًا** (حتى `unit_id` برقم واحد:
     `"EPPNE-RE-1-XXXX"` = 15 حرف)، أطول من عمود `VARCHAR(10)` بكتير.
   - **النتيجة: أي استدعاء حقيقي لـ`tokenize_asset` — بغض النظر تمامًا
     عن هوية الـcaller أو صحة تحقق الـownership — بيفشل حاليًا
     بـ`StringDataRightTruncationError` (Postgres) عند الـINSERT.**
     مؤكَّد حيًا:
     ```
     sqlalchemy.exc.DBAPIError: StringDataRightTruncationError:
     value too long for type character varying(10)
     [parameters: (1, 89, 1000, Decimal('10'), 1, True, False, None,
     'EPPNE-RE-89-C9D6')]
     ```
   - **ده بج وظيفي حقيقي وقائم بذاته (مش عيب بيئة اختبار زي تصادم
     invoice_number) — الـendpoint معطّل بالكامل في أي بيئة حاليًا،
     بغض النظر عن هذا الإصلاح.** صفر لمس عليه من غير موافقة صريحة —
     محتاج قرار: نوسّع العمود (`String(10)` → مثلاً `String(30)`
     migration جديدة) ولا نقصّر صيغة التوليد في `service.py`؟

**قرار المستخدم [2026-08-29]:** نفّذ migration بسيطة توسّع `token_symbol`
من `VARCHAR(10)` لـ`VARCHAR(30)` (كافية للصيغة الحالية حتى مع `unit_id`
كبير)، بعدين أكمل التحقق الحي الكامل.

**الإصلاح المُطبَّق لبج `token_symbol` (منفصل تمامًا عن إصلاح الـownership،
نطاق موسَّع بموافقة صريحة):**
- migration جديدة: `migrations/versions/041_widen_asset_tokenizations_token_symbol.py`
  (`down_revision = '040_...'`) — `ALTER COLUMN token_symbol TYPE VARCHAR(30)`.
- `models.py:244`: `token_symbol = Column(String(10), ...)` →
  `Column(String(30), ...)` (مطابقة للـmigration).
- اتنفذت فعليًا: `alembic upgrade head` → نجحت (`040_... → 041_...`).

**التحقق الحي الكامل بعد الـmigration (إعادة تشغيل الاختبارين):**

```
tests/test_realestate_tokenize_asset_ownership_check.py::test_tokenize_asset_succeeds_for_real_owner PASSED
tests/test_realestate_tokenize_asset_ownership_check.py::test_tokenize_asset_rejects_non_owner_with_403 PASSED
======================= 2 passed, 3 warnings in 46.85s ========================
```

- **مسار الشرعية: ✅ نجح للنهاية الطبيعية الآن.** المالك الحقيقي عمل
  `tokenize_asset` → `AssetTokenization` اتسجلت فعليًا (اتأكد بـSELECT
  مستقل: `unit_id` و`total_shares` مطابقين).
- **مسار الهجوم: ✅ لسه بيترفض بـ403 برسالة تحقق الـownership بالتحديد.**

**الخلاصة النهائية:** تحقق الـownership في `tokenize_asset` **مُطبَّق،
صحيح، ومتحقق منه حيًا 100%** لكلا المسارين (شرعي + هجوم)، وبج
`token_symbol` غير المرتبط اتصلح كمان بموافقة صريحة ومُتحقَّق منه حيًا
كجزء من نفس دورة الاختبار.

---

## الحالة النهائية — كلا الإصلاحين مقفولين ومتحققين حيًا 100%

| # | الدالة | الإصلاح | مسار شرعي (حي) | مسار هجوم (حي، 403) | ملاحظات |
|---|---|---|---|---|---|
| 1 | `rent_unit` | تحقق `owner.id == landlord_id` عبر `_get_land_owner_for_unit` | ✅ PASSED | ✅ PASSED | تجاوز بج invoice_number غير مرتبط بـ`monkeypatch` داخل الاختبار فقط |
| 2 | `tokenize_asset` | تحقق `owner.id == initiator_id` (باراميتر جديد، ممرَّر من الراوتر) + إصلاح `token_symbol` (migration 041) | ✅ PASSED | ✅ PASSED | بج SaaS-gate + بج token_symbol اتعزلوا/اتصلحوا بشفافية كاملة |

**الملفات المتأثرة (كل التغييرات موثَّقة بالتفصيل فوق):**
- `eppne-backend/app/domains/realestate/router.py` — تمرير `initiator_id`
- `eppne-backend/app/domains/realestate/service.py` — تحقق ownership في `rent_unit` و`tokenize_asset`
- `eppne-backend/app/domains/realestate/models.py` — `token_symbol` VARCHAR(10)→VARCHAR(30)
- `eppne-backend/migrations/versions/041_widen_asset_tokenizations_token_symbol.py` — migration جديدة
- `eppne-backend/tests/test_realestate_rent_unit_ownership_check.py` — اختبارين جدد
- `eppne-backend/tests/test_realestate_tokenize_asset_ownership_check.py` — اختبارين جدد

**STATUS: كل حاجة مقفولة ومتحققة حيًا. جاهز للـcommit بموافقة المستخدم.**
