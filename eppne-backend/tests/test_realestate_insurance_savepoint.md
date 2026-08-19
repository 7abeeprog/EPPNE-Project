# `test_realestate_insurance_savepoint.py`

## المرجع الأصلي
- `.claude/reports/realestate-insurance-savepoint-fix-session-log.md` (Backlog #11b، جلسة `invoicing-savepoint-conflict`).
- يغطي 8 دوال عبر 4 دومينات: `tourism_sports` (×3)، `realestate` (×2)، `insurance` (×2)، `zamakana` (×1).

## السبب الجذري (كان) — ملخص
`InvoicingRepository.create_invoice()` بتعمل `commit()` مباشر — بيقفل الـ
SAVEPOINT بتاع `begin_nested()` في أي دالة بتستدعيها من جواه.

## الإصلاح المُطبَّق (نفس النمط في الثمانية دوال)
نقل استدعاء `create_invoice()` من جوه `begin_nested()` إلى **مباشرة بعد
`await self.db.commit()`**، ملفوف بـ`try/except Exception`. `finance.transfer()`
(حيث موجودة) تفضل جوه `begin_nested()` — مثبَّت أنها آمنة.

## إيه اللي بيتحقق منه هذا الملف

**⚠️ تعديل نطاق عن التقرير الأصلي، بموافقة مستخدم صريحة [2026-08-18]:**
التقرير الأصلي وثَّق مستوى تحقق حي كامل لـ4 دوال (`purchase_event_ticket`,
`rent_unit`, `insurance.subscribe` جزئيًا, `pledge_time`). أثناء كتابة هذا
الملف اكتُشف بج مسبق جديد (`invoicing-generate-invoice-number-count-based-collision`
— راجع `PROGRESS_LOG.md`) بيمنع **أي** استدعاء حقيقي لـ`create_invoice()`
لـ`tenant_id=1` حاليًا. **النتيجة: كل الثمانية دوال بمراجعة بنيوية فقط
(source-order check) في هذا الملف — صفر تحقق حي مباشر لأي منها.** صفر لمس
على `invoicing/service.py`.

### 8 اختبارات مراجعة بنيوية (`test_*_invoice_ordering`)
كل واحد بيستخدم `_assert_invoice_after_commit_and_wrapped()` — حارس مبني
على `inspect.getsource()` بيتأكد إن `create_invoice()`:
1. تظهر في الكود **بعد** `await self.db.commit()` (مش قبله/جواه) — الحارس
   الأساسي ضد رجوع باج savepoint leak.
2. **مُغلَّفة بـ`try/except`** — نفس نمط الإصلاح المطبَّق.

| الدالة | لماذا مراجعة بنيوية بس |
|---|---|
| `tourism_sports.purchase_event_ticket` | `invoicing-generate-invoice-number-count-based-collision` |
| `tourism_sports.book_program` | `finance-transfer-returns-transaction-object-not-tx-hash-string` |
| `tourism_sports.place_transfer_bid` | `tourism-place-transfer-bid-player-id-user-id-conflict` + Backlog #12 |
| `realestate.rent_unit` | `invoicing-generate-invoice-number-count-based-collision` |
| `realestate.buy_fractional_ownership` | `finance-transfer-returns-transaction-object-not-tx-hash-string` |
| `insurance.subscribe` | `invoicing-generate-invoice-number-count-based-collision` |
| `insurance.review_claim` | `finance-transfer-returns-transaction-object-not-tx-hash-string` |
| `zamakana.pledge_time` | `invoicing-generate-invoice-number-count-based-collision` |

### اختبار تاسع إضافي (`xfail` موثَّق، بونص خارج نطاق الثمانية دوال)
`test_realestate_rent_unit_real_invoice_failure_leaves_session_broken` —
تحقق حي فعلي (بيانات throwaway حقيقية، DB حقيقي) بيثبت اكتشاف جانبي حرج:
لما `create_invoice()` تفشل بخطأ DB **حقيقي** (مش `RuntimeError` مصطنع بره
الـDB)، الـ`try/except` المضاف في #11b بيمسك الاستثناء لكن **من غير
`db.rollback()`** — السيشن بتفضل `PendingRollbackError` لأي كود بعده جوه
نفس الدالة (`_store_idempotency`). `xfail(strict=True)` — لو حد يصلح الباج
لاحقًا (يضيف `db.rollback()`)، التست هيبقى XPASS ويفشل تلقائيًا، فيبقى
تذكير واضح إن مستوى التحقق محتاج يترفّع.

## استثناءات موثَّقة
- **صفر `skip` في هذا الملف.**
- **8 من 9 اختبارات مراجعة بنيوية فقط** (بدل تحقق حي) — كل واحد موثَّق
  بسببه المحدد في الدوكسترنج (docstring) الخاصة بيه، وفي جدول أعلى.
- **اختبار واحد `xfail(strict=True)`** — موثَّق بالكامل، بيثبت باج حقيقي
  مش regression.

## بجات مسبقة اكتُشفت أثناء كتابة هذا الملف (موثَّقة في `PROGRESS_LOG.md`)
1. **`invoicing-generate-invoice-number-count-based-collision`** — `_generate_invoice_number()`
   بتحسب `count(invoices)+1`؛ فجوة في تسلسل `tenant_id=1` (فاتورة اتحذفت
   قديمًا) بتخلي أي محاولة إنشاء فاتورة حقيقية تتصادم مع `INV-1-000015`
   الموجودة بالفعل. مؤكَّد حيًا 4 مرات مستقلة.
2. **`invoicing-missing-rollback-on-exception-11b`** — الـ`try/except`
   المضاف في #11b حوالين `create_invoice()` من غير `db.rollback()`. مؤكَّد
   حيًا بالاختبار التاسع (`xfail`). اكتشاف إضافي: `db.rollback()` وحدها
   مش كافية للتعافي بعد فشل flush حقيقي — استدعاء ORM لاحق بيكسر بـ
   `MissingGreenlet` (خطأ أعمق)؛ التنظيف في الاختبار التاسع بيستخدم
   `AsyncSessionLocal()` جديدة تمامًا بدل محاولة إصلاح القديمة.

هذان البجان **منفصلان تمامًا عن #11b نفسها** — صفر لمس على
`invoicing/service.py` في هذه الجلسة، موثَّقان كبندي Backlog مستقلين
بأولوية عالية جدًا (دومين مالي).

## بيانات throwaway
- `tenant_id=1` ("Local Test Tenant").
- كل اختبار يستخدم بيانات جديدة (`uuid4` suffix) — صفر تصادم بين تشغيلات.
- تنظيف كامل في `finally` بعد كل اختبار حي؛ الاختبار التاسع (`xfail`)
  يستخدم session منفصلة تمامًا للتنظيف (راجع السبب أعلاه) — كلاهما
  تأكَّد بـ`SELECT` مباشر بعد التشغيل: صفر صفوف throwaway متبقية.

## طريقة التشغيل
```
./venv/Scripts/python.exe -m pytest tests/test_realestate_insurance_savepoint.py -v
```
يحتاج DB حقيقي شغّال (`docker` container `eppne_db`, بورت 5435).

**آخر تشغيل مُوثَّق:** 8 passed, 1 xfailed.
