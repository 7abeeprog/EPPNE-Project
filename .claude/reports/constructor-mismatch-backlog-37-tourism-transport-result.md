# #37 — نتائج `tourism_sports.book_program` و`transport.pay_delivery` (آخر موضعين)

**تاريخ:** 2026-08-29
**الحالة:** الأربعة مواضع خلصوا كلهم. #37 مُصلَح بالكامل في الكود، بمستويات تحقق مختلفة موثَّقة بدقة لكل موضع.

---

## `tourism_sports.book_program` — ✅ مُصلَح ومُتحقَّق منه حيًا **end-to-end كامل** (الأفضل بين الأربعة)

**الإصلاح:** `tourism_sports/service.py:179` — `payment_tx_hash=tx_hash` → `payment_tx_hash=cast(str, tx_hash.tx_hash)`

**خطوة تمهيدية مطلوبة (موافَق عليها):** إضافة كود `"tourism"` لـ`saas_service_catalog` (`id=78`) — توسيع فعلي لـ#28، لأن `book_program` بينادي `_check_saas_limits(tenant_id, "tourism")` بكود مختلف عن الافتراضي `"tourism_sports"`.

**التحقق الحي — عبر الـservice method العامة الحقيقية بالكامل (مش repository مباشرة، مش monkeypatch):**
بيانات throwaway حقيقية (مستخدم + محفظة ممولة + برنامج سياحي + **سلسلة اشتراك SaaS حقيقية كاملة**:
service plan + tenant subscription `ACTIVE` + tenant service access — بيانات DB حقيقية شرعية، مش
تحايل)، ثم استدعاء `TourismSportsService(db).book_program(user_id, tenant_id=1, program_id, idempotency_key)`
الحقيقية بلا أي تعديل/تجاوز:

```
program_participants: id=1, user_id=990, program_id=9, payment_tx_hash='TX-0FC913F7A97E'
transactions:          id=85, sender_id=990, receiver_id=87, tx_hash='TX-0FC913F7A97E'
pg_typeof(payment_tx_hash) = character varying
```

القيمتان متطابقتان حرفيًا — الفلوس اتحوّلت فعليًا، والـtx_hash الصحيح اتخزَّن كنص، مش كائن.

### ⚠️ اكتشاف جانبي جديد أثناء نفس التحقق — موثَّق في PROGRESS_LOG.md، صفر إصلاح

بعد نجاح خطوة الدفع/الحجز (خارج نطاق #37 تمامًا — الكراش القديم كان **قبل** هذه النقطة، دلوقتي
اتخطَّته بنجاح)، محاولة `book_program` إنشاء فاتورة عبر `InvoicingService.create_invoice()` (بعد
`commit()` الخارجي، نفس نمط #11b) اصطدمت بباج منفصل تمامًا: `_generate_invoice_number()`
(`invoicing/service.py:115-119`) بتحسب رقم الفاتورة التالي بـ`COUNT(invoices) + 1` بدل sequence
حقيقي — أي تينانت له تاريخ حذف فواتير throwaway (كل تينانت اختباري تقريبًا في المشروع) معرَّض
لتصادم رقم فاتورة موجود بالفعل. **مؤكَّد حيًا:** `INV-1-000015` كان موجود مسبقًا، الاصطدام
حصل فورًا وبشكل حتمي (مش صدفة). **بند Backlog جديد مُسجَّل:**
`invoicing-generate-invoice-number-count-based-collision` — راجع `PROGRESS_LOG.md` (سطر جديد
بعد `insurance-review-claim-payout-from-reviewer-personal-wallet`). **صفر إصلاح — خارج نطاق #37.**

**تنظيف كامل** (`program_participants`, `tourism_programs`, `saas_tenant_service_access`,
`saas_tenant_subscriptions`, `saas_service_plans`, `audit_logs`, `transactions`, `wallets`,
`users`) — تأكيد `SELECT COUNT`، صفر بيانات متبقية. ملاحظة: 3 محاولات throwaway إجمالًا أثناء
تطوير سكريبت التحقق (2 فشلا بسبب الحاجب الأصلي قبل إضافة سلسلة الاشتراك، واحدة نجحت بالكامل)،
كلها اتنضّفت في نفس عملية التنظيف النهائية.

---

## `transport.pay_delivery` — ✅ الكود مُصلَح، فحص سورس فقط (بلا تحقق حي — نفس معاملة #18)

**الإصلاح:** `transport/service.py:531` — `payment_tx_hash=tx_hash` → `payment_tx_hash=tx_hash.tx_hash`
(داخل `update(DeliveryTask).where(...).values(...)`)

**السبب:** جداول `transport` (بما فيها `delivery_tasks`) غير موجودة إطلاقًا في قاعدة البيانات
الحالية (#39 — `transport-domain-tables-never-migrated`) — مستحيل بناء سيناريو تحقق حي حقيقي.

**التحقق البديل المُنفَّذ (نفس منهجية #18 بالحرف):**
- `DeliveryTask.payment_tx_hash` مؤكَّد `Column(String(100), nullable=True)` (`transport/models.py:216`).
- `finance.transfer()` مؤكَّد ترجع كائن `Transaction` (نفس التأكيد المستخدَم للمواضع التلاتة التانية،
  `finance/service.py:147`).
- فحص السورس المباشر بعد التعديل يؤكد: `tx_hash.tx_hash` (النص الصحيح) هو اللي بيتخزَّن دلوقتي،
  مش الكائن الكامل.

**ملاحظة إضافية أثناء المراجعة (صفر لمس، خارج نطاق #37):** `transport.book_trip`
(`service.py:333`) عندها نفس نمط `tx_hash = await finance.transfer(...)` **لكن المتغيّر مش
مُستخدَم في أي كتابة DB لاحقة أصلًا** (`create_booking()` مفيهاش `tx_hash`/`fare_tx_hash`) —
تأكيد إضافي إنها من فئة "الـ9 مواضع تسمية مربكة بلا كراش" الموصوفة في البند الأصلي، مش موضع خامس
مؤكَّد. **صفر تعديل هنا** (خارج الأربعة المتفق عليها صراحة).

**هيستاهل تحقق حي كامل لاحقًا لو/لما جداول `transport` اتعملها migration** — نفس التحفظ الموثَّق
سلفًا لـ#18/#39.

---

## ملخص نهائي — الأربعة مواضع

| الموضع | الإصلاح | مستوى التحقق |
|---|---|---|
| `realestate.buy_fractional_ownership` | ✅ | Repository-level (بمعزل عن #40) |
| `insurance.review_claim` | ✅ | Repository-level (بمعزل عن #41) |
| `tourism_sports.book_program` | ✅ | **End-to-end كامل عبر الـservice method الحقيقية** |
| `transport.pay_delivery` | ✅ | فحص سورس فقط (جداول غير موجودة، #39) |

**#37 مُصلَح بالكامل كودًا في الأربعة مواضع الأصلية. صفر لمس على الـ~9 مواضع "تسمية مربكة بلا
كراش" الأخرى (خارج النطاق المتفق عليه صراحة).**
