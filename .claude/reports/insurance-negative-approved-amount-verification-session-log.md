# جلسة: التحقق من `review_claim` (insurance) — مبلغ `approved_amount` سالب يعكس التحويل

**التاريخ:** 2026-09-23
**البند:** `insurance-review-claim-negative-approved-amount-reverses-transfer` (مُعلَّم في تقرير `insurance-review-claim-double-payment-verification-session-log.md` §6، §11 — "غير مُتحقَّق حيًّا").
**القواعد:** قراءة فقط حتى الآن. لا تعديل كود، لا staging/commit، لا كتابة في `PROGRESS_LOG.md`، لا push.
**الحالة:** الخطوة 1 (قراءة) + الخطوة 2 (تشخيص) مكتملتان — **متوقف بانتظار موافقة المستخدم.** لم يُلمس أي كود.

---

## 0. الخلاصة التنفيذية

- **الثغرة في طبقة التطبيق حقيقية** (لا يوجد أي فحص `amount > 0` في `review_claim` ولا في `FinanceService.transfer/hold_funds/release_held_funds/settle_held_funds`).
- **لكن سرقة الأموال الموصوفة في الفرضية لا يمكن أن تُحفَظ فعليًا** — قاعدة البيانات الحية تحتوي على CHECK constraints تمنعها:
  - `transactions.check_transaction_amount_positive` → `CHECK (amount > 0)`
  - `wallets.check_wallet_balances_non_negative` و `check_wallet_held_balances_non_negative`
  - `invoices.check_amount_non_negative` → `CHECK (amount >= 0)`
- كل مسارات تحريك الأموال الأربعة تُدرج صف `Transaction` داخل نفس `begin_nested()` مع تحديث المحافظ، ولا يوجد أي `commit` داخل المسار → الـ INSERT بمبلغ سالب يفشل بـ`IntegrityError` → الـsavepoint يُلغى بالكامل → الأرصدة لا تتغير، والمطالبة تبقى `SUBMITTED`.
- **التصنيف الصحيح:** ليس "سرقة أموال" بل **"الدفاع الوحيد هو قاعدة البيانات" + خطأ 500 غير مُعالَج بدل 4xx نظيف** (لا يوجد `exception_handler` لـ`IntegrityError` في `app/main.py`).
- **اكتشاف جانبي حقيقي:** `approved_amount=0` → `final_amount = approved_amount or claimed` → `Decimal('0')` قيمة falsy → **يُدفع كامل المبلغ المطالب به** بدل صفر. سلوك مفاجئ (من مال المراجِع نفسه، ليس سرقة).
- التحقق من القيود تم بقراءة `pg_constraint` في الحاوية `eppne_db` — **لم يُنفَّذ الاستغلال حيًّا بعد** (مقترح في §5 كخطوة أولى قبل أي إصلاح).

---

## 1. الخطوة 1.1 — `review_claim` بعد commit `88097be`

- `eppne-backend/app/domains/insurance/router.py:225`:
  ```python
  approved_amount: Optional[Decimal] = Query(None, description="المبلغ المعتمد (إن كانت الموافقة)"),
  ```
  لا `gt=0` ولا `ge=0`. (للمقارنة: `schemas.py:101` فيه `approved_amount_mrusdt ... ge=0` لكنه غير مستخدم في هذا المسار.)
- `eppne-backend/app/domains/insurance/service.py:524-526`:
  ```python
  final_amount = approved_amount or cast(Decimal, claim.claimed_amount_mrusdt)
  if final_amount > cast(Decimal, policy.max_coverage_limit_mrusdt):
      final_amount = cast(Decimal, policy.max_coverage_limit_mrusdt)
  ```
  حد أعلى فقط. لا حد أدنى. → **الفجوة ما زالت موجودة (مؤكَّد).**
- إصلاح اليوم (قفل الصف + فحص الحالة + مفتاح حتمي `claim_payout_{claim_id}`) لا يمس هذه الفجوة.
- ملاحظة: `approved_amount=0` → يسقط إلى `claimed_amount` (بسبب `or`).
- ملاحظة: `approved_amount > claimed_amount` مسموح (حتى سقف البوليصة) — من مال المراجِع نفسه؛ خارج النطاق.

## 2. الخطوة 1.2 — `finance/service.py`

| الدالة | الأسطر | فحص `amount > 0`؟ | ماذا يحدث بمبلغ سالب (منطقيًا) | ماذا يحدث فعليًا (DB) |
|---|---|---|---|---|
| `transfer` | 58-147 | **لا** | `sender_current < amount` دائمًا False → رصيد المرسل يزيد، المستلم ينقص | UPDATE المستلم قد يفشل بـ wallet CHECK إن صار سالبًا؛ وإلا INSERT `transactions` يفشل بـ `amount > 0` → rollback |
| `hold_funds` | 149-210 | **لا** | الرصيد المتاح يزيد، المحجوز ينقص (يصبح سالبًا) | held CHECK أو transactions CHECK → rollback |
| `release_held_funds` | 212-270 | **لا** | المحجوز يزيد، المتاح ينقص | transactions CHECK → rollback |
| `settle_held_funds` | 272-362 | **لا** (مُضافة للقائمة — لم تُذكر في الفرضية) | محجوز المرسل يزيد، رصيد المستلم ينقص | نفسه → rollback |
| `swap` | ~364 | لا في الخدمة، لكن `SwapRequest.amount_in` فيه `gt=0` | — | — |

- **مسار الكتابة** (`finance/repository.py:51-94`): `update_balances` / `update_wallet_funds` / `tx_repo.create` كلها `flush()` فقط — **لا commit داخلي** → الـsavepoint يغطي كل شيء.
- `identity/repository.py:286` فيه `update_balances` مكرر — **صفر مستدعين** (تم التحقق بـgrep). لا توجد كتابة أرصدة تتجاوز `FinanceService`.
- **القيود الحية** (استعلام `pg_constraint` على `eppne_db`/`eppne_v2`):
  ```
  wallets|check_wallet_balances_non_negative|CHECK (MR_POUND/MR_USDT/MR7/NBT/MRX >= 0)
  wallets|check_wallet_held_balances_non_negative|CHECK (... >= 0)
  transactions|check_transaction_amount_positive|CHECK ((amount > (0)::numeric))
  invoices|check_amount_non_negative|CHECK ((amount >= (0)::numeric))
  ```
  ملاحظة: wallet CHECK يغطي 5 عملات فقط (ليس `LOYALTY_POINTS`)، لكن `transactions` CHECK يغطي كل العملات — وهو الحاجز الحاسم.

## 3. الخطوة 1.3 — كل مواقع الاستدعاء وتصنيفها

المفتاح:
- **A** = مبلغ من مدخلات المستخدم مباشرة **بدون** قيد موجب في الأعلى.
- **B** = سعر مخزَّن يضعه مستخدم آخر (تاجر/منشئ) عبر schema **بدون** `gt/ge` — ولا يوجد حارس `> 0` قبل الاستدعاء.
- **S** = آمن (قيد `gt=0` في الأعلى، أو حارس `if x > 0`، أو قيمة ثابتة/محسوبة خادميًا من مصدر مقيَّد).

| # | الموقع | المبلغ | التصنيف | السبب |
|---|---|---|---|---|
| 1 | `insurance/service.py:530` (review_claim) | `approved_amount` (Query) | **A** | لا قيد في `router.py:225` |
| 2 | `finance/router.py:47` | `req.amount` | S | `TransferRequest.amount gt=0` (`finance/schemas.py:17`) |
| 3 | `social/service.py:590` (request_physical_gift) | `product_price` | **A** | `social/schemas.py:169` بلا قيد |
| 4 | `projects/service.py:185` (contribute) | `data.amount_mrusdt` | **A** | `projects/schemas.py:69` بلا قيد؛ لا حارس `> 0` |
| 5 | `transport/service.py:478` (book_trip → hold_funds) | `base_fare * seats_count` | **A** | `transport/schemas.py:131` `seats_count` بلا قيد → أجرة سالبة |
| 6 | `affiliate/service.py:576` | `amount` | S | `schemas.py:197 gt=0` + `>= min_withdrawal` |
| 7 | `sovereign_entities/service.py:411` | `amount` | S | `schemas.py:167 gt=0` |
| 8 | `sovereign_entities/service.py:483` | `amount` | S | `schemas.py:174 gt=0` |
| 9 | `realestate/service.py:311` | `price * percentage/100` | S* | `ownership_percentage gt=0, le=100`؛ السعر المخزَّن غير مفحوص هنا (B جزئي) |
| 10 | `tenders_auctions/service.py:415` (hold) | `bid_amount` | S | `>= current_highest + increment`؛ `start_price gt=0` |
| 11 | `tenders_auctions/service.py:482` (release) | مبلغ مزايدة مخزَّن | S | نفس المبلغ المحجوز سابقًا |
| 12 | `tenders_auctions/service.py:493` (settle) | مبلغ مزايدة مخزَّن | S | نفسه |
| 13 | `invitations/service.py:643` | `budget_mrusdt` | S | `ge=0` + حارس `if budget > 0` |
| 14 | `academy/service.py:365` | سعر الدورة | S | حارس `amount > 0` |
| 15 | `arbitration_syndicates/service.py:337` | رسوم سنوية | S | حارس `fee > 0` |
| 16 | `digital_twin/service.py:177` | `fee * duration_minutes` | S | حارس `fee > 0` (لكن انظر §4.3) |
| 17 | `service_marketplace/service.py:191, 362, 399` | أسعار مخزَّنة | S | حراس `> 0` |
| 18 | `tasks/billing.py:351` | اشتراك التوأم | S | حارس `> 0` |
| 19 | `health/service.py:262` | `Decimal("10.00")` | S | ثابت |
| 20 | `insurance/service.py:226` | `base_premium` | S | حارس `> 0` + `gt=0` |
| 21 | `insurance/service.py:309` (renew) | `base_premium` | S | `schemas.py:20,34 gt=0` |
| 22 | `insurance/service.py:649` (pensions) | `monthly_amount` | S | `schemas.py:127,134 gt=0` |
| 23 | `invoicing/service.py:189` | `invoice.amount` | S | `invoicing/schemas.py:12 gt=0` + DB `>= 0` |
| 24 | `saas/service.py:703` | `invoice.amount` | S | نفسه |
| 25 | `saas/service.py:292` | `plan.price_monthly` | B (مسؤول) | `saas/schemas.py:39` بلا قيد — لكن يضعه مسؤول المنصة |
| 26 | `commerce/service.py:174` (checkout) | مجموع `price * qty` | **B** | `commerce/schemas.py:44,50` السعر/الجملة بلا قيد (`quantity gt=0`) |
| 27 | `commerce/service.py:527` (retry) | `order.total_amount` | B | مشتق من #26 |
| 28 | `tourism_sports/service.py:184` | `program.base_price` | **B** | `schemas.py:44` بلا قيد |
| 29 | `tourism_sports/service.py:342` | `event.base_ticket_price * mult (+50)` | **B** | `schemas.py:97` بلا قيد |
| 30 | `transport/service.py:388, 571` | `booking.fare_paid` | B | مشتق من #5 و `base_fare` (`schemas.py:101` بلا قيد) |
| 31 | `transport/service.py:609, 757, 814` | `delivery_fee` | **B** | `schemas.py:157` بلا قيد |
| 32 | `social/service.py:679` | سعر خطة المجموعة | **B** | `schemas.py:184-185` بلا قيد |
| 33 | `social/service.py:523` | `gift_value` | S | حارس `> 0` |
| 34 | `iot/service.py:219` | `credits * 50` | S* | "تُحسب تلقائيًا" خادميًا — لم أتتبع مصدر القراءات بالكامل |
| 35 | `tasks/employment.py:313` | `payroll.net_salary` | B | `employment/schemas.py:70 base_salary` بلا قيد — يضعه صاحب العمل نفسه (من ماله) |

**الخلاصة:** 4 مواقع فئة **A**، ~9 فئة **B**. **في الحالتين النتيجة الفعلية اليوم = 500 + rollback، وليس نقل أموال**، بفضل CHECK في DB.

## 4. الخطوة 2 — التشخيص

### 4.1 هل هي ثغرة حقيقية؟

**جزئيًا — لكن ليس بالشكل المفترض.**
- ❌ **سرقة الأموال عبر مبلغ سالب: مدحوضة على مستوى الكود+القيود** (لم تُثبت حيًّا بعد). `tx_repo.create` بمبلغ سالب ينتهك `check_transaction_amount_positive` داخل نفس الـsavepoint مع تحديثات المحافظ → rollback كامل؛ المطالبة تبقى `SUBMITTED`؛ لا فاتورة (تُنشأ بعد commit ولا يصل التنفيذ إليها).
- ✅ **حقيقي:** طبقة التطبيق لا تتحقق إطلاقًا — الدفاع الوحيد هو DB. أي migration يُسقط/يُعدّل القيد، أو أي عملة جديدة/مسار لا يُدرج صف `Transaction`، يفتح الثغرة كاملة.
- ✅ **حقيقي:** مبلغ غير موجب → `IntegrityError` غير مُعالَج → **HTTP 500** (بدل 400/422) في كل المواقع A و B.
- ✅ **حقيقي (اكتشاف جانبي):** `approved_amount=0` يدفع كامل المطالبة (§1).

### 4.2 الخطورة

منخفضة–متوسطة (hardening + تصحيح كود الخطأ)، **ليست** HIGH. لا يوجد مسار سرقة قابل للاستغلال اليوم وفق القراءة.

### 4.3 اكتشافات جانبية (غير مُصلحة، للتسجيل فقط)

- `digital_twin`: `duration_minutes` بلا قيد → قيمة سالبة تجعل `fee < 0` → يتخطى الدفع (`if fee > 0`) → تفاعل مجاني يُسجَّل بمدة سالبة. ليس عكس أموال.
- أسعار الفئة B (commerce/tourism/transport/social/saas/employment): مستخدم يضع سعرًا سالبًا → المشتري يحصل على 500. يُقترح backlog منفصل لـ`ge=0` على schemas الأسعار.

## 5. الخطوة 2.3 — الإصلاح المقترح (الحد الأدنى)

**(1) حارس مركزي في `FinanceService`** — في `transfer` و`hold_funds` و`release_held_funds` و`settle_held_funds`، مباشرة بعد `amount_decimal = Decimal(str(amount))`:
```python
if amount_decimal <= 0:
    raise ValidationError("المبلغ يجب أن يكون أكبر من صفر")
```
- يحوّل الـ500 إلى 4xx نظيف في **كل** الـ~45 موقع دفعة واحدة، ويجعل التطبيق لا يعتمد على DB وحده.
- **لا تراجع لأي تدفق شرعي:** أي مبلغ `<= 0` يفشل اليوم أصلًا في DB (`amount > 0`)؛ المواقع ذات الحراس `if x > 0` لا تصل للاستدعاء أصلًا.
- مخطط الترتيب: في `transfer`/`settle` بعد فحص `idempotency_key` الفارغ — **قبل** البحث عن المستلم (تجنب استعلامات بلا فائدة). في `hold`/`release` قبل فحص الـidempotency (حاليًا `amount_decimal` يُحسب قبله أصلًا).

**(2) قيد `gt=0` في `insurance/router.py:225`** (موضوع الجلسة):
```python
approved_amount: Optional[Decimal] = Query(None, gt=0, description=...)
```
- يغلق أيضًا اكتشاف `approved_amount=0` (يصبح 422) دون لمس منطق `or` في الخدمة.

**(3) قيود schema لمدخلات المستخدم الأخرى من فئة A** — مقترحة، أوصي بتضمينها لكنها قابلة للفصل:
- `social/schemas.py:169` `product_price_mrusdt` → `gt=0`
- `projects/schemas.py:69` `amount_mrusdt` → `gt=0` (Optional، `None` يبقى مسموحًا للمساهمات غير النقدية)
- `transport/schemas.py:131` `seats_count` → `ge=1`

**خارج النطاق (backlog مقترح):** فئة B (أسعار التجار/المنشئين) + `digital_twin.duration_minutes` + إضافة `exception_handler` عام لـ`IntegrityError`.

**لا يُلمس:** كل المواقع المصنفة S.

## 6. الخطوة 2.4 — خطة التحقق الحي

**قبل الإصلاح (على tenant مؤقت):**
1. إعداد: tenant جديد، مستخدم مراجِع (OWNER على الكيان المُصدِر) برصيد MR_USDT (مثلاً 500)، مستخدم مُطالِب برصيد (مثلاً 200)، بوليصة، اشتراك، مطالبة `SUBMITTED`.
2. `PUT /insurance/claims/{id}/review?approve=true&approved_amount=-50` → تسجيل: كود HTTP (المتوقع 500)، نص الخطأ في اللوج (المتوقع `check_transaction_amount_positive` أو `check_wallet_balances_non_negative`).
3. التحقق من DB: رصيد المراجِع والمُطالِب **بلا تغيير**، المطالبة `SUBMITTED`، لا صف `transactions` بمفتاح `claim_payout_{id}`، لا فاتورة.
4. استدعاء مباشر على مستوى الخدمة (سكربت في scratchpad): `transfer(-10)`، `hold_funds(-10)`، `release_held_funds(-10)`، `settle_held_funds(-10)` → المتوقع `IntegrityError` لكل منها، والأرصدة بلا تغيير — لإثبات أن DB هو الحاجز الوحيد.
5. (اختياري) `approved_amount=0` على مطالبة ثانية → إثبات أنه يدفع المبلغ الكامل (اكتشاف §1).
6. نفس الشيء لـ`POST` physical gift بـ`product_price=-10` و booking بـ`seats_count=-1`.

**بعد الإصلاح:**
1. نفس الطلب → **422** (Query validation)، لا أثر في DB.
2. المسارات الأربعة على مستوى الخدمة بـ`-10` و`0` → `ValidationError` (قبل أي SQL)، الأرصدة بلا تغيير.
3. المسار الشرعي: `approve=true&approved_amount=50` → `PAID`، المراجِع −50، المُطالِب +50، صف transaction واحد.
4. `approved_amount=0` → 422.
5. اختبار pytest جديد (مقترح: `tests/test_finance_non_positive_amount_guard.py`) + إعادة تشغيل مجموعات: insurance double-payment، finance/FINBIND، transport hold/settle، tenders auctions — المطلوب صفر تراجع (مع استثناء الإخفاقات المعروفة مسبقًا "Backlog #8").
6. تنظيف صفوف الـtenant المؤقت (أو الإبقاء عليها كما في الجلسات السابقة — حسب قرارك).

---

## 7. الحالة (نهاية الجولة الأولى)

- لم يُعدَّل أي ملف كود. الملف الوحيد المكتوب: هذا التقرير.
- **بانتظار موافقة المستخدم** على: (أ) تشغيل التحقق الحي قبل الإصلاح، (ب) نطاق الإصلاح (1)+(2) إلزامي، (3) اختياري.

---

## 8. قرارات المستخدم (الجولة الثانية)

1. **نعم** — تشغيل إثبات "قبل الإصلاح" أولًا كما في §6، بنفس انضباط باقي جلسات اليوم.
2. **لا** — البند (3) من §5 (قيود schema على `product_price_mrusdt` و`amount_mrusdt` و`seats_count`) **يُستبعد من هذه الجلسة** ويُوثَّق كبنود backlog منفصلة (§11). السبب كما ذكره المستخدم: الحارس المركزي في `FinanceService` هو الإصلاح الحقيقي، يوقف أي مبلغ سالب مهما كان مصدره؛ قيود الـschema دفاع إضافي مرغوب وليست ضرورية لإغلاق الثغرة.
3. **النطاق النهائي:** الدوال الأربع في `FinanceService` + `gt=0` على `approved_amount` في `insurance/router.py` فقط.
4. **الترتيب:** إثبات قبل ← تطبيق الإصلاح ← تحقق بعد ← regression ← عرض خطة التنظيف قبل تشغيلها ← الـdiff في التقرير ← توقف قبل staging/commit.
5. المستخدم طلب رؤية التقرير الكامل قبل الموافقة النهائية على خطة التحقق الحي — **لم يُشغَّل شيء بعد.**

## 9. الـdiff المقترح الكامل (لم يُطبَّق)

### 9.1 `eppne-backend/app/domains/finance/service.py` — `transfer` (حول السطر 68)

```diff
@@ async def transfer(
         if not idempotency_key:
             raise ValidationError("Idempotency key is required")
 
+        # حارس المبلغ: مبلغ <= 0 كان يعكس اتجاه التحويل منطقيًا (فحص الرصيد يمر دائمًا)،
+        # والحاجز الوحيد كان CHECK في DB (500 بدل 4xx)
+        amount_decimal = Decimal(str(amount))
+        if amount_decimal <= 0:
+            raise ValidationError("المبلغ يجب أن يكون أكبر من صفر")
+
         existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
         if existing_tx:
@@
         if crypto_mode == "POINTS_ONLY" and currency != "LOYALTY_POINTS":
             raise PermissionDeniedError("العملات المشفرة معطلة حالياً")
 
-        amount_decimal = Decimal(str(amount))
-
         async with self.db.begin_nested():
```

(نقل سطر `amount_decimal` لأعلى بدل تكراره — لا تغيير في قيمته أو استخدامه لاحقًا.)

### 9.2 `hold_funds` (حول السطر 159)

```diff
@@ async def hold_funds(
         amount_decimal = Decimal(str(amount))
+        if amount_decimal <= 0:
+            raise ValidationError("المبلغ يجب أن يكون أكبر من صفر")
 
         if idempotency_key:
             existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
```

### 9.3 `release_held_funds` (حول السطر 222)

```diff
@@ async def release_held_funds(
         amount_decimal = Decimal(str(amount))
+        if amount_decimal <= 0:
+            raise ValidationError("المبلغ يجب أن يكون أكبر من صفر")
 
         if idempotency_key:
             existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
```

### 9.4 `settle_held_funds` (حول السطر 287)

```diff
@@ async def settle_held_funds(
         if not idempotency_key:
             raise ValidationError("Idempotency key is required")
 
+        amount_decimal = Decimal(str(amount))
+        if amount_decimal <= 0:
+            raise ValidationError("المبلغ يجب أن يكون أكبر من صفر")
+
         existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
         if existing_tx:
@@
         if receiver.tenant_id != self.tenant_id:
             raise PermissionDeniedError("المستلم لا يخص هذا المستأجر")
 
-        amount_decimal = Decimal(str(amount))
-
         async with self.db.begin_nested():
```

### 9.5 `eppne-backend/app/domains/insurance/router.py:225`

```diff
-    approved_amount: Optional[Decimal] = Query(None, description="المبلغ المعتمد (إن كانت الموافقة)"),
+    approved_amount: Optional[Decimal] = Query(None, gt=0, description="المبلغ المعتمد (إن كانت الموافقة)"),
```

### 9.6 ملاحظات على الـdiff

- `ValidationError` مستورد أصلًا في `finance/service.py` (مستخدم في `transfer` و`release_held_funds`) — لا import جديد.
- رسالة الخطأ بالعربية كباقي رسائل الملف.
- الحارس **قبل** فحص idempotency في كل الدوال: طلب بمبلغ غير صالح يُرفض حتى لو تطابق مفتاحه مع معاملة موجودة (لا يمكن أصلًا أن توجد معاملة بمبلغ <= 0 بسبب CHECK في DB).
- `service.py:524` (`approved_amount or claimed`) **لا يُلمس** — مع `gt=0` في الراوتر، القيمة 0 لا تصل للخدمة عبر HTTP. (مستدعٍ داخلي يمرر 0 مباشرة سيظل يسقط إلى `claimed` — مُسجَّل كبند backlog §11.)
- **حد معروف:** `gt=0` في الراوتر لا يغطي استدعاءات الخدمة المباشرة؛ مبلغ سالب من مستدعٍ داخلي يُوقَف بالحارس المركزي (§9.1).
- عدد الأسطر المتوقع: `finance/service.py` ≈ +12/−4، `insurance/router.py` 1/1.

## 10. خطة إثبات "قبل الإصلاح" الملموسة (بانتظار الموافقة النهائية)

**الأداة:** سكربت واحد مؤقت في scratchpad (ليس في `tests/`)، يعيد استخدام `_seed` / `_cleanup` / `_state` من `tests/test_insurance_review_claim_status_guard.py` (نفس نمط جلسة الدفع المزدوج: tenant throwaway `REGTEST_NEGAMT_*`، مراجِع برصيد 500 MR_USDT، مُطالِب برصيد 0، بوليصة بسقف 1000، مطالبات `SUBMITTED` بمبلغ 20).

**الحالات (كلها على الكود الحالي غير المُصلَح):**

| # | الإجراء | المتوقع قبل الإصلاح |
|---|---|---|
| B1 | `review_claim(approve=True, approved_amount=-50)` على مطالبة 1 | استثناء `IntegrityError` (غالبًا `check_wallet_balances_non_negative` لأن رصيد المُطالِب 0 → −50 عند UPDATE)؛ الأرصدة 500/0 بلا تغيير؛ الحالة `SUBMITTED`؛ 0 صفوف `claim_payout_*`؛ 0 فواتير |
| B2 | نفس B1 لكن المُطالِب يُعطى رصيد 100 أولًا (ليمر wallet CHECK) | يصل التنفيذ إلى INSERT `transactions` → `check_transaction_amount_positive`؛ لا تغيير — **هذا يثبت أن `transactions` CHECK وحده يكفي حتى لو كان للضحية رصيد** |
| B3 | HTTP: `PUT /insurance/claims/{id}/review?approve=true&approved_amount=-50` عبر `httpx.AsyncClient(ASGITransport(app))` مع override لـ`get_current_active_user` | **500** (لا handler لـ`IntegrityError`) |
| B4 | `FinanceService.transfer(amount=-10)` مباشرة | `IntegrityError`؛ الأرصدة بلا تغيير |
| B5 | `hold_funds(amount=-10)` | `IntegrityError` (`check_wallet_held_balances_non_negative`)؛ بلا تغيير |
| B6 | `release_held_funds(amount=-10)` | `IntegrityError` (`transactions` CHECK)؛ بلا تغيير |
| B7 | `settle_held_funds(amount=-10)` | `IntegrityError`؛ بلا تغيير |
| B8 | `review_claim(approve=True, approved_amount=Decimal("0"))` على مطالبة 2 | **يدفع 20 كاملة** (اكتشاف `or`)؛ الحالة `PAID`، `approved_amount=20` |

- كل حالة في جلسة DB مستقلة. تُسجَّل: نوع الاستثناء + اسم القيد + لقطة `_state` قبل/بعد → ملف أدلة `...-evidence-before.txt` في `.claude/reports/` (نفس نمط الجلسة السابقة).
- **ملاحظة صريحة:** إن ثبت B1–B7 كما هو متوقع، فالإثبات هو إثبات "**لا نقل أموال + 500**"، وليس إثبات سرقة — لأن السرقة ممنوعة على مستوى DB. لن أُسقط أو أعطّل أي قيد DB لمحاكاة السرقة.

**التنظيف (يُعرض عليك قبل التشغيل، كما طلبت):** `_cleanup` الموجود: حذف صفوف `transactions` حيث `sender_id`/`receiver_id` ضمن مستخدمي الاختبار ← حذف كل الصفوف بـ`tenant_id` الخاص بالـtenant المؤقت (جولات لحل ترتيب FK) ← حذف صف `academy_tenants`. يُستدعى في `finally`. سأعرض الأوامر الفعلية + عدد الصفوف المتأثرة قبل التنفيذ.

**بعد الإصلاح:** نفس الحالات — المتوقع: B1/B2/B4–B7 → `ValidationError` قبل أي SQL؛ B3 → **422**؛ B8 عبر HTTP → 422 (عبر الخدمة مباشرة: يبقى 20 — حد معروف §9.6)؛ + حالة إيجابية A1: `approved_amount=50` → `PAID`، مراجِع 450، مُطالِب 50، صف transaction واحد. ثم ملف pytest دائم `tests/test_finance_non_positive_amount_guard.py` وregression (insurance status guard، FINBIND، transport، tenders).

## 11. بنود backlog جديدة (توثيق فقط — لا تنفيذ)

1. `backlog-social-physical-gift-product-price-no-positive-constraint` — `social/schemas.py:169`.
2. `backlog-projects-contribution-amount-no-positive-constraint` — `projects/schemas.py:69`.
3. `backlog-transport-booking-seats-count-no-min` — `transport/schemas.py:131` (`ge=1`).
4. `backlog-merchant-set-prices-no-nonnegative-constraint` — commerce `price_mrusdt`/`wholesale_price_mrusdt`، tourism_sports `base_price_mrusdt`/`base_ticket_price_mrusdt`، transport `base_fare_mrusdt`/`delivery_fee_mrusdt`، social خطط المجموعات، saas `price_monthly`، employment `base_salary`.
5. `backlog-digital-twin-negative-duration-free-interaction` — `digital_twin/schemas.py:49`.
6. `backlog-no-global-integrityerror-handler` — `app/main.py` (500 عام لأي انتهاك قيد).
7. `backlog-review-claim-zero-amount-falls-back-to-claimed` — `insurance/service.py:524` (`or` بدل `is not None`) — مغلق عبر HTTP بـ`gt=0`، مفتوح للمستدعين الداخليين.

## 12. الحالة الحالية

- لا كود مُعدَّل. لا staging. لا commit. `PROGRESS_LOG.md` لم يُلمس.
- **بانتظار الموافقة النهائية من المستخدم على §10** قبل تشغيل أي شيء.


---
---

# القسم الإضافي — 2026-09-23 (الجولة الثالثة): توضيح قيد DB + الجداول الكاملة + الـdiff الحرفي + خطة B1–B8

**القواعد لهذه الجولة:** لم يُشغَّل أي شيء (لا سكربت، لا اختبار، لا استعلام DB جديد). قراءة ملفات فقط (migrations + `database.py` + 3 مواقع استدعاء أُعيد فحصها). لا تعديل كود.

**تصحيح رقمي مهم:** قلتُ سابقًا "~45 موقع استدعاء". العدد الدقيق من الـgrep هو **40 موقع استدعاء فعلي** + 6 أسطر تعليقات فقط (`# WARNING: هذا الـcommit() بيغطي ... finance.transfer()` في `digital_twin/repository.py:59`، `employment/repository.py:424`، `insurance/repository.py:99`، `invoicing/repository.py:23`، `invoicing/repository.py:54`، `projects/repository.py:107`) — ليست استدعاءات.

**تصحيح تصنيفي:** إعادة الفحص في هذه الجولة غيّرت تصنيف موقعين من B إلى A (الصفوف 25 و38 في §ب)، وحددت موقع المزاد (#32) كـ"A مشروط". الإصلاح المركزي يغطيها كلها، لذا النطاق لا يتغير؛ أُضيفت كبنود backlog (§ب.3).

---

## أ. توضيح سؤال قيد قاعدة البيانات

### أ.a — هل يوجد اليوم CHECK على `transactions.amount > 0`؟

**نعم.** في المخطط الحالي غير المعدَّل.

**1) من قاعدة البيانات الحية** (استعلام `pg_constraint` نُفِّذ في الجولة الأولى على الحاوية `eppne_db`، قاعدة `eppne_v2`، مستخدم `eppne` — مخرجات حرفية):
```
wallets|check_wallet_balances_non_negative|CHECK (((((balances ->> 'MR_POUND'::text))::numeric >= (0)::numeric) AND (((balances ->> 'MR_USDT'::text))::numeric >= (0)::numeric) AND (((balances ->> 'MR7'::text))::numeric >= (0)::numeric) AND (((balances ->> 'NBT'::text))::numeric >= (0)::numeric) AND (((balances ->> 'MRX'::text))::numeric >= (0)::numeric)))
transactions|check_transaction_amount_positive|CHECK ((amount > (0)::numeric))
invoices|check_amount_non_negative|CHECK ((amount >= (0)::numeric))
wallets|check_wallet_held_balances_non_negative|CHECK (((((held_balances ->> 'MR_POUND'::text))::numeric >= (0)::numeric) AND (((held_balances ->> 'MR_USDT'::text))::numeric >= (0)::numeric) AND (((held_balances ->> 'MR7'::text))::numeric >= (0)::numeric) AND (((held_balances ->> 'NBT'::text))::numeric >= (0)::numeric) AND (((held_balances ->> 'MRX'::text))::numeric >= (0)::numeric)))
```

**2) الـmigration الذي أنشأه** — `eppne-backend/migrations/versions/71820e4fe1f3_initial_migration_all_34_sectors_final.py:2034` (داخل `create_table('transactions', ...)`):
```python
    sa.CheckConstraint('amount > 0', name='check_transaction_amount_positive'),
```
والقيود الأخرى:
- `check_wallet_balances_non_negative` — نفس الملف، سطر 461.
- `check_wallet_held_balances_non_negative` — `migrations/versions/042_add_held_balances_to_wallets.py:28-34`.
- `check_amount_non_negative` (invoices) — `migrations/versions/016_create_invoices_table.py:40`.

**3) الموديل** — `eppne-backend/app/domains/finance/models.py:64`:
```python
        CheckConstraint("amount > 0", name="check_transaction_amount_positive"),
```

### أ.b — هل تفشل محاولة التحويل بمبلغ سالب اليوم على مستوى DB بغض النظر عن أي إصلاح في التطبيق؟

**نعم (استنتاجًا من الكود والقيود — لم يُثبت حيًّا بعد؛ B1–B7 مصممة لإثباته).**

كل الدوال الأربع تُنشئ صف `Transaction` بـ`amount=float(amount_decimal)` — القيمة نفسها السالبة، بلا `abs()` ولا عكس للاتجاه:
- `transfer` — `service.py:119-131` (`tx_type="TRANSFER"`)
- `hold_funds` — `service.py:185-195` (`tx_type="HOLD"`)
- `release_held_funds` — `service.py:245-255` (`tx_type="RELEASE"`)
- `settle_held_funds` — `service.py:331-343` (`tx_type="SETTLEMENT"`)

أي مبلغ `<= 0` → الـINSERT ينتهك `check_transaction_amount_positive` → `sqlalchemy.exc.IntegrityError`. **ولا يوجد أي مسار في الكود يغيّر الأرصدة دون إدراج صف `Transaction`:** الكاتب الآخر الوحيد للأرصدة، `identity/repository.py:286 update_balances`، لا يستدعيه أحد (تحقق عبر grep).

### أ.c — إعادة سير سيناريو الهجوم مع وجود القيد

**الترتيب داخل `transfer` (`service.py:92-131`) — تعديل المحافظ يحدث قبل الـINSERT المحظور، وداخل نفس الـSAVEPOINT:**

```
async with self.db.begin_nested():                       # SAVEPOINT
    SELECT ... FOR UPDATE  (محفظتا الطرفين، بترتيب id)
    فحص is_frozen
    فحص الرصيد: sender_current < amount_decimal         # مع amount سالب → False دائمًا → يمر
    sender_balances[cur]   = sender_current - amount     # يزيد
    receiver_balances[cur] = receiver_current + amount   # ينقص
    (1) UPDATE wallets SET balances=... WHERE id=sender     ← wallet_repo.update_balances → execute + flush
    (2) UPDATE wallets SET balances=... WHERE id=receiver   ← نفس الشيء
    (3) INSERT INTO transactions (amount = سالب)            ← tx_repo.create → add + flush
```

- `update_balances` (`finance/repository.py:51-60`) يستخدم `db.execute(update(Wallet)...)` — عبارة SQL تُرسل فورًا لـPostgres داخل الـSAVEPOINT، ثم `flush()`. **لا `commit()`.**
- `tx_repo.create` (`finance/repository.py:90-94`) — `add` + `flush` + `refresh`. **لا `commit()`.**

**أين يفشل بالضبط؟ حالتان:**
1. **رصيد المستلم أقل من |المبلغ|** (مثلًا المُطالِب رصيده 0 والمبلغ −50): الـUPDATE رقم (2) يجعل رصيده −50 → ينتهك `check_wallet_balances_non_negative` فورًا (Postgres يفحص CHECK عند كل عبارة، والقيد غير DEFERRABLE) → `IntegrityError` عند الخطوة (2). الـUPDATE رقم (1) كان قد نُفِّذ داخل نفس الـSAVEPOINT.
2. **رصيد المستلم يكفي** (أو العملة `LOYALTY_POINTS` غير المشمولة بقيد المحفظة): (1) و(2) ينجحان داخل الـSAVEPOINT، ثم (3) ينتهك `check_transaction_amount_positive` → `IntegrityError`.

**هل يعود كل شيء بشكل نظيف بصافي تغيير صفر؟ نعم — على ثلاث طبقات:**
1. `async with self.db.begin_nested()` في `transfer`: عند خروج استثناء من الكتلة، SQLAlchemy يُصدر `ROLLBACK TO SAVEPOINT` → Postgres يلغي الـUPDATE(s) المنفَّذة داخلها. الأقفال (`FOR UPDATE`) تبقى حتى نهاية المعاملة الخارجية.
2. في `review_claim` (`insurance/service.py:514-540`): الاستدعاء داخل `begin_nested()` خارجي آخر → الاستثناء يمر خلاله → `ROLLBACK TO SAVEPOINT` ثانٍ؛ `update_claim(status=PAID)` لم يُنفَّذ أصلًا (يأتي بعد `transfer`). الـ`commit()` في السطر 541 **لا يُوصَل إليه**. إنشاء الفاتورة (543-553) **لا يُوصَل إليه**.
3. `get_db` (`app/core/database.py:45-51`): `async with AsyncSessionLocal() as session: try: yield session finally: await session.close()` — لا commit عند الاستثناء؛ `close()` يلغي المعاملة الخارجية المفتوحة.

**النتيجة المتوقعة:** صافي تغيير صفر في `wallets`، `transactions`، `insurance_claims`، `invoices`. العميل يتلقى **HTTP 500** (لا يوجد `exception_handler` لـ`IntegrityError` في `app/main.py` — الموجود فقط: `SovereignError` سطر 110، `IdempotencyError` سطر 118، `RateLimitError` سطر 126).

**آثار جانبية غير مالية قبل الفشل (للأمانة):** `_check_saas_limits` واستدعاء وكيل AI (`agent_id=10`، أخطاؤه تُبلَع) يحدثان قبل الـSAVEPOINT — قد يكتبان سجلات AI/audit خاصة بهما. لا علاقة لهما بالأرصدة. سيتم رصد ذلك في B1.

**حالة `hold_funds` بمبلغ سالب:** الترتيب نفسه — `update_wallet_funds` (balances يزيد، held ينقص) ثم INSERT. `held_balances` يصبح سالبًا → `check_wallet_held_balances_non_negative` يفشل عند الـUPDATE (لو المحجوز الحالي أقل من |المبلغ|)، وإلا يفشل الـINSERT. نفس الـrollback.

**حالة `release_held_funds` / `settle_held_funds` بمبلغ سالب:** held يزيد (من 0 إلى +|المبلغ|) والرصيد المتاح/رصيد المستلم ينقص — قيود المحفظة قد تمر كلها إذا كانت الأرصدة كافية → **الحاجز الوحيد عندها هو قيد `transactions`** (انظر B6، B7).

### أ.d — الخلاصة الصريحة

**الثغرة كما عُلِّمت في الأصل ("مُصدِر تأمين خبيث يسرق أموال المُطالِبين بمبلغ سالب") ليست حقيقية اليوم.** التعليم الأصلي في جلسة `review_claim` (§6، §11 من تقريرها) **بُني على قراءة ناقصة**: قرأ منطق `FinanceService.transfer` في Python وحده (وهو فعلًا بلا فحص حد أدنى)، لكنه **لم يفحص** `__table_args__` في `finance/models.py` ولا الـmigrations ولا القيود الحية، ففاته `check_transaction_amount_positive` وقيود المحفظة. هذا خطئي في تلك الجلسة.

**ما يبقى حقيقيًا (أقل خطورة):**
1. طبقة التطبيق بلا أي حارس `amount > 0` في الدوال الأربع — الحماية معلّقة بالكامل على قيد DB واحد (أي migration مستقبلي يُسقطه أو يُضعفه يفتح السرقة فورًا).
2. أي مبلغ `<= 0` يصل للدوال → **500 غير مُعالَج** بدل 4xx نظيف.
3. `approved_amount=0` → يُدفع كامل المبلغ المطالب به (منطق `or`) — ممكن عبر HTTP اليوم.

**التصنيف الجديد:** hardening + تصحيح كود الخطأ، خطورة منخفضة–متوسطة. **ليس** سرقة أموال قابلة للاستغلال. هذا استنتاج من القراءة؛ B1–B7 ستؤكده أو تنفيه حيًّا.

---

## ب. كل مواقع الاستدعاء الـ40 (الـgrep الكامل مع التصنيف)

**أمر الـgrep:** `grep -rn "\.transfer(\|\.hold_funds(\|\.release_held_funds(\|\.settle_held_funds(" app --include=*.py | grep -v "def "` (من `eppne-backend/`).

**المفتاح:**
- **A** = المبلغ يتحكم فيه المستخدم الذي يستدعي الـendpoint (مباشرة أو كعامل ضرب)، بلا قيد موجب في الأعلى ولا حارس `> 0`.
- **B** = سعر/قيمة مخزَّنة يضعها مستخدم آخر (تاجر/منشئ/صاحب عمل/مسؤول) عبر schema بلا `gt`/`ge`، ولا حارس `> 0` قبل الاستدعاء. (B-مشتق = مبلغ مخزَّن نتج عن تدفق A/B سابق.)
- **S** = آمن: قيد `gt=0` في الأعلى، أو حارس `if x > 0`، أو ثابت/محسوب خادميًا من مصدر مقيَّد. (S* = آمن على الأرجح مع تحفظ مذكور.)

**النتيجة اليوم لكل A/B مع مبلغ `<= 0`: 500 + rollback (قيد DB)، وليس نقل أموال.**

### ب.1 `transfer` — 31 موقعًا

| # | الموقع | الدالة المستدعية | مصدر المبلغ | التصنيف | السبب |
|---|---|---|---|---|---|
| 1 | `app/domains/academy/service.py:365` | `enroll_in_course` | `course.price_mrusdt` (مخزَّن، يضعه منشئ الدورة؛ `academy/schemas.py:122` بلا قيد) | S | حارس `payment_method == "WALLET" and amount > 0 and not is_free` قبل الاستدعاء |
| 2 | `app/domains/affiliate/service.py:576` | `withdraw_commissions` | `amount` من الطلب | S | `affiliate/schemas.py:197` `gt=0` + `amount >= min_withdrawal` + `amount <= total_pending` |
| 3 | `app/domains/arbitration_syndicates/service.py:337` | الانضمام لنقابة | `syndicate.annual_fee_mrusdt` (مخزَّن؛ `schemas.py:43` بلا قيد) | S | حارس `if fee > 0` |
| 4 | `app/domains/commerce/service.py:174` | checkout | `Σ unit_price × quantity`؛ `unit_price` = `variant.price_mrusdt` أو `wholesale_price_mrusdt` | **B** | `quantity` مقيَّد (`schemas.py:120 gt=0`) لكن `price_mrusdt` (`schemas.py:44`) و`wholesale_price_mrusdt` (`schemas.py:50`) بلا قيد؛ لا حارس `> 0` |
| 5 | `app/domains/commerce/service.py:527` | `retry_failed_payments` (Celery) | `order.total_amount_mrusdt` | B-مشتق | ناتج #4 |
| 6 | `app/domains/digital_twin/service.py:177` | `interact_with_twin` | `interaction_fee_mrusdt × duration_minutes` | S | حارس `if fee > 0` (انظر backlog: مدة سالبة → تفاعل مجاني، ليس عكس أموال) |
| 7 | `app/domains/finance/router.py:47` | `POST /finance/transfer` | `req.amount` | S | `finance/schemas.py:17` `gt=0` |
| 8 | `app/domains/health/service.py:262` | حجز موعد | `Decimal("10.00")` | S | ثابت |
| 9 | `app/domains/insurance/service.py:226` | الاشتراك في بوليصة | `policy.base_premium_mrusdt` | S | `insurance/schemas.py:20,34` `gt=0` + حارس `if premium > 0` |
| 10 | `app/domains/insurance/service.py:309` | `renew_subscription` | `policy.base_premium_mrusdt` | S | `schemas.py:20,34` `gt=0` (لا حارس في الخدمة؛ بوليصة بقسط 0 مُدرجة مباشرة في DB — كما في seed الاختبارات — تعطي 500 عند التجديد) |
| 11 | `app/domains/insurance/service.py:530` | **`review_claim`** | `approved_amount` (Query) أو `claimed_amount_mrusdt` | **A** | `insurance/router.py:225` بلا قيد؛ الخدمة تفحص الحد الأعلى فقط (524-526) |
| 12 | `app/domains/insurance/service.py:649` | `disburse_monthly_pensions` | `pension.monthly_amount_mrusdt` | S | `schemas.py:127,134` `gt=0` |
| 13 | `app/domains/invitations/service.py:643` | `create_campaign` | `budget_mrusdt` | S | `schemas.py:180,199` `ge=0` + حارس `if budget > 0` |
| 14 | `app/domains/invoicing/service.py:189` | `update_invoice_status` → PAID | `invoice.amount` | S* | `invoicing/schemas.py:12` `gt=0` للإنشاء عبر API؛ لكن المستدعون الداخليون لـ`create_invoice` يتجاوزون الـschema، وقيد DB هو `>= 0` → فاتورة بمبلغ 0 ممكنة → دفعها = 500 |
| 15 | `app/domains/iot/service.py:219` | تسييل أرصدة الكربون | `Σ carbon_credits_generated × 50` | S* | "تُحسب تلقائيًا" خادميًا (`iot/schemas.py:69`)؛ لم أتتبع مصدر القراءات حتى النهاية |
| 16 | `app/domains/projects/service.py:185` | المساهمة في مشروع (MONETARY) | `data.amount_mrusdt` | **A** | `projects/schemas.py:69` بلا قيد؛ لا حارس `> 0`؛ الاستثناء يُعاد رفعه (`raise`) بعد حذف مفتاح redis |
| 17 | `app/domains/realestate/service.py:311` | شراء حصة من وحدة | `sale_price_mrusdt × percentage / 100` | S* | `ownership_percentage` `gt=0, le=100` (`realestate/schemas.py:81`)؛ `sale_price_mrusdt` المخزَّن لم يُفحص قيده في هذه الجلسة |
| 18 | `app/domains/saas/service.py:292` | `process_auto_renewals` (Celery) | `plan.price_monthly` | B (مسؤول) | `saas/schemas.py:39` بلا قيد — لكن الخطط يضعها مسؤول المنصة |
| 19 | `app/domains/saas/service.py:703` | `pay_invoice` | `invoice.amount` | S* | مثل #14 |
| 20 | `app/domains/service_marketplace/service.py:191` | شراء خدمة | `base_price + Σ addons` | S | حارس `if total_price > 0` |
| 21 | `app/domains/service_marketplace/service.py:362` | `renew_subscription` | `base_price` حسب الخطة | S | حارس `if base_price > 0` |
| 22 | `app/domains/service_marketplace/service.py:399` | `purchase_addon` | `addon.price_mrusdt` | S | حارس `if addon_price > 0` |
| 23 | `app/domains/social/service.py:523` | `send_digital_gift` | `gift_value` | S | حارس `if gift_value > 0` |
| 24 | `app/domains/social/service.py:590` | `request_physical_gift` | `product_price` من الطلب | **A** | `social/schemas.py:169` بلا قيد؛ لا حارس |
| 25 | `app/domains/social/service.py:679` | الاشتراك في مجموعة | `price_yearly` أو `price_monthly × duration_months` | **A** (مُصحَّح من B) | `duration_months` من الطلب (`social/router.py:389`، `schemas.py:196` بلا قيد) → قيمة سالبة أو 0 → سعر سالب/صفر؛ والأسعار نفسها (`schemas.py:184-185`) بلا قيد (B) |
| 26 | `app/domains/sovereign_entities/service.py:411` | إيداع في خزينة | `amount` من الطلب | S | `schemas.py:167` `gt=0` |
| 27 | `app/domains/sovereign_entities/service.py:483` | تحويل من الخزينة | `amount` من الطلب | S | `schemas.py:174` `gt=0` |
| 28 | `app/domains/tourism_sports/service.py:184` | التسجيل في برنامج | `program.base_price_mrusdt` | **B** | `tourism_sports/schemas.py:44` بلا قيد؛ لا حارس |
| 29 | `app/domains/tourism_sports/service.py:342` | شراء تذكرة | `base_ticket_price × multiplier (+50 لـVIP transport)` | **B** | `schemas.py:97` بلا قيد؛ المضاعف ثابت خادميًا |
| 30 | `app/tasks/billing.py:351` | اشتراك التوأم الرقمي (Celery) | `twin.subscription_monthly_mrusdt` | S | حارس `if monthly_fee > 0` |
| 31 | `app/tasks/employment.py:313` | صرف الرواتب (Celery) | `payroll.net_salary` | B | مشتق من `base_salary` (`employment/schemas.py:70` بلا قيد)؛ يضعه صاحب العمل (المُرسِل هو صاحب العمل نفسه) |

### ب.2 `hold_funds` / `release_held_funds` / `settle_held_funds` — 9 مواقع

| # | الموقع | الدالة | مصدر المبلغ | التصنيف | السبب |
|---|---|---|---|---|---|
| 32 | `app/domains/tenders_auctions/service.py:415` | `hold_funds` — مزايدة حية | `bid_amount` من الطلب | **A (مشروط)** | الحد الأدنى `min_required = current_highest + auction.min_increment_mrusdt` (`service.py:390`)؛ `start_price` مقيَّد `gt=0` لكن `min_increment_mrusdt` (`schemas.py:75`) بلا قيد → منشئ المزاد يضع زيادة سالبة كبيرة → المزايِد يمرر مبلغًا سالبًا |
| 33 | `app/domains/tenders_auctions/service.py:482` | `release_held_funds` — المزايدات الخاسرة | مبلغ المزايدة المخزَّن | S | نفس المبلغ الذي نجح حجزه سابقًا (مر عبر قيد DB) |
| 34 | `app/domains/tenders_auctions/service.py:493` | `settle_held_funds` — الفائز | مبلغ المزايدة المخزَّن | S | نفسه |
| 35 | `app/domains/transport/service.py:388` | `settle_held_funds` — إكمال الرحلة | `booking.fare_paid_mrusdt` | B-مشتق | ناتج #36 |
| 36 | `app/domains/transport/service.py:478` | `hold_funds` — حجز رحلة | `trip.base_fare_mrusdt × seats_count` | **A** | `seats_count` من الطلب (`transport/schemas.py:131` بلا قيد)؛ و`base_fare_mrusdt` (`schemas.py:101`) بلا قيد (B) |
| 37 | `app/domains/transport/service.py:571` | `release_held_funds` — إلغاء حجز | `booking.fare_paid_mrusdt` | B-مشتق | ناتج #36 |
| 38 | `app/domains/transport/service.py:814` | `hold_funds` — دفع رسوم توصيل | `task.delivery_fee_mrusdt` | **A** (مُصحَّح من B) | المُرسِل نفسه يضع الرسوم عند الإنشاء (`DeliveryTaskCreate.delivery_fee_mrusdt`، `schemas.py:157` بلا قيد → `service.py:701`)، ثم هو نفسه الدافع (`task.sender_id != payer_id` → رفض) |
| 39 | `app/domains/transport/service.py:609` | `release_held_funds` — إلغاء توصيل | `task.delivery_fee_mrusdt` | B-مشتق | ناتج #38 |
| 40 | `app/domains/transport/service.py:757` | `settle_held_funds` — إكمال توصيل | `task.delivery_fee_mrusdt` | B-مشتق | ناتج #38 |

### ب.3 الملخص

- **A (7):** #11 review_claim، #16 projects، #24 social gift، #25 social group sub، #32 tenders bid (مشروط)، #36 transport booking، #38 transport delivery payment.
- **B / B-مشتق (10):** #4، #5، #18، #28، #29، #31، #35، #37، #39، #40 (+ السعر المخزَّن كعامل ثانٍ في #25، #36).
- **S / S* (23):** الباقي.
- **القرار (متوافق مع قرار المستخدم §8):** الإصلاح المركزي في الدوال الأربع يغطي كل الـ40 موقعًا دفعة واحدة، فلا حاجة للمس أي موقع. قيود الـschema لكل صفوف A/B → backlog فقط.
- **بنود backlog إضافية من هذه الجولة** (تُضاف لقائمة §11):
  8. `backlog-social-group-subscription-duration-months-no-min` — `social/schemas.py:196`.
  9. `backlog-transport-delivery-fee-no-nonnegative-constraint` — `transport/schemas.py:157` (يضعه الدافع نفسه).
  10. `backlog-tenders-min-increment-no-nonnegative-constraint` — `tenders_auctions/schemas.py:75`.

---

## ج. الـdiff الكامل — الكود الحرفي قبل/بعد (لم يُطبَّق)

الملف: `eppne-backend/app/domains/finance/service.py`. `ValidationError` مستورد أصلًا ومستخدم في نفس الملف (`transfer` و`release_held_funds` و`settle_held_funds`) — **لا import جديد.**

### ج.1 `transfer` (الأسطر 58-92 حاليًا)

**قبل:**
```python
    async def transfer(
        self,
        sender_id: int,
        receiver_email: str,
        currency: str,
        amount: Decimal,
        idempotency_key: str,
        notes: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ):
        if not idempotency_key:
            raise ValidationError("Idempotency key is required")

        existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
        if existing_tx:
            logger.warning(f"Duplicate transfer request detected: {idempotency_key}")
            return existing_tx

        user_repo = UserRepository(self.db)
        receiver = await user_repo.get_by_email(receiver_email, self.tenant_id)
        if not receiver:
            raise NotFoundError("المستلم غير موجود")

        if receiver.tenant_id != self.tenant_id:
            raise PermissionDeniedError("المستلم لا يخص هذا المستأجر")

        state = await self.state_repo.get_state()
        crypto_mode = str(getattr(state, "crypto_mode", "FULL_CRYPTO"))
        if crypto_mode == "POINTS_ONLY" and currency != "LOYALTY_POINTS":
            raise PermissionDeniedError("العملات المشفرة معطلة حالياً")

        amount_decimal = Decimal(str(amount))

        async with self.db.begin_nested():
```

**بعد:**
```python
    async def transfer(
        self,
        sender_id: int,
        receiver_email: str,
        currency: str,
        amount: Decimal,
        idempotency_key: str,
        notes: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ):
        if not idempotency_key:
            raise ValidationError("Idempotency key is required")

        # مبلغ <= 0 يعكس اتجاه التحويل منطقيًا (فحص الرصيد يمر دائمًا)؛
        # بدون هذا الحارس الحاجز الوحيد هو CHECK في DB (IntegrityError → 500)
        amount_decimal = Decimal(str(amount))
        if amount_decimal <= 0:
            raise ValidationError("المبلغ يجب أن يكون أكبر من صفر")

        existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
        if existing_tx:
            logger.warning(f"Duplicate transfer request detected: {idempotency_key}")
            return existing_tx

        user_repo = UserRepository(self.db)
        receiver = await user_repo.get_by_email(receiver_email, self.tenant_id)
        if not receiver:
            raise NotFoundError("المستلم غير موجود")

        if receiver.tenant_id != self.tenant_id:
            raise PermissionDeniedError("المستلم لا يخص هذا المستأجر")

        state = await self.state_repo.get_state()
        crypto_mode = str(getattr(state, "crypto_mode", "FULL_CRYPTO"))
        if crypto_mode == "POINTS_ONLY" and currency != "LOYALTY_POINTS":
            raise PermissionDeniedError("العملات المشفرة معطلة حالياً")

        async with self.db.begin_nested():
```
(سطر `amount_decimal = Decimal(str(amount))` **نُقل** لأعلى ولم يُكرَّر؛ باقي الدالة لا يتغير.)

### ج.2 `hold_funds` (الأسطر 149-165 حاليًا)

**قبل:**
```python
    async def hold_funds(
        self,
        user_id: int,
        amount: Decimal,
        currency: str,
        description: str,
        idempotency_key: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ):
        amount_decimal = Decimal(str(amount))

        if idempotency_key:
            existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
            if existing_tx:
                logger.warning(f"Duplicate hold request detected: {idempotency_key}")
                return existing_tx
```

**بعد:**
```python
    async def hold_funds(
        self,
        user_id: int,
        amount: Decimal,
        currency: str,
        description: str,
        idempotency_key: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ):
        amount_decimal = Decimal(str(amount))
        if amount_decimal <= 0:
            raise ValidationError("المبلغ يجب أن يكون أكبر من صفر")

        if idempotency_key:
            existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
            if existing_tx:
                logger.warning(f"Duplicate hold request detected: {idempotency_key}")
                return existing_tx
```

### ج.3 `release_held_funds` (الأسطر 212-228 حاليًا)

**قبل:**
```python
    async def release_held_funds(
        self,
        user_id: int,
        amount: Decimal,
        currency: str,
        description: str,
        idempotency_key: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ):
        amount_decimal = Decimal(str(amount))

        if idempotency_key:
            existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
            if existing_tx:
                logger.warning(f"Duplicate release request detected: {idempotency_key}")
                return existing_tx
```

**بعد:**
```python
    async def release_held_funds(
        self,
        user_id: int,
        amount: Decimal,
        currency: str,
        description: str,
        idempotency_key: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ):
        amount_decimal = Decimal(str(amount))
        if amount_decimal <= 0:
            raise ValidationError("المبلغ يجب أن يكون أكبر من صفر")

        if idempotency_key:
            existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
            if existing_tx:
                logger.warning(f"Duplicate release request detected: {idempotency_key}")
                return existing_tx
```

### ج.4 `settle_held_funds` (الأسطر 272-302 حاليًا)

**قبل:**
```python
    async def settle_held_funds(
        self,
        sender_id: int,
        receiver_email: str,
        currency: str,
        amount: Decimal,
        idempotency_key: str,
        notes: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ):
        """تسوية ذرّية لحجز قائم: تنقل المبلغ من held_balances الخاص بالمرسل
        مباشرة إلى balances الخاص بالمستلم، بدون المرور بـbalances المتاح
        للمرسل — تقفل نافذة الخطر بين release_held_funds و transfer المنفصلين."""
        if not idempotency_key:
            raise ValidationError("Idempotency key is required")

        existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
        if existing_tx:
            logger.warning(f"Duplicate settlement request detected: {idempotency_key}")
            return existing_tx

        user_repo = UserRepository(self.db)
        receiver = await user_repo.get_by_email(receiver_email, self.tenant_id)
        if not receiver:
            raise NotFoundError("المستلم غير موجود")

        if receiver.tenant_id != self.tenant_id:
            raise PermissionDeniedError("المستلم لا يخص هذا المستأجر")

        amount_decimal = Decimal(str(amount))

        async with self.db.begin_nested():
```

**بعد:**
```python
    async def settle_held_funds(
        self,
        sender_id: int,
        receiver_email: str,
        currency: str,
        amount: Decimal,
        idempotency_key: str,
        notes: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ):
        """تسوية ذرّية لحجز قائم: تنقل المبلغ من held_balances الخاص بالمرسل
        مباشرة إلى balances الخاص بالمستلم، بدون المرور بـbalances المتاح
        للمرسل — تقفل نافذة الخطر بين release_held_funds و transfer المنفصلين."""
        if not idempotency_key:
            raise ValidationError("Idempotency key is required")

        amount_decimal = Decimal(str(amount))
        if amount_decimal <= 0:
            raise ValidationError("المبلغ يجب أن يكون أكبر من صفر")

        existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
        if existing_tx:
            logger.warning(f"Duplicate settlement request detected: {idempotency_key}")
            return existing_tx

        user_repo = UserRepository(self.db)
        receiver = await user_repo.get_by_email(receiver_email, self.tenant_id)
        if not receiver:
            raise NotFoundError("المستلم غير موجود")

        if receiver.tenant_id != self.tenant_id:
            raise PermissionDeniedError("المستلم لا يخص هذا المستأجر")

        async with self.db.begin_nested():
```
(سطر `amount_decimal` **نُقل** لأعلى ولم يُكرَّر.)

### ج.5 `eppne-backend/app/domains/insurance/router.py:225`

**قبل:**
```python
    approved_amount: Optional[Decimal] = Query(None, description="المبلغ المعتمد (إن كانت الموافقة)"),
```

**بعد:**
```python
    approved_amount: Optional[Decimal] = Query(None, gt=0, description="المبلغ المعتمد (إن كانت الموافقة)"),
```

### ج.6 ملاحظات

- **المجموع المتوقع:** `finance/service.py` ≈ +12 / −2 (سطران منقولان + تعليق من سطرين + 4×2 أسطر حارس + أسطر فارغة)؛ `insurance/router.py` 1/1. سيُتحقق بـ`git diff --stat` بعد التطبيق.
- **لماذا الحارس قبل البحث عن idempotency:** لا يمكن أن توجد معاملة محفوظة بمبلغ `<= 0` (قيد DB)، فرفض الطلب مبكرًا لا يكسر أي إعادة محاولة شرعية.
- **لا تراجع للتدفقات الشرعية:** كل مبلغ `<= 0` يفشل اليوم أصلًا في DB؛ الحارس يغيّر فقط **نوع** الفشل (`IntegrityError`/500 ← `ValidationError`/4xx) و**توقيته** (قبل أي SQL بدل بعد أقفال `FOR UPDATE` وUPDATE-ات).
- **`insurance/service.py:524` (`approved_amount or claimed`) لا يُلمس** (backlog #7): `gt=0` يمنع 0 عبر HTTP؛ مستدعٍ داخلي يمرر 0 مباشرة للخدمة سيبقى يسقط إلى المبلغ المطالب به.
- **كود الحالة لـ`ValidationError`:** سأتحقق أثناء التحقق بعد الإصلاح من كود HTTP الفعلي الذي يُرجعه handler الـ`SovereignError` (المتوقع 400 أو 422) وأسجله.

---

## د. خطة إثبات "قبل الإصلاح" B1–B8 — بالتفصيل الكامل

### د.1 الأداة والإعداد

- **سكربت مؤقت واحد** في مجلد scratchpad الخاص بالجلسة (ليس في `eppne-backend/tests/`، لا يُضاف للـgit). يُشغَّل بـ`venv/Scripts/python` من `eppne-backend/`.
- **ينسخ حرفيًا** منطق `_user` / `_seed` / `_cleanup` / `_state` / `_balances` من `tests/test_insurance_review_claim_status_guard.py` مع تغيير البادئة إلى `REGTEST_NEGAMT_*` (لتجنب بادئة `RCGUARD` المضللة في الأدلة). لا تعديل على ملف الاختبار الأصلي.
- **Seed** (tenant واحد مؤقت `REGTEST_NEGAMT_{suffix}`، الـDB الحية `eppne_v2` على المنفذ 5435):
  - مستخدم **مراجِع**: رصيد `MR_USDT = 500`، `system_role=SUPER_ADMIN`، عضوية `OWNER` على كيان سيادي `ENTERPRISE` مُصدِر للبوليصة.
  - مستخدم **مُطالِب**: رصيد `MR_USDT = 0` (يُعدَّل في B2).
  - وصول SaaS: الخدمة/الخطة 101 (نفس جلسة الدفع المزدوج).
  - بوليصة `ACCIDENT` بسقف تغطية 1000، قسط 0 (مُدرجة مباشرة عبر ORM، كما في الاختبار الموجود).
  - اشتراك `ACTIVE` للمُطالِب.
  - **3 مطالبات** `SUBMITTED` بمبلغ 20 لكل منها: C1 (لـB1/B2)، C2 (لـB3)، C3 (لـB8).
- **لقطة الحالة** (`_state`) قبل وبعد كل حالة: رصيد MR_USDT للطرفين، `status` / `approved_amount_mrusdt` / `payout_tx_hash` للمطالبة، عدد صفوف `transactions` بمفتاح `claim_payout_{id}%`، عدد الفواتير في الـtenant. + للحالات B4–B7: `balances` و`held_balances` كاملتين للمحفظتين + عدد صفوف `transactions` للمستخدمَين.
- كل حالة في **جلسة DB مستقلة** (`AsyncSessionLocal()` جديدة)، تمامًا كطلب HTTP منفصل.
- **مخرجات:** ملف أدلة `.claude/reports/insurance-negative-approved-amount-evidence-before.txt` (نفس نمط `...-double-payment-evidence-after.txt`): لكل حالة — المدخلات، نوع الاستثناء، اسم القيد من رسالة Postgres، لقطة قبل/بعد، و`PASS`/`FAIL` مقابل المتوقع.

### د.2 الحالات

| # | الإجراء (على الكود الحالي غير المُصلَح) | المتوقع | ما يثبته |
|---|---|---|---|
| **B1** | `InsuranceService(session).review_claim(claim_id=C1, reviewer_id=R, tenant_id=T, approve=True, approved_amount=Decimal("-50"))` — المُطالِب رصيده 0 | `IntegrityError` باسم `check_wallet_balances_non_negative` (رصيد المُطالِب 0 → −50 عند UPDATE المستلم، قبل الـINSERT). بعده: مراجِع 500، مُطالِب 0، C1 `SUBMITTED`، `approved_amount` NULL، `payout_tx_hash` NULL، 0 صفوف `claim_payout_C1%`، 0 فواتير | عند ضحية بلا رصيد: قيد المحفظة يوقف العملية؛ لا نقل أموال؛ rollback كامل عبر الـSAVEPOINT-ين |
| **B2** | إعطاء المُطالِب رصيد 100 (UPDATE مباشر لمحفظته في الـtenant المؤقت + commit، يُسجَّل في الأدلة)، ثم نفس استدعاء B1 على C1 | UPDATE المحفظتين ينجحان داخل الـSAVEPOINT (مراجِع 550، مُطالِب 50 مؤقتًا)، ثم `IntegrityError` باسم `check_transaction_amount_positive` عند INSERT. بعده: مراجِع 500، مُطالِب **100** (بلا تغيير)، C1 `SUBMITTED`، 0 صفوف دفع، 0 فواتير | **الحالة الأهم:** حتى لو كان للضحية رصيد يكفي "السرقة"، قيد `transactions` وحده يُلغي الـUPDATE-ين المنفَّذين فعلًا. هذا يجيب عمليًا على سؤال أ.c |
| **B3** | HTTP: `PUT /insurance/claims/{C2}/review?approve=true&approved_amount=-50` عبر `httpx.AsyncClient(transport=ASGITransport(app=fastapi_app))` مع `app.dependency_overrides[get_current_active_user]` يعيد المراجِع (يُزال الـoverride في `finally`). المُطالِب رصيده 100 من B2 | **HTTP 500** (لا handler لـ`IntegrityError`). بعده: لا تغيير في الأرصدة، C2 `SUBMITTED`، 0 صفوف دفع | سلوك العميل الفعلي اليوم: خطأ داخلي بدل 4xx. (`@rate_limit` على الـendpoint يستخدم Redis — طلب واحد لا يقترب من حد 10/دقيقة) |
| **B4** | `FinanceService(session, T).transfer(sender_id=R, receiver_email=<بريد المُطالِب>, currency="MR_USDT", amount=Decimal("-10"), idempotency_key="NEGAMT-B4-{suffix}")` مباشرة | `IntegrityError` باسم `check_transaction_amount_positive` (المُطالِب رصيده 100 ≥ 10). لا تغيير في `balances` لأي طرف؛ 0 صفوف بمفتاح `NEGAMT-B4-*` | الدالة الأساسية بلا حارس؛ DB هو الحاجز الوحيد |
| **B5** | `hold_funds(user_id=R, amount=Decimal("-10"), currency="MR_USDT", description="NEGAMT B5", idempotency_key="NEGAMT-B5-{suffix}")` | `IntegrityError` باسم `check_wallet_held_balances_non_negative` (held للمراجِع 0 → −10 عند UPDATE). لا تغيير في `balances` ولا `held_balances`؛ 0 صفوف | نفس الشيء لـ`hold_funds` — كان سيزيد الرصيد المتاح لولا القيد |
| **B6** | `release_held_funds(user_id=R, amount=Decimal("-10"), currency="MR_USDT", description="NEGAMT B6", idempotency_key="NEGAMT-B6-{suffix}")` — held للمراجِع 0 | فحص `current_held < amount_decimal` → `0 < -10` = False → يمر؛ UPDATE: held = 0−(−10) = **+10**، balances = 500+(−10) = 490 — القيدان يمران! → ثم `IntegrityError` باسم `check_transaction_amount_positive` عند INSERT. لا تغيير صافٍ | يثبت أن قيد `transactions` هو الحاجز **الوحيد** لـ`release_held_funds` (قيود المحفظة لا تلتقطه) |
| **B7** | `settle_held_funds(sender_id=R, receiver_email=<بريد المُطالِب>, currency="MR_USDT", amount=Decimal("-10"), idempotency_key="NEGAMT-B7-{suffix}")` — held للمراجِع 0 | held للمراجِع 0 → +10 (يمر)، رصيد المُطالِب 100 → 90 (يمر) → `IntegrityError` باسم `check_transaction_amount_positive`. لا تغيير صافٍ | نفس ملاحظة B6: الحاجز الوحيد هو قيد `transactions` |
| **B8** | `review_claim(claim_id=C3, ..., approve=True, approved_amount=Decimal("0"))` | **ينجح**: C3 `PAID`، `approved_amount_mrusdt = 20`، مراجِع 500 → **480**، مُطالِب 100 → **120**، صف دفع واحد `claim_payout_C3`، فاتورة واحدة | اكتشاف `or`: "موافقة بمبلغ صفر" تدفع كامل المطالبة. (المال يتحرك فعلًا هنا — داخل tenant الاختبار فقط، ويُحذف في التنظيف) |

**ملاحظة تحفظ (B1):** ترتيب القفل `sorted([sender_id, receiver.id])` يغيّر ترتيب SELECT فقط؛ ترتيب الـUPDATE ثابت (المرسل أولًا ثم المستلم، `service.py:115-116`). إن ظهر قيد مختلف عن المتوقع في أي حالة سأسجله كما هو ولن أعدّل التوقع بأثر رجعي.

### د.3 تعريف "نجاح الإثبات قبل الإصلاح"

- B1–B7: **كل** الحالات تنتهي بـ`IntegrityError` (أو HTTP 500 في B3) **و** صافي تغيير صفر في الأرصدة والمطالبات والمعاملات والفواتير. ← يؤكد أ.b وأ.c وأ.d حيًّا.
- B8: يدفع 20 كاملة. ← يؤكد اكتشاف `or`.
- **إن تحرك أي مبلغ في B1–B7:** أتوقف فورًا، أسجل ذلك، وأرفع الخطورة إلى HIGH وأعود إليك قبل أي خطوة أخرى — هذا يعني أن استنتاج أ.d خاطئ.
- **لن أُسقط أو أعطّل أي قيد DB** لمحاكاة السرقة.

### د.4 التنظيف (سيُعرض عليك قبل التشغيل، كما طلبت)

في `finally` للسكربت، بنفس منطق `_cleanup` الموجود:
1. `delete from transactions where sender_id = any(:u) or receiver_id = any(:u)` — مستخدمو الاختبار فقط (الجدول بلا `tenant_id`). المتوقع: صف B8 فقط (+ أي صف غير متوقع يُسجَّل).
2. حذف كل صف بـ`tenant_id = :T` من كل جدول فيه عمود `tenant_id` (جولات حتى 8 لحل ترتيب FK).
3. `delete from academy_tenants where id = :T`.
4. استعلام تحقق نهائي: 0 صفوف متبقية للـtenant ولمستخدميه في `users` / `wallets` / `transactions`.

قبل التشغيل سأكتب في هذا التقرير أوامر الحذف الحرفية + عدد الصفوف المتوقع لكل خطوة، وأنتظر موافقتك.

### د.5 ما بعد الإصلاح (للعلم — لن يبدأ قبل موافقتك على نتائج B1–B8)

- نفس B1، B2، B4–B7 → `ValidationError("المبلغ يجب أن يكون أكبر من صفر")` **قبل أي SQL** (لا أقفال، لا UPDATE)؛ صافي تغيير صفر.
- B3 → **422** (تحقق FastAPI على الـQuery)؛ + `approved_amount=0` عبر HTTP → **422**.
- B8 عبر الخدمة مباشرة → يبقى 20 (حد معروف، backlog #7).
- **A1 (إيجابية):** `approved_amount=50` → `PAID`، المراجِع −50، المُطالِب +50، صف دفع واحد، فاتورة واحدة.
- **A2 (إيجابية):** `hold_funds(10)` ثم `release_held_funds(10)` ثم `hold_funds(10)` ثم `settle_held_funds(10)` → أرصدة صحيحة.
- ملف pytest دائم `tests/test_finance_non_positive_amount_guard.py` (نفس نمط seed/cleanup) + regression: `test_insurance_review_claim_status_guard.py`، `test_financeservice_tenant_binding_fix.py`، واختبارات transport/tenders الموجودة — المطلوب صفر تراجع (باستثناء "Backlog #8" المعروفة مسبقًا، تُسجَّل كما هي).

---

## هـ. الحالة الآن

- **لم يُشغَّل أي شيء في هذه الجولة.** لم يُعدَّل أي كود. لا staging، لا commit، لا `PROGRESS_LOG.md`، لا push.
- **بانتظار مراجعة المستخدم الكاملة لهذا القسم وموافقته على §د** قبل تشغيل إثبات "قبل الإصلاح".


---
---

# القسم الإضافي — 2026-09-23 (الجولة الرابعة): نتائج إثبات "قبل الإصلاح" B1–B8

**ملف الأدلة:** `.claude/reports/insurance-negative-approved-amount-evidence-before.txt`
**الكود:** `finance/service.py`، `insurance/router.py`، `insurance/service.py` مطابقة لـHEAD (تحقق بـ`git diff --quiet HEAD` قبل التشغيل). لم يُعدَّل أي كود.
**السكربتات (scratchpad، ليست في git):** `negamt_before.py` (الإعداد + B1–B8)، `negamt_b3_rerun.py`، `negamt_b3_cause.py`.
**الـtenant المؤقت:** `academy_tenants.id=144` (`REGTEST_NEGAMT_bd430284`)، مراجِع `13851`، مُطالِب `13852`، مطالبات C1=194، C2=195، C3=196.

## ر.1 النتائج

| # | الحالة | النتيجة الفعلية | صافي التغيير | الحكم |
|---|---|---|---|---|
| B1 | `review_claim(C1, -50)`، رصيد المُطالِب 0 | `IntegrityError` — `check_wallet_balances_non_negative` (relation `wallets`) | صفر (500/0، C1 `SUBMITTED`، 0 tx، 0 فواتير) | PASS |
| B2 | `review_claim(C1, -50)`، رصيد المُطالِب 100 | `IntegrityError` — `check_transaction_amount_positive` (relation `transactions`) | صفر (500/100) | PASS |
| B3 | HTTP `PUT /api/insurance/claims/195/review?approve=true&approved_amount=-50` | **HTTP 500** `Internal Server Error`؛ السبب (B3b): `IntegrityError` — `check_transaction_amount_positive` | صفر، C2 `SUBMITTED` | PASS (بعد إعادة التشغيل — انظر ر.2) |
| B4 | `transfer(R→C, -10)` | `IntegrityError` — `check_transaction_amount_positive` | صفر | PASS |
| B5 | `hold_funds(R, -10)` | `IntegrityError` — `check_wallet_held_balances_non_negative` | صفر | PASS |
| B6 | `release_held_funds(R, -10)`، held=0 | `IntegrityError` — `check_transaction_amount_positive` (قيود المحفظة مرّت كما توقعنا) | صفر | PASS |
| B7 | `settle_held_funds(R→C, -10)`، held=0 | `IntegrityError` — `check_transaction_amount_positive` | صفر | PASS |
| B8 | `review_claim(C3, approved_amount=0)` | **نجح ودفع 20 كاملة**: C3 `PAID`، `approved_amount=20`، `TX-D341247A5131`، مراجِع 500→480، مُطالِب 100→120، فاتورة واحدة (id 259) | +20 للمُطالِب (متوقع) | PASS (اكتشاف `or` مؤكَّد) |

**أي حركة أموال في B1–B7: لا (`False`).** شرط التوقف في §د.3 لم يتحقق.

**كل قيد في كل حالة طابق التوقع المكتوب مسبقًا في §د.2 حرفيًا** — بما في ذلك الفرق بين B1 (قيد المحفظة يلتقط أولًا) وB2 (قيد `transactions` يلتقط بعد نجاح الـUPDATE-ين داخل الـSAVEPOINT).

## ر.2 انحرافات عن الخطة (للأمانة)

1. **B3 — المحاولة الأولى فشلت بسبب أداة الاختبار لا الكود:** `base_url="http://test"` رُفض من `TrustedHostMiddleware` (`app/main.py:247`، `ALLOWED_HOSTS` في `.env:76`) → HTTP 400 `Invalid host header` قبل الوصول للـendpoint. أُعيد تشغيل B3 وحده بـ`base_url="http://localhost"` (مسموح) على نفس C2 (كانت ما زالت `SUBMITTED`).
2. **B3b — تشغيل إضافي غير مخطط:** إعادة B3 أعطت 500 لكن لوج الخادم لم يطبع traceback، فلم يكن السبب مُثبتًا. شُغِّل نفس الطلب مرة ثالثة بـ`raise_app_exceptions=True` لإظهار الاستثناء: `sqlalchemy.exc.IntegrityError` / `check_transaction_amount_positive`. نفس المدخلات، صفر تغيير.
3. **ترتيب التنفيذ:** B3 وB3b نُفِّذا **بعد** B8 (بسبب الإعادة)، لذا لقطة "before" فيهما تُظهر 480/120 من B8. لا يؤثر على الحكم: المقارنة قبل/بعد لكل منهما متطابقة.
4. **`held_balances` في اللقطات تظهر `None` لـMR_USDT:** الـseed (المنسوخ من الاختبار الموجود) لا يضع `held_balances` صراحةً، والمفتاح غائب → الكود يعامله كـ0 (`held_balances.get(currency, 0)`). المقارنة صحيحة لأنها بقيت `None` قبل وبعد في B5–B7 (أي لم يُكتب أي held).
5. **مراجعة الـAI (`agent_id=10`) فشلت في كل استدعاء لـ`review_claim`** (`الوكيل 10 غير موجود`) — الخطأ يُبلَع بالتصميم، لا أثر على النتائج. سلوك موجود مسبقًا، ليس من هذه الجلسة.

## ر.3 الخلاصة

- **مؤكَّد حيًّا:** الثغرة كما عُلِّمت أصلًا (سرقة أموال بمبلغ سالب) **غير قابلة للاستغلال** اليوم — قيود DB توقفها في كل الدوال الأربع، مع rollback كامل وصافي تغيير صفر. استنتاج §أ.d صحيح.
- **مؤكَّد حيًّا:** طبقة التطبيق بلا حارس، والعميل يتلقى **500** (لا 4xx).
- **مؤكَّد حيًّا:** B6 وB7 يثبتان أن قيد `transactions` هو **الحاجز الوحيد** لـ`release_held_funds` و`settle_held_funds` (قيود المحفظة مرّت).
- **مؤكَّد حيًّا:** `approved_amount=0` يدفع كامل المطالبة.
- الإصلاح المعتمد (§ج) لم يُطبَّق بعد.

## ر.4 التنظيف — الأوامر الحرفية (لم تُشغَّل؛ بانتظار الموافقة)

**عدّ الصفوف الحالي (استعلام قراءة فقط):**

| الجدول | الشرط | عدد الصفوف |
|---|---|---|
| `transactions` | `sender_id` أو `receiver_id` ∈ {13851, 13852} | 1 (دفعة B8) |
| `audit_logs` | `tenant_id=144` | 1 |
| `saas_tenant_service_access` | `tenant_id=144` | 1 |
| `saas_tenant_subscriptions` | `tenant_id=144` | 1 |
| `sovereign_entities_v2` | `tenant_id=144` | 1 |
| `entity_memberships` | `tenant_id=144` | 1 |
| `insurance_policies` | `tenant_id=144` | 1 |
| `insurance_subscriptions` | `tenant_id=144` | 1 |
| `insurance_claims` | `tenant_id=144` | 3 |
| `invoices` | `tenant_id=144` | 1 (فاتورة B8، id 259) |
| `wallets` | `tenant_id=144` | 2 |
| `users` | `tenant_id=144` | 2 |
| `academy_tenants` | `id=144 AND name LIKE 'REGTEST_NEGAMT_%'` | 1 |
| **المجموع** | | **17** |

**الأوامر (سكربت Python واحد بنفس منطق `_cleanup` في `tests/test_insurance_review_claim_status_guard.py:106-133`):**

```sql
-- 1. معاملات مستخدمي الاختبار (الجدول بلا tenant_id)
DELETE FROM transactions WHERE sender_id = ANY(ARRAY[13851,13852]) OR receiver_id = ANY(ARRAY[13851,13852]);   -- متوقع: 1

-- 2. كل جدول فيه عمود tenant_id (عدا academy_tenants)، بجولات حتى 8 لحل ترتيب الـFK،
--    كل DELETE داخل SAVEPOINT خاص (فشل جدول لا يُسقط الباقي):
DELETE FROM "<table>" WHERE tenant_id = 144;                                                                   -- متوقع: 15 إجمالًا عبر 12 جدولًا

-- 3. الـtenant نفسه — مقيَّد بالبادئة كحماية إضافية
DELETE FROM academy_tenants WHERE id = 144 AND name LIKE 'REGTEST_NEGAMT_%';                                     -- متوقع: 1

-- 4. تحقق نهائي (قراءة فقط)
SELECT count(*) FROM users WHERE id IN (13851,13852);                                                            -- متوقع: 0
SELECT count(*) FROM wallets WHERE user_id IN (13851,13852);                                                     -- متوقع: 0
SELECT count(*) FROM transactions WHERE sender_id IN (13851,13852) OR receiver_id IN (13851,13852);              -- متوقع: 0
-- + إعادة عدّ كل جداول tenant_id=144                                                                            -- متوقع: 0 في كل جدول
SELECT count(*) FROM academy_tenants WHERE id = 144;                                                             -- متوقع: 0
```

**تحفظ:** `audit_logs` قد يكون محميًا من الحذف (append-only) — إن فشل حذفه، سيُسجَّل ويبقى صف واحد يتيم بـ`tenant_id=144` (نمط `_cleanup` يتحمّل الفشل). سأبلغ بالنتيجة الفعلية.

**لا شيء آخر يُلمس:** لا مفاتيح idempotency في Redis (لم يُرسل هيدر `Idempotency-Key`)؛ مفاتيح rate-limit الخاصة بـB3 تنتهي تلقائيًا خلال 60 ثانية.

## ر.5 الحالة

- لا كود مُعدَّل. لا staging، لا commit، لا `PROGRESS_LOG.md`.
- بيانات الـtenant 144 **ما زالت في DB** — بانتظار موافقتك على §ر.4.
- الخطوة التالية بعد موافقتك: التنظيف ← تطبيق §ج ← تحقق بعد الإصلاح (§د.5) ← regression ← الـdiff في التقرير ← توقف قبل staging.


---
---

# القسم الإضافي — 2026-09-23 (الجولة الخامسة): التنظيف ← الإصلاح ← تحقق بعد الإصلاح ← اختبار دائم ← regression

## س.1 تنظيف tenant 144 (موافق عليه، نُفِّذ)

سكربت `negamt_cleanup.py` (scratchpad) بنفس أوامر §ر.4 حرفيًا، مع حماية إضافية: يتوقف (`assert`) إن لم يبدأ اسم الـtenant بـ`REGTEST_NEGAMT_`.

```
1. transactions deleted: 1
2. tenant rows deleted: 15 {'audit_logs': 1, 'saas_tenant_service_access': 1, 'saas_tenant_subscriptions': 1, 'sovereign_entities_v2': 1, 'invoices': 1, 'insurance_claims': 3, 'entity_memberships': 1, 'wallets': 2, 'insurance_subscriptions': 1, 'insurance_policies': 1, 'users': 2}
3. academy_tenants deleted: 1
4. verify:
   users 13851/13852 -> 0 ; wallets -> 0 ; transactions -> 0
   tenant_id=144 rows remaining: 0
   academy_tenants id=144: 0
```

- **17 صفًا — مطابق للعدّ المسبق تمامًا.** `audit_logs` حُذف بشكل طبيعي (ليس append-only) — **لا صف يتيم**.

## س.2 الإصلاح المُطبَّق — الـdiff الحرفي (`git diff`)

`git diff --stat`: `finance/service.py | 18 ++++++++++++++----` ، `insurance/router.py | 2 +-` — **15 إضافة، 5 حذف** (تقديري في §ج.6 كان +12/−2؛ الفرق: سطرا فراغ محذوفان مع السطرين المنقولين، وسطر فراغ مضاف في كل من transfer/settle). المحتوى مطابق لـ§ج حرفيًا.

```diff
diff --git a/eppne-backend/app/domains/finance/service.py b/eppne-backend/app/domains/finance/service.py
index 40d43ac..41b4ce2 100644
--- a/eppne-backend/app/domains/finance/service.py
+++ b/eppne-backend/app/domains/finance/service.py
@@ -69,6 +69,12 @@ class FinanceService:
         if not idempotency_key:
             raise ValidationError("Idempotency key is required")
 
+        # مبلغ <= 0 يعكس اتجاه التحويل منطقيًا (فحص الرصيد يمر دائمًا)؛
+        # بدون هذا الحارس الحاجز الوحيد هو CHECK في DB (IntegrityError → 500)
+        amount_decimal = Decimal(str(amount))
+        if amount_decimal <= 0:
+            raise ValidationError("المبلغ يجب أن يكون أكبر من صفر")
+
         existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
         if existing_tx:
             logger.warning(f"Duplicate transfer request detected: {idempotency_key}")
@@ -87,8 +93,6 @@ class FinanceService:
         if crypto_mode == "POINTS_ONLY" and currency != "LOYALTY_POINTS":
             raise PermissionDeniedError("العملات المشفرة معطلة حالياً")
 
-        amount_decimal = Decimal(str(amount))
-
         async with self.db.begin_nested():
             first_id, second_id = sorted([sender_id, cast(int, receiver.id)])
             first_wallet = await self.get_or_create_wallet_for_update(first_id)
@@ -157,6 +161,8 @@ class FinanceService:
         ua: Optional[str] = None
     ):
         amount_decimal = Decimal(str(amount))
+        if amount_decimal <= 0:
+            raise ValidationError("المبلغ يجب أن يكون أكبر من صفر")
 
         if idempotency_key:
             existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
@@ -220,6 +226,8 @@ class FinanceService:
         ua: Optional[str] = None
     ):
         amount_decimal = Decimal(str(amount))
+        if amount_decimal <= 0:
+            raise ValidationError("المبلغ يجب أن يكون أكبر من صفر")
 
         if idempotency_key:
             existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
@@ -286,6 +294,10 @@ class FinanceService:
         if not idempotency_key:
             raise ValidationError("Idempotency key is required")
 
+        amount_decimal = Decimal(str(amount))
+        if amount_decimal <= 0:
+            raise ValidationError("المبلغ يجب أن يكون أكبر من صفر")
+
         existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
         if existing_tx:
             logger.warning(f"Duplicate settlement request detected: {idempotency_key}")
@@ -299,8 +311,6 @@ class FinanceService:
         if receiver.tenant_id != self.tenant_id:
             raise PermissionDeniedError("المستلم لا يخص هذا المستأجر")
 
-        amount_decimal = Decimal(str(amount))
-
         async with self.db.begin_nested():
             first_id, second_id = sorted([sender_id, cast(int, receiver.id)])
             first_wallet = await self.get_or_create_wallet_for_update(first_id)
diff --git a/eppne-backend/app/domains/insurance/router.py b/eppne-backend/app/domains/insurance/router.py
index 3e5bb03..acf9e25 100644
--- a/eppne-backend/app/domains/insurance/router.py
+++ b/eppne-backend/app/domains/insurance/router.py
@@ -222,7 +222,7 @@ async def get_my_claims(
 async def review_claim(
     claim_id: int,
     approve: bool = Query(..., description="true للموافقة، false للرفض"),
-    approved_amount: Optional[Decimal] = Query(None, description="المبلغ المعتمد (إن كانت الموافقة)"),
+    approved_amount: Optional[Decimal] = Query(None, gt=0, description="المبلغ المعتمد (إن كانت الموافقة)"),
     notes: Optional[str] = Query(None, description="ملاحظات المراجعة"),
     idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
     current_user: User = Depends(get_current_active_user),
```

- `mint` (الدالة الخامسة التي تحوي `amount_decimal = Decimal(str(amount))`) **لم تُلمس** — خارج النطاق المعتمد.
- `ValidationError` → `status_code=422` (`app/core/errors.py:54-56`).

## س.3 التحقق الحي بعد الإصلاح (§د.5)

**ملف الأدلة:** `.claude/reports/insurance-negative-approved-amount-evidence-after.txt` — **15/15 PASS، 0 FAIL.**
**الأداة:** `negamt_after.py` (scratchpad) — نفس seed الجولة السابقة + مطالبة رابعة C4؛ مستمع SQLAlchemy `before_cursor_execute` على `engine.sync_engine` يعدّ كل عبارات SQL أثناء كل استدعاء.
**الـtenant المؤقت:** 145 (`REGTEST_NEGAMT_b2a93b7b`)، مراجِع 13853، مُطالِب 13854، C1=197، C2=198، C3=199، C4=200.

| # | يقابل | الإجراء | النتيجة | الحكم |
|---|---|---|---|---|
| N1 | B1 | `review_claim(C1, -50)`، رصيد المُطالِب 0 | `ValidationError: المبلغ يجب أن يكون أكبر من صفر`؛ 16 عبارة SQL (جلب المطالبة/العضوية/قفل الصف)، **0** UPDATE wallets / INSERT transactions؛ صفر تغيير | PASS |
| N2 | B2 | نفسه، رصيد المُطالِب 100 | نفسه | PASS |
| N3 | B3 | HTTP `approved_amount=-50` | **422** `{"type":"greater_than","loc":["query","approved_amount"],"msg":"Input should be greater than 0"}`؛ صفر تغيير | PASS |
| N3b | — | HTTP `approved_amount=0` | **422** نفس الرسالة | PASS |
| N4 | B4 | `transfer(-10)` و`transfer(0)` | `ValidationError`؛ **0 عبارات SQL** | PASS ×2 |
| N5 | B5 | `hold_funds(-10)` و`(0)` | `ValidationError`؛ **0 عبارات SQL** | PASS ×2 |
| N6 | B6 | `release_held_funds(-10)` و`(0)` | `ValidationError`؛ **0 عبارات SQL** | PASS ×2 |
| N7 | B7 | `settle_held_funds(-10)` و`(0)` | `ValidationError`؛ **0 عبارات SQL** | PASS ×2 |
| N8 | B8 | `review_claim(C3, 0)` مباشرة على الخدمة | **يدفع 20 كاملة** (480/120) — الحد المعروف، backlog #7 | PASS (كما هو متوقع) |
| A1 | إيجابي | HTTP `approved_amount=50` على C4 | **200**، C4 `PAID`، `approved_amount=50`، مراجِع 480→430، مُطالِب 120→170، +1 معاملة، +1 فاتورة | PASS |
| A2 | إيجابي | `hold 10 → release 10 → hold 10 → settle 10` | (420,held 10) → (430,held 0) → (420,held 10) → (420,held 0) + مُطالِب 170→180؛ +4 معاملات | PASS |

**ملاحظة A1:** `approved_amount=50` أكبر من `claimed_amount=20` ودُفع 50 — سلوك موجود مسبقًا (السقف الوحيد هو `max_coverage_limit`)، مذكور في §1، خارج النطاق؛ لم يتغير بالإصلاح.

**"قبل أي SQL":** مُثبت حرفيًا لكل الدوال الأربع (0 عبارات). في N1/N2 تحدث عبارات SQL قبل الوصول لـ`transfer` (منطق `review_claim` نفسه)، لكن الحارس يطلق قبل أي قفل على المحافظ أو UPDATE أو INSERT.

## س.4 الاختبار الدائم `tests/test_finance_non_positive_amount_guard.py` (ملف جديد، untracked)

- 10 اختبارات: 8 (`parametrize` 4 دوال × {-10, 0}) تتحقق من `ValidationError` + `status_code == 422` + **صفر عبارات SQL** + صفر تغيير؛ 1 لـ`review_claim(-50)` على الخدمة؛ 1 HTTP (`-50` و`0` → 422، ثم `50` → 200 ودفع صحيح 450/150).
- نفس نمط `test_insurance_review_claim_status_guard.py` (seed/cleanup ذاتيان، tenant بادئته `REGTEST_NEGGUARD_*`، حذف كامل في `finally`)؛ مكتفٍ ذاتيًا (لا استيراد من ملف اختبار آخر — لا سابقة لذلك في `tests/`).
- **على الكود المُصلَح: `10 passed` (590 ث).**
- **Mutation check — على كود HEAD (الملفان أُعيدا مؤقتًا بـ`git show HEAD:...`، ثم استُعيد الإصلاح من نسخة احتياطية + `cmp` للتأكد): `10 failed` (341 ث)**، كلها بـ`IntegrityError` من `check_transaction_amount_positive` (8) أو `check_wallet_held_balances_non_negative` (1)؛ اختبار HTTP فشل لأن الـendpoint قبل `-50` (لا 422). بعد الاستعادة: `git diff --stat` مطابق (15/5).
- تحقق بعد التشغيلين: **0** tenants متبقية بالبادئة `REGTEST_NEGGUARD_%`.

## س.5 Regression

```
pytest tests/test_insurance_review_claim_status_guard.py tests/test_financeservice_tenant_binding_fix.py
       tests/test_tenders_auctions_finance_hold_release_settle.py
       tests/test_transport_entity_membership_full_implementation.py tests/test_transport_fleet_entity_id_required.py
       tests/test_transport_getter_endpoints_wiring.py tests/test_transport_vehicles_fleets_drivers.py
→ 26 passed, 40 warnings in 236.76s — 0 failed, 0 errors
```

- **صفر إخفاقات** — ولا حتى الإخفاقات المعروفة مسبقًا ("Backlog #8") ظهرت في هذه المجموعات.
- ملاحظة معروفة مسبقًا (ليست من هذه الجلسة): اختبار FINBIND يسرّب رصيد user1 (مسجَّل في جلسة review_claim) — لم يُفحص/يُعالَج هنا.

## س.6 تنظيف tenant 145 (بيانات التحقق بعد الإصلاح) — الأوامر الحرفية، **لم تُشغَّل؛ بانتظار الموافقة**

**عدّ الصفوف (قراءة فقط):**

| الجدول | الشرط | العدد |
|---|---|---|
| `transactions` | `sender_id`/`receiver_id` ∈ {13853, 13854} | 6 (N8 + A1 + 4×A2) |
| `audit_logs` | `tenant_id=145` | 6 |
| `saas_tenant_service_access` | `tenant_id=145` | 1 |
| `saas_tenant_subscriptions` | `tenant_id=145` | 1 |
| `sovereign_entities_v2` | `tenant_id=145` | 1 |
| `entity_memberships` | `tenant_id=145` | 1 |
| `insurance_policies` | `tenant_id=145` | 1 |
| `insurance_subscriptions` | `tenant_id=145` | 1 |
| `insurance_claims` | `tenant_id=145` | 4 |
| `invoices` | `tenant_id=145` | 2 |
| `wallets` | `tenant_id=145` | 2 |
| `users` | `tenant_id=145` | 2 |
| `academy_tenants` | `id=145 AND name LIKE 'REGTEST_NEGAMT_%'` | 1 |
| **المجموع** | | **29** (6 + 22 + 1) |

**الأوامر** (نفس السكربت `negamt_cleanup.py` الذي نُفِّذ على 144، بالمعاملات `145 13853,13854 REGTEST_NEGAMT_`):

```sql
-- 0. حماية: assert أن اسم academy_tenants.id=145 يبدأ بـ'REGTEST_NEGAMT_' وإلا توقف
DELETE FROM transactions WHERE sender_id = ANY(ARRAY[13853,13854]) OR receiver_id = ANY(ARRAY[13853,13854]);   -- متوقع: 6
DELETE FROM "<table>" WHERE tenant_id = 145;   -- كل جدول فيه tenant_id، جولات حتى 8، كل DELETE في SAVEPOINT   -- متوقع: 22 عبر 12 جدولًا
DELETE FROM academy_tenants WHERE id = 145 AND name LIKE 'REGTEST_NEGAMT_%';                                     -- متوقع: 1
-- تحقق: users/wallets/transactions لـ13853,13854 = 0 ؛ كل جداول tenant_id=145 = 0 ؛ academy_tenants id=145 = 0
```

## س.7 الحالة

| البند | الحالة |
|---|---|
| تنظيف 144 | ✅ نُفِّذ، 17/17، صفر متبقٍ |
| الإصلاح (§ج) | ✅ مُطبَّق في شجرة العمل — **غير staged** |
| تحقق بعد الإصلاح | ✅ 15/15 PASS |
| اختبار دائم | ✅ 10/10 على الإصلاح؛ 10/10 FAIL على HEAD (mutation) — **untracked** |
| Regression | ✅ 26/26، صفر إخفاقات |
| تنظيف 145 | ⏸ بانتظار الموافقة (§س.6) |
| staging / commit / `PROGRESS_LOG.md` / push | ⛔ لم يُلمس — متوقف هنا |

**ملفات الجلسة المتغيرة:** `eppne-backend/app/domains/finance/service.py` (M)، `eppne-backend/app/domains/insurance/router.py` (M)، `eppne-backend/tests/test_finance_non_positive_amount_guard.py` (??)، + ملفات التقارير في `.claude/reports/` (هذا التقرير، `...-evidence-before.txt`، `...-evidence-after.txt`).


---
---

# القسم الإضافي — 2026-09-23 (الجولة السادسة): تنظيف 145 + staging + مسودة PROGRESS_LOG

## ص.1 تنظيف tenant 145 (موافق عليه، نُفِّذ)

```
1. transactions deleted: 6
2. tenant rows deleted: 22 {'audit_logs': 6, 'saas_tenant_service_access': 1, 'saas_tenant_subscriptions': 1, 'sovereign_entities_v2': 1, 'invoices': 2, 'insurance_claims': 4, 'entity_memberships': 1, 'wallets': 2, 'insurance_subscriptions': 1, 'insurance_policies': 1, 'users': 2}
3. academy_tenants deleted: 1
4. verify: users/wallets/transactions (13853,13854) -> 0 ; tenant_id=145 rows remaining: 0 ; academy_tenants id=145: 0
+ academy_tenants بالبادئة REGTEST_NEGAMT_% أو REGTEST_NEGGUARD_% المتبقية: 0
```

**29 صفًا — مطابق للعدّ المسبق تمامًا. صفر بيانات اختبار متبقية من هذه الجلسة في DB.**

## ص.2 Staging

- الـindex كان **فارغًا** قبل الـstaging (`git diff --cached --name-only` → لا شيء) — لا ملفات staged مسبقًا من جلسات أخرى.
- نفس نمط `88097be`: كود + اختبار + تقرير الجلسة + ملفات الأدلة. 6 ملفات، كلها بـpathspec صريح لملفات كاملة (لا hunks جزئية — الملفات الثلاثة في الكود كانت نظيفة عند HEAD قبل الجلسة؛ ملفات التقرير والاختبار جديدة).
- **هذه المسودة كُتبت في التقرير قبل الـstaging** عمدًا، لكي يطابق الـsnapshot المُجهَّز شجرة العمل حرفيًا (لا تعديلات unstaged على التقرير بعد الـstaging).
- `PROGRESS_LOG.md` **غير مشمول** — فيه تعديلات غير committed مسبقة من جلسات أخرى (+670/−1)؛ سيُعالَج في commit `docs:` منفصل بـhunk staging بعد موافقتك.

**رسالة الـcommit المقترحة (من المستخدم):**
```
fix(finance): reject non-positive amounts in transfer/hold_funds/release_held_funds/settle_held_funds + insurance approved_amount gt=0
```
(الجسم المقترح — للمراجعة، مني:)
```
The flagged "negative approved_amount reverses the payout" finding was
re-verified live: DB CHECK constraints (transactions.amount > 0, non-negative
wallet balances) already block any fund movement, but only at the DB layer —
every non-positive amount surfaced as an unhandled IntegrityError (HTTP 500),
and release/settle were protected by the transactions constraint alone.

- FinanceService.transfer / hold_funds / release_held_funds / settle_held_funds
  raise ValidationError (422) for amount <= 0 before any SQL
- PUT /insurance/claims/{id}/review: approved_amount Query gt=0 (also closes
  approved_amount=0 silently paying the full claimed amount via HTTP)
- regression test: 10 cases fail on the old code (IntegrityError), pass on the fix

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

## ص.3 مسودة إدخال `PROGRESS_LOG.md` (لم تُكتب بعد)

**الموضع:** مباشرة بعد السطر 1060 الحالي (صف `insurance-review-claim-negative-approved-amount-reverses-transfer` — آخر صف في جدول الـbacklog، يليه سطر فارغ ثم `---`). الصف الأصلي **لا يُعدَّل**. الإضافة = 10 صفوف backlog جديدة داخل نفس الجدول، ثم سطر فارغ، ثم فقرة الإغلاق المؤرَّخة (نفس نمط فقرة "✅ إغلاق جزئي مؤرَّخ" في السطر 1035). `<HASH>` يُستبدل بالـhash الفعلي بعد الـcommit.

### ص.3.1 الصفوف العشرة الجديدة (تُلحق بالجدول)

```markdown
| — | **`social-physical-gift-product-price-no-positive-constraint`** [2026-09-23] — اكتُشف في جلسة `insurance-negative-approved-amount-verification` (§3/§ب، الصف 24): `social/schemas.py:169` `product_price_mrusdt` بلا `gt=0` ولا حارس في `request_physical_gift` (`social/service.py:590`). منذ `<HASH>` المبلغ غير الموجب يُرفض مركزيًا في `FinanceService` (422) — المتبقي دفاع إضافي على مستوى الـschema فقط. أولوية منخفضة. |
| — | **`projects-contribution-amount-no-positive-constraint`** [2026-09-23] — نفس الجلسة (الصف 16): `projects/schemas.py:69` `amount_mrusdt` (Optional) بلا `gt=0`؛ المساهمة النقدية تمرره مباشرة لـ`finance.transfer` (`projects/service.py:185`). مغطى مركزيًا منذ `<HASH>`؛ المتبقي قيد schema. أولوية منخفضة. |
| — | **`transport-booking-seats-count-no-min`** [2026-09-23] — نفس الجلسة (الصف 36): `transport/schemas.py:131` `seats_count` بلا `ge=1` → `fare = base_fare × seats_count` سالب/صفر → `hold_funds` (`transport/service.py:478`). مغطى مركزيًا منذ `<HASH>`؛ المتبقي قيد schema. أولوية منخفضة. |
| — | **`merchant-set-prices-no-nonnegative-constraint`** [2026-09-23] — نفس الجلسة (فئة B): أسعار يضعها تاجر/منشئ/صاحب عمل/مسؤول بلا `ge=0`: commerce `price_mrusdt`/`wholesale_price_mrusdt` (`schemas.py:44,50`)، tourism_sports `base_price_mrusdt`/`base_ticket_price_mrusdt` (`schemas.py:44,97`)، transport `base_fare_mrusdt` (`schemas.py:101`)، social أسعار خطط المجموعات (`schemas.py:184-185`)، saas `price_monthly` (`schemas.py:39`)، employment `base_salary` (`schemas.py:70`). قبل `<HASH>`: سعر سالب → 500 للمشتري؛ بعده → 422. المتبقي قيود schema. أولوية منخفضة. |
| — | **`digital-twin-negative-duration-free-interaction`** [2026-09-23] — نفس الجلسة (الصف 6): `digital_twin/schemas.py:49` `duration_minutes` بلا قيد → `fee × duration` سالب → حارس `if fee > 0` يتخطى الدفع → تفاعل مجاني يُسجَّل بمدة سالبة (ليس عكس أموال؛ الحارس المركزي لا يلتقطه لأن `transfer` لا يُستدعى). أولوية منخفضة. |
| — | **`no-global-integrityerror-handler`** [2026-09-23] — نفس الجلسة: `app/main.py` فيه handlers لـ`SovereignError`/`IdempotencyError`/`RateLimitError` فقط؛ أي انتهاك قيد DB يخرج كـ500 عام بلا traceback في اللوج (مُثبت حيًا في B3 قبل الإصلاح). أولوية منخفضة–متوسطة. |
| — | **`review-claim-zero-amount-falls-back-to-claimed`** [2026-09-23] — نفس الجلسة: `insurance/service.py:524` `final_amount = approved_amount or claimed` — `Decimal("0")` falsy → الموافقة بـ0 تدفع كامل المبلغ المطالب به (مُثبت حيًا: B8 قبل الإصلاح، N8 بعده). عبر HTTP مغلق منذ `<HASH>` (`gt=0` → 422)؛ مستدعٍ داخلي يمرر 0 مباشرة لا يزال يدفع كاملًا. الإصلاح: `approved_amount if approved_amount is not None else claimed`. أولوية منخفضة. |
| — | **`social-group-subscription-duration-months-no-min`** [2026-09-23] — نفس الجلسة (الصف 25): `social/schemas.py:196` `duration_months` من الطلب بلا حد أدنى (`social/router.py:389`) → `price_monthly × duration_months` سالب/صفر (`social/service.py:671`). مغطى مركزيًا منذ `<HASH>`؛ المتبقي قيد schema (`ge=1`). أولوية منخفضة. |
| — | **`transport-delivery-fee-no-nonnegative-constraint`** [2026-09-23] — نفس الجلسة (الصف 38): `DeliveryTaskCreate.delivery_fee_mrusdt` (`transport/schemas.py:157`) بلا `ge=0` — المُرسِل يضع الرسوم (`transport/service.py:701`) ثم هو نفسه الدافع (`hold_funds`، `service.py:814`). مغطى مركزيًا منذ `<HASH>`؛ المتبقي قيد schema. أولوية منخفضة. |
| — | **`tenders-min-increment-no-nonnegative-constraint`** [2026-09-23] — نفس الجلسة (الصف 32): `tenders_auctions/schemas.py:75` `min_increment_mrusdt` بلا `ge=0` → منشئ المزاد يضع زيادة سالبة → `min_required = current_highest + min_increment` (`service.py:390`) قد يصبح سالبًا → مزايدة سالبة تصل `hold_funds`. مغطى مركزيًا منذ `<HASH>`؛ المتبقي قيد schema. أولوية منخفضة. |
```

### ص.3.2 فقرة الإغلاق (بعد سطر فارغ من الجدول)

```markdown
**✅ إغلاق مؤرَّخ [2026-09-23] — `insurance-review-claim-negative-approved-amount-reverses-transfer`: مُغلَق (commit `<HASH>`)، مع تصحيح تصنيف الخطورة.** جلسة `insurance-negative-approved-amount-verification` (تقرير: `.claude/reports/insurance-negative-approved-amount-verification-session-log.md`). **التصحيح:** الملاحظة الأصلية ("مُصدِر خبيث يسرق أموال المُطالِبين بمبلغ سالب") **بُنيت على قراءة ناقصة** — فاتها قيود DB: `transactions.check_transaction_amount_positive` (`CHECK (amount > 0)`، migration `71820e4fe1f3...:2034`) و`wallets.check_wallet_balances_non_negative` / `check_wallet_held_balances_non_negative`. كل دوال `FinanceService` الأربع تُحدِّث المحافظ وتُدرج صف `Transaction` داخل نفس `begin_nested()` بلا commit داخلي → أي مبلغ `<= 0` يُلغى بالكامل. **BEFORE (حي، تينانت throwaway 144، كود غير مُصلَح):** B1–B7 — `review_claim(-50)` (بمُطالِب رصيده 0 ثم 100)، HTTP (`-50`)، و`transfer`/`hold_funds`/`release_held_funds`/`settle_held_funds(-10)` مباشرة — **كلها `IntegrityError` بصافي تغيير صفر** (لا حركة أموال)، لكن العميل يتلقى **HTTP 500**؛ B6/B7 أثبتا أن قيد `transactions` هو **الحاجز الوحيد** لـrelease/settle (قيود المحفظة مرّت)؛ B8 — `approved_amount=0` **دفع كامل المطالبة (20)**. **الخطورة الفعلية:** hardening + تصحيح كود خطأ (منخفضة–متوسطة)، **ليست سرقة**. **الإصلاح (2 ملف، +15/−5):** حارس `amount <= 0 → ValidationError (422)` في أول الدوال الأربع قبل أي SQL (`finance/service.py`)؛ `approved_amount: Query(None, gt=0)` (`insurance/router.py:225`). **AFTER (تينانت 145):** 15/15 — الدوال الأربع ترفض `-10` و`0` بـ**صفر عبارات SQL** (مستمع `before_cursor_execute`)؛ HTTP `-50`/`0` → 422؛ التدفقات الموجبة (موافقة 50 عبر HTTP، hold→release→hold→settle) سليمة؛ الموافقة بـ0 عبر الخدمة مباشرة لا تزال تدفع كاملًا (backlog `review-claim-zero-amount-falls-back-to-claimed`). **اختبار دائم:** `tests/test_finance_non_positive_amount_guard.py` — 10/10 على الإصلاح، 10/10 FAIL على HEAD (mutation check). **Regression:** 26/26 (insurance status guard، FINBIND، tenders hold/release/settle، 4 مجموعات transport). **تنظيف:** التينانتان 144 (17 صفًا) و145 (29 صفًا) حُذفا بالكامل، صفر متبقٍ. **مواقع الاستدعاء:** 40 موقعًا لـ`transfer`/`hold`/`release`/`settle` صُنِّفت (7 A، 10 B، 23 S) — الحارس المركزي يغطيها كلها؛ قيود الـschema لمواقع A/B → 10 بنود backlog أعلاه (توثيق فقط، بقرار المستخدم).
```

## ص.4 الحالة

- staging: 6 ملفات (انظر الطرفية لـ`--name-only` و`--stat`). **لا commit بعد — بانتظار الموافقة الصريحة.**
- `PROGRESS_LOG.md`: لم يُكتب — المسودة أعلاه بانتظار المراجعة.
- لا push.


---
---

# القسم الإضافي — 2026-09-23 (الجولة السابعة): المخرجات الحرفية للـstaging قبل الـcommit

بطلب المستخدم: المخرجات الحرفية لـ`git diff --cached` هنا (لا "انظر الطرفية"). هذا القسم نفسه جزء من التقرير المُجهَّز، لذا الأرقام أدناه تشمله: حُسبت مسبقًا، ثم أُعيد staging التقرير (ملف جديد كامل — لا hunks)، ثم قورنت بالمخرجات الفعلية للأمر (نتيجة المقارنة في الطرفية وفي §ط.3).

## ط.1 `git diff --cached --name-only`

```
.claude/reports/insurance-negative-approved-amount-evidence-after.txt
.claude/reports/insurance-negative-approved-amount-evidence-before.txt
.claude/reports/insurance-negative-approved-amount-verification-session-log.md
eppne-backend/app/domains/finance/service.py
eppne-backend/app/domains/insurance/router.py
eppne-backend/tests/test_finance_non_positive_amount_guard.py
```

## ط.2 `git diff --cached --stat`

```
 ...nce-negative-approved-amount-evidence-after.txt |  124 ++
 ...ce-negative-approved-amount-evidence-before.txt |   89 ++
 ...ive-approved-amount-verification-session-log.md | 1252 ++++++++++++++++++++
 eppne-backend/app/domains/finance/service.py       |   18 +-
 eppne-backend/app/domains/insurance/router.py      |    2 +-
 .../test_finance_non_positive_amount_guard.py      |  240 ++++
 6 files changed, 1720 insertions(+), 5 deletions(-)
```

## ط.3 الملاحظات

- 6 ملفات: 3 كود/اختبار (`finance/service.py` 18 سطرًا = +14/−4؛ `insurance/router.py` 2 = +1/−1؛ ملف الاختبار الجديد 240) + 3 ملفات تقارير (التقرير، أدلة before، أدلة after).
- `PROGRESS_LOG.md` **غير مُجهَّز** — commit `docs:` منفصل بعد هذا الـcommit.
- لا ملفات أخرى في الـindex؛ لا تعديلات unstaged متبقية في هذه المسارات الستة.
- التحقق: مخرجات `git diff --cached --stat` الفعلية بعد إعادة الـstaging طابقت ط.1/ط.2 أعلاه حرفيًا (مقارنة آلية).
- الحالة: **لا commit بعد** — بانتظار الموافقة النهائية الصريحة من المستخدم.


---
---

# القسم الإضافي — 2026-09-23 (الجولة الثامنة): commit الإصلاح + مسودة PROGRESS_LOG مُطبَّقة ومُجهَّزة

## ق.1 commit الإصلاح (موافق عليه، نُفِّذ)

- **`58b30aff91cce28a0d40dcda68f67df2df021403`** — `fix(finance): reject non-positive amounts in transfer/hold_funds/release_held_funds/settle_held_funds + insurance approved_amount gt=0` (الرسالة + الجسم من §ص.2 حرفيًا).
- `git show --stat HEAD`: نفس الملفات الستة و`1720 insertions(+), 5 deletions(-)` — مطابق لـ§ط.2.
- الـindex فارغ بعد الـcommit. **لا push** (`main` بلا upstream مُتتبَّع).

## ق.2 تطبيق مسودة §ص.3 على `PROGRESS_LOG.md`

- `<HASH>` → `58b30af` (كل المواضع؛ تحقق آلي: لا `<HASH>` متبقٍ).
- الموضع: بعد صف `insurance-review-claim-negative-approved-amount-reverses-transfer` (السطر 1060 في HEAD وفي شجرة العمل — تحقق آلي: الصف فريد، والسطر التالي فارغ = آخر صف في الجدول). الصف الأصلي لم يُعدَّل.
- **12 سطرًا مضافًا:** 10 صفوف backlog + سطر فارغ + فقرة الإغلاق.
- **الـstaging بلا `git add`:** `PROGRESS_LOG.md` في شجرة العمل فيه تعديلات غير committed من جلسات أخرى (+670/−1). بُني الـblob المُجهَّز من **نسخة HEAD** + إدخالنا فقط (`git hash-object -w` ثم `git update-index --cacheinfo`) — فلا يدخل الـindex أي سطر من تلك التعديلات. نهايات الأسطر: HEAD بـLF (محفوظة)، شجرة العمل بـCRLF (محفوظة).
- تحقق: `git diff -- PROGRESS_LOG.md` (شجرة العمل مقابل الـindex) لا يزال `670 insertions(+), 1 deletion(-)` — تعديلات الجلسات الأخرى بقيت unstaged ولم تتغير.

## ق.3 الـdiff الحرفي المُجهَّز لـ`PROGRESS_LOG.md` (`git diff --cached -- PROGRESS_LOG.md`)

```diff
diff --git a/PROGRESS_LOG.md b/PROGRESS_LOG.md
index dc3d214..68f22ad 100644
--- a/PROGRESS_LOG.md
+++ b/PROGRESS_LOG.md
@@ -1058,6 +1058,18 @@ seed حقيقي (5 صفوف/دومين عبر `docker exec psql` مباشر) + 
 | — | **`admin-kill-switch-regression-suite-side-effects`** [2026-09-22] — *لم تُصلَح، غير خاصة بمنطق الـkill switch نفسه:* أثناء تشغيل مجموعة الانحدار (147 اختبارًا) للتحقق من عدم كسر شيء بعد 0-C، ظهرت 3 آثار جانبية **من الاختبارات القديمة نفسها، ليست من تعديلات هذه الجلسة**: (1) **`admin-kill-switch-realestate-invoice-ordering-guard-stale`** — الفشل الوحيد في المجموعة (`test_realestate_buy_fractional_ownership_invoice_ordering`) حارس بنيوي (`inspect.getsource`) قديم مقابل بنية `buy_fractional_ownership` الحالية (كتلة `try/except` جديدة لاستدعاء AI أُضيفت قبل كتلة الفاتورة في جلسة أخرى غير متعلقة) — لم يُشغَّل الكود الفعلي، `realestate/service.py` لم يُلمَس في 0-C؛ (2) مجموعات الانحدار **تغيّر رصيد محفظتي حسابَي اختبار دائمَين** (`wallets.id=41`/`45`) وتترك **رسائل Celery يتيمة** في طابور `celery` (931 رسالة متراكمة من جلسات سابقة، منها اثنتان من هذه الجلسة أُزيلتا) وكاش Redis لمستخدمين محذوفين — لا baseline على مستوى الصفوف لهذين الحسابين لتمكين استعادة دقيقة مستقبلًا؛ (3) توصية منهجية: أي لقطة zero-diff مستقبلية يجب أن تحفظ صفوف `wallets`/`users` الحساسة كاملة، لا فقط md5/عدد الصفوف. **قرار المالك [2026-09-22]:** أرصدة `wallets` 41/45 تُترَك كما هي — لا استعادة (جدول `transactions` لم يتغيّر، فلا فقد محاسبي حقيقي؛ أي استعادة الآن تخمين غير مسجَّل). | 🟡 **مفتوح، أولوية متوسطة — منهجي، يخص كل مجموعات الانحدار الحية لا 0-C تحديدًا** | `.claude/reports/admin-batch0c-kill-switch-session-log.md` §الجزء الرابع (B-12، B-13، B-14) |
 | — | **`test-financeservice-tenant-binding-leaks-user1-funds`** [2026-09-23] — اكتُشف أثناء regression جلسة `insurance-review-claim-double-payment-verification` (مقارنة لقطة zero-diff فشلت): اختبارا `tests/test_financeservice_tenant_binding_fix.py` — `test_process_auto_renewals_admin_sentinel_full_loop_success_and_past_due` (اشتراك `REGTEST-FINBIND-PLAN-cheap-*`) و`test_pay_invoice_same_tenant_still_works_after_removing_self_finance` — يحرّكان **أموالًا حقيقية** من **user 1** (محفظة 39، تينانت 1) إلى **حساب نظام تينانت 1** (user 957، محفظة 929): 1 MR_USDT لكلٍّ عبر `FinanceService.transfer` (مفتاحا `AUTO-RENEW-{sub_id}-{YYYY-MM}` و`PAY-INV-{invoice_id}`). دوال `_cleanup` في الملف تحذف الاشتراك/الخطة/الخدمة لكنها **لا تعكس التحويل ولا تحذف صفّي `transactions`/`audit_logs`** → كل تشغيل للملف: user 1 −2، حساب النظام +2، +2 صف `transactions`، +2 صف `audit_logs`. **مؤكَّد مرتين:** 2026-09-18 (tx #907 `PAY-INV-158`، #920 `AUTO-RENEW-834-2026-09`) و2026-09-23 (tx #948 `AUTO-RENEW-851-2026-09`، #950 `PAY-INV-161`). **تسرّب 09-23 عُكِس يدويًا** بـSQL مُحرَس في نفس الجلسة (`.claude/reports/insurance-review-claim-double-payment-leak-reversal.sql`: user 1 708→710، 957 167→165، حذف الصفوف الأربعة) → zero-diff. **تسرّب 09-18 لم يُعكَس** — أي أن "user 1 = 710.0" المستخدَم كـbaseline في Batch 0-A وفي هذه الجلسة كان **بعده** أصلًا. **الحل المتوقَّع (لم يُنفَّذ):** (أ) تشغيل الاختبارين على مستخدم/تينانت throwaway مموَّل بدل user 1 — **الأنظف**، ومتسق مع نمط التينانت throwaway في باقي الاختبارات؛ أو (ب) عكس صريح في `_cleanup` (حذف `transactions`/`audit_logs` بالمفتاح + إرجاع الرصيدين). **تحذير لأي جلسة قادمة:** أي مقارنة zero-diff تشمل تشغيل هذا الملف ستفشل بـ−2 على user 1 — ليس باجًا في الكود قيد الاختبار. | 🟡 **مفتوح، أولوية متوسطة** — لا يمس كود إنتاج، لكنه يلوّث user 1 وحساب النظام الحقيقيين في كل تشغيل regression | `.claude/reports/insurance-review-claim-double-payment-verification-session-log.md` §14.5، §15.1–15.3، §16.1 |
 | — | **`insurance-review-claim-negative-approved-amount-reverses-transfer`** [2026-09-23] — *ملاحظة بالقراءة الثابتة أثناء جلسة `insurance-review-claim-double-payment-verification`، **غير مُتحقَّق منها حيًا، وليست ثغرة مؤكَّدة**:* `PUT /insurance/claims/{id}/review` يقبل `approved_amount` **سالبًا**: (1) `insurance/router.py:225` — `approved_amount: Optional[Decimal] = Query(None, ...)` بلا `gt=0`؛ (2) `insurance/service.py` (`final_amount = approved_amount or claimed`، سطر 524 بعد الإصلاح) — الـcap على الحد الأعلى فقط (`> max_coverage_limit`)؛ (3) **`FinanceService.transfer` (`finance/service.py:90-113`) لا يفحص `amount > 0`**: مع `amount=-50` فحص الرصيد `sender_current < -50` خطأ دائمًا → يمر، ثم رصيد المُرسِل (المراجِع) **يزيد** 50 ورصيد المستلم (المطالِب) **ينقص** 50 — وقد يصبح سالبًا (لا فحص على المستلم) — ثم `status=PAID` و`approved_amount_mrusdt=-50` وفاتورة بمبلغ سالب. **شرط الهجوم:** OWNER/EXECUTIVE_DIRECTOR على الكيان المُصدِر للبوليصة — أي مُصدِر تأمين خبيث يسحب من مشتركيه بـ"مراجعة" مطالباتهم. **إصلاح `review_claim` [2026-09-23] لا يغلقه** (مطالبة `SUBMITTED` تقبل مراجعة أولى بمبلغ سالب). **نطاق أوسع:** `FinanceService.transfer` مشترك بين كل الدومينات — أي مستدعٍ يمرّر مبلغًا يتحكم فيه المستخدم بلا تحقق `> 0` معرَّض لنفس الانعكاس؛ و`hold_funds`/`release` (`finance/service.py:159`، `:222`) بنفس النمط ظاهريًا. **نقطة البداية للجلسة المخصصة:** (1) تحقق حي على تينانت throwaway (`approved_amount=-50`)؛ (2) grep كل استدعاءات `finance.transfer(`/`hold_funds(` وتصنيف مصدر `amount`؛ (3) قرار: حارس مركزي في `transfer` (`amount <= 0 → ValidationError`) + `gt=0` في الـrouter. **ملاحظة جانبية:** `approved_amount=0` يُعامَل كـ"غير مُرسَل" (`or`) فيُدفع المبلغ المطالَب به كاملًا. | 🔴 **غير مُتحقَّق منه — أولوية عالية (احتمال سرقة أموال)**؛ جلسة مخصصة ضيقة (قرار المستخدم 2026-09-23) | `.claude/reports/insurance-review-claim-double-payment-verification-session-log.md` §6، §11 |
+| — | **`social-physical-gift-product-price-no-positive-constraint`** [2026-09-23] — اكتُشف في جلسة `insurance-negative-approved-amount-verification` (§3/§ب، الصف 24): `social/schemas.py:169` `product_price_mrusdt` بلا `gt=0` ولا حارس في `request_physical_gift` (`social/service.py:590`). منذ `58b30af` المبلغ غير الموجب يُرفض مركزيًا في `FinanceService` (422) — المتبقي دفاع إضافي على مستوى الـschema فقط. أولوية منخفضة. |
+| — | **`projects-contribution-amount-no-positive-constraint`** [2026-09-23] — نفس الجلسة (الصف 16): `projects/schemas.py:69` `amount_mrusdt` (Optional) بلا `gt=0`؛ المساهمة النقدية تمرره مباشرة لـ`finance.transfer` (`projects/service.py:185`). مغطى مركزيًا منذ `58b30af`؛ المتبقي قيد schema. أولوية منخفضة. |
+| — | **`transport-booking-seats-count-no-min`** [2026-09-23] — نفس الجلسة (الصف 36): `transport/schemas.py:131` `seats_count` بلا `ge=1` → `fare = base_fare × seats_count` سالب/صفر → `hold_funds` (`transport/service.py:478`). مغطى مركزيًا منذ `58b30af`؛ المتبقي قيد schema. أولوية منخفضة. |
+| — | **`merchant-set-prices-no-nonnegative-constraint`** [2026-09-23] — نفس الجلسة (فئة B): أسعار يضعها تاجر/منشئ/صاحب عمل/مسؤول بلا `ge=0`: commerce `price_mrusdt`/`wholesale_price_mrusdt` (`schemas.py:44,50`)، tourism_sports `base_price_mrusdt`/`base_ticket_price_mrusdt` (`schemas.py:44,97`)، transport `base_fare_mrusdt` (`schemas.py:101`)، social أسعار خطط المجموعات (`schemas.py:184-185`)، saas `price_monthly` (`schemas.py:39`)، employment `base_salary` (`schemas.py:70`). قبل `58b30af`: سعر سالب → 500 للمشتري؛ بعده → 422. المتبقي قيود schema. أولوية منخفضة. |
+| — | **`digital-twin-negative-duration-free-interaction`** [2026-09-23] — نفس الجلسة (الصف 6): `digital_twin/schemas.py:49` `duration_minutes` بلا قيد → `fee × duration` سالب → حارس `if fee > 0` يتخطى الدفع → تفاعل مجاني يُسجَّل بمدة سالبة (ليس عكس أموال؛ الحارس المركزي لا يلتقطه لأن `transfer` لا يُستدعى). أولوية منخفضة. |
+| — | **`no-global-integrityerror-handler`** [2026-09-23] — نفس الجلسة: `app/main.py` فيه handlers لـ`SovereignError`/`IdempotencyError`/`RateLimitError` فقط؛ أي انتهاك قيد DB يخرج كـ500 عام بلا traceback في اللوج (مُثبت حيًا في B3 قبل الإصلاح). أولوية منخفضة–متوسطة. |
+| — | **`review-claim-zero-amount-falls-back-to-claimed`** [2026-09-23] — نفس الجلسة: `insurance/service.py:524` `final_amount = approved_amount or claimed` — `Decimal("0")` falsy → الموافقة بـ0 تدفع كامل المبلغ المطالب به (مُثبت حيًا: B8 قبل الإصلاح، N8 بعده). عبر HTTP مغلق منذ `58b30af` (`gt=0` → 422)؛ مستدعٍ داخلي يمرر 0 مباشرة لا يزال يدفع كاملًا. الإصلاح: `approved_amount if approved_amount is not None else claimed`. أولوية منخفضة. |
+| — | **`social-group-subscription-duration-months-no-min`** [2026-09-23] — نفس الجلسة (الصف 25): `social/schemas.py:196` `duration_months` من الطلب بلا حد أدنى (`social/router.py:389`) → `price_monthly × duration_months` سالب/صفر (`social/service.py:671`). مغطى مركزيًا منذ `58b30af`؛ المتبقي قيد schema (`ge=1`). أولوية منخفضة. |
+| — | **`transport-delivery-fee-no-nonnegative-constraint`** [2026-09-23] — نفس الجلسة (الصف 38): `DeliveryTaskCreate.delivery_fee_mrusdt` (`transport/schemas.py:157`) بلا `ge=0` — المُرسِل يضع الرسوم (`transport/service.py:701`) ثم هو نفسه الدافع (`hold_funds`، `service.py:814`). مغطى مركزيًا منذ `58b30af`؛ المتبقي قيد schema. أولوية منخفضة. |
+| — | **`tenders-min-increment-no-nonnegative-constraint`** [2026-09-23] — نفس الجلسة (الصف 32): `tenders_auctions/schemas.py:75` `min_increment_mrusdt` بلا `ge=0` → منشئ المزاد يضع زيادة سالبة → `min_required = current_highest + min_increment` (`service.py:390`) قد يصبح سالبًا → مزايدة سالبة تصل `hold_funds`. مغطى مركزيًا منذ `58b30af`؛ المتبقي قيد schema. أولوية منخفضة. |
+
+**✅ إغلاق مؤرَّخ [2026-09-23] — `insurance-review-claim-negative-approved-amount-reverses-transfer`: مُغلَق (commit `58b30af`)، مع تصحيح تصنيف الخطورة.** جلسة `insurance-negative-approved-amount-verification` (تقرير: `.claude/reports/insurance-negative-approved-amount-verification-session-log.md`). **التصحيح:** الملاحظة الأصلية ("مُصدِر خبيث يسرق أموال المُطالِبين بمبلغ سالب") **بُنيت على قراءة ناقصة** — فاتها قيود DB: `transactions.check_transaction_amount_positive` (`CHECK (amount > 0)`، migration `71820e4fe1f3...:2034`) و`wallets.check_wallet_balances_non_negative` / `check_wallet_held_balances_non_negative`. كل دوال `FinanceService` الأربع تُحدِّث المحافظ وتُدرج صف `Transaction` داخل نفس `begin_nested()` بلا commit داخلي → أي مبلغ `<= 0` يُلغى بالكامل. **BEFORE (حي، تينانت throwaway 144، كود غير مُصلَح):** B1–B7 — `review_claim(-50)` (بمُطالِب رصيده 0 ثم 100)، HTTP (`-50`)، و`transfer`/`hold_funds`/`release_held_funds`/`settle_held_funds(-10)` مباشرة — **كلها `IntegrityError` بصافي تغيير صفر** (لا حركة أموال)، لكن العميل يتلقى **HTTP 500**؛ B6/B7 أثبتا أن قيد `transactions` هو **الحاجز الوحيد** لـrelease/settle (قيود المحفظة مرّت)؛ B8 — `approved_amount=0` **دفع كامل المطالبة (20)**. **الخطورة الفعلية:** hardening + تصحيح كود خطأ (منخفضة–متوسطة)، **ليست سرقة**. **الإصلاح (2 ملف، +15/−5):** حارس `amount <= 0 → ValidationError (422)` في أول الدوال الأربع قبل أي SQL (`finance/service.py`)؛ `approved_amount: Query(None, gt=0)` (`insurance/router.py:225`). **AFTER (تينانت 145):** 15/15 — الدوال الأربع ترفض `-10` و`0` بـ**صفر عبارات SQL** (مستمع `before_cursor_execute`)؛ HTTP `-50`/`0` → 422؛ التدفقات الموجبة (موافقة 50 عبر HTTP، hold→release→hold→settle) سليمة؛ الموافقة بـ0 عبر الخدمة مباشرة لا تزال تدفع كاملًا (backlog `review-claim-zero-amount-falls-back-to-claimed`). **اختبار دائم:** `tests/test_finance_non_positive_amount_guard.py` — 10/10 على الإصلاح، 10/10 FAIL على HEAD (mutation check). **Regression:** 26/26 (insurance status guard، FINBIND، tenders hold/release/settle، 4 مجموعات transport). **تنظيف:** التينانتان 144 (17 صفًا) و145 (29 صفًا) حُذفا بالكامل، صفر متبقٍ. **مواقع الاستدعاء:** 40 موقعًا لـ`transfer`/`hold`/`release`/`settle` صُنِّفت (7 A، 10 B، 23 S) — الحارس المركزي يغطيها كلها؛ قيود الـschema لمواقع A/B → 10 بنود backlog أعلاه (توثيق فقط، بقرار المستخدم).
 
 ---
 
```

## ق.4 `git diff --cached --name-only` و`--stat` (بعد إعادة staging هذا التقرير)

هذا القسم نفسه يُضاف للتقرير ويُجهَّز معه (ملف كان نظيفًا مقابل HEAD قبل هذا القسم → staging للملف كاملًا = هذا القسم فقط). الأرقام حُسبت مسبقًا ثم قورنت آليًا بمخرجات الأمر الفعلية.

```
.claude/reports/insurance-negative-approved-amount-verification-session-log.md
PROGRESS_LOG.md
```

```
 ...ive-approved-amount-verification-session-log.md | 75 ++++++++++++++++++++++
 PROGRESS_LOG.md                                    | 12 ++++
 2 files changed, 87 insertions(+)
```

**رسالة commit الـdocs المقترحة (للمراجعة):**
```
docs: close insurance negative approved_amount finding (hardening, not theft — DB CHECKs already blocked it) + 10 backlog items

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

## ق.5 الحالة

- commit الإصلاح: ✅ `58b30af`. لا push.
- `PROGRESS_LOG.md`: مكتوب في شجرة العمل، و**هانك الجلسة فقط** مُجهَّز. **لا commit `docs:` بعد — بانتظار موافقتك.**
