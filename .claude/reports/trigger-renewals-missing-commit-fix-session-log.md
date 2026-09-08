# إصلاح ضيق: `backlog-trigger-renewals-admin-endpoint-missing-commit-silent-write`

**النطاق:** `SaaSControlService.trigger_renewals` بس
(`app/domains/saas/service.py:618-620` الأصلية). **صفر لمس على
`router.py` أو `process_auto_renewals` نفسها.**

**السياق الكامل (تحقيق الجلسة السابقة، صفر تعديل كود):**
`.claude/reports/trigger-renewals-missing-commit-investigation-session-log.md`.

---

## 1) الباج (ملخّص من التحقيق السابق)

`POST /admin/trigger-renewals` (`router.py:265-275`) بينادي
`service.trigger_renewals(tenant_id)` اللي كانت بترجّع نتيجة
`process_auto_renewals(target)` مباشرة بلا أي `commit()`. فرع `except
InsufficientBalanceError` (PAST_DUE) جوّه `process_auto_renewals`
بيعمل `repo.update_subscription(...)` عبر `flush()` بس (بلا `commit()`
مستقل) — فكانت الكتابة معتمدة كليًا على commit خارجي غائب في مسار
الراوتر. **مؤكَّد حيًا في الجلسة السابقة:** رد الـAPI كان بيرجّع
`PAST_DUE` بينما الـDB تفضل `ACTIVE` بعد إغلاق جلسة الطلب.

فرعا SUCCESS وFAILED كانا آمنين مسبقًا (SUCCESS عندها `self.db.commit()`
خاص بيها سطر 314، FAILED صفر كتابة DB) — راجع §4 من تقرير التحقيق
للتفاصيل الكاملة.

---

## 2) التعديل الفعلي

**الملف:** `app/domains/saas/service.py`

```diff
     async def trigger_renewals(self, tenant_id: Optional[int] = None):
         """تشغيل مهمة تجديد الاشتراكات يدوياً (للمشرفين)."""
         target = tenant_id if tenant_id is not None else self.tenant_id
-        return await self.process_auto_renewals(target)
+        results = await self.process_auto_renewals(target)
+        await self.db.commit()
+        return results
```

نفس نمط `saas_tasks.py:74-75` (الـcelery task) بالحرف: `commit()`
مباشرة بعد استدعاء `process_auto_renewals`، قبل أي معالجة/إرجاع
للنتيجة.

**تأكيد نطاق الـdiff** (`git diff` على `service.py`، معزول لهذه الدالة
فقط — باقي التعديلات الظاهرة في الملف كانت موجودة *قبل* بداية هذه
الجلسة، غير مرتبطة):

```diff
     async def trigger_renewals(self, tenant_id: Optional[int] = None):
         """تشغيل مهمة تجديد الاشتراكات يدوياً (للمشرفين)."""
         target = tenant_id if tenant_id is not None else self.tenant_id
-        return await self.process_auto_renewals(target)
+        results = await self.process_auto_renewals(target)
+        await self.db.commit()
```

`router.py`: **صفر diff** (تأكَّد بـ`git diff -- router.py` فارغ تمامًا).

---

## 3) الاختبار الحي — سيناريو PAST_DUE (نفس الاختبار اللي فشل قبل الإصلاح)

**الملف:** `tests/test_trigger_renewals_endpoint_missing_commit.py`
(نفس ملف الجلسة السابقة، **الاسم بقي كما هو** — الآن regression test
لإصلاح البند نفسه بدل اكتشافه؛ الدالة اتسمّت `..._persists_past_due_after_fix`
بدل `..._loses_past_due...`).

نفس المنهجية بالحرف: استدعاء `trigger_renewals` فعليًا بجلسة
`AsyncSessionLocal()` تُفتح وتُغلق بنمط `get_db()` الحقيقي (بلا commit
إضافي من الاختبار نفسه — الـcommit الوحيد جوّه `trigger_renewals` نفسها
بعد الإصلاح)، اشتراك باهظ واحد (999999.00 MR_USDT) → `InsufficientBalanceError`.

**النتيجة بعد الإصلاح:**

| | قبل الإصلاح (الجلسة السابقة) | بعد الإصلاح (الآن) |
|---|---|---|
| رد الـAPI | `{"status": "PAST_DUE"}` | `{"status": "PAST_DUE"}` (بلا تغيير) |
| `TenantSubscription.status` في الـDB (جلسة مستقلة بعد إغلاق جلسة الطلب) | `"ACTIVE"` ❌ (ضاع) | `"PAST_DUE"` ✅ (اتحفظ فعليًا) |
| `grace_period_end_date` | `None` ❌ | مضروب (+3 أيام) ✅ |

```
tests/test_trigger_renewals_endpoint_missing_commit.py::test_trigger_renewals_endpoint_persists_past_due_after_fix PASSED
```

---

## 4) الاختبار الحي الإضافي — سيناريو SUCCESS عبر نفس المسار (فحص double-commit)

نفس المسار (`trigger_renewals`) لكن اشتراك رخيص (1.00 MR_USDT) —
يفترض `SUCCESS`. الهدف: التأكد إن `await self.db.commit()` الإضافي
(المُضاف الآن في `trigger_renewals`) **بعد** commit سابق فعلاً (فرع
SUCCESS جوّه `process_auto_renewals`، `service.py:314`، بيعمل
`self.db.commit()` خاص بيه لكل اشتراك ناجح) لا يسبب أي استثناء
"double commit" أو تلف بيانات.

**النتيجة:**

```
tests/test_trigger_renewals_endpoint_missing_commit.py::test_trigger_renewals_endpoint_success_path_no_double_commit_error PASSED
```

- رد الـAPI: `{"status": "SUCCESS", "tx_hash": "..."}` ✅
- `TenantSubscription.status == "ACTIVE"`, `next_billing_date` محدَّث
  (+30 يوم) ✅
- فاتورة `Invoice` حقيقية `status="PENDING"` موجودة على القرص ✅
- **صفر استثناء** — `commit()` على session بلا ترانزاكشن معلَّقة (بعد
  ما اتقفلت فعليًا من الـcommit الداخلي) هو no-op آمن تمامًا في
  SQLAlchemy async، مش خطأ.

---

## 5) Regression — اختبارات موجودة تلمس `process_auto_renewals`/`SaaSControlService`

`grep -rln "trigger_renewals\|trigger-renewals"` عبر `tests/` أظهر ملف
واحد بس يلمس `trigger_renewals` تحديدًا (ملف هذه الجلسة نفسه). أقرب
اختبار regression ذو صلة مباشرة (بينادي `process_auto_renewals` اللي
`trigger_renewals` بتستدعيها، ونفس `SaaSControlService`):

```
tests/test_financeservice_tenant_binding_fix.py::test_process_auto_renewals_admin_sentinel_full_loop_success_and_past_due PASSED
tests/test_financeservice_tenant_binding_fix.py::test_pay_invoice_same_tenant_still_works_after_removing_self_finance PASSED
```

هذا الاختبار بينادي `process_auto_renewals` **مباشرة** (مش عبر
`trigger_renewals`) مع `db.commit()` يدوي خاص بالاختبار نفسه (يحاكي
`saas_tasks.py`) — مسار منفصل تمامًا عن التعديل، ومرّ بلا أي تأثر (كما
متوقَّع، لأن `process_auto_renewals` نفسها لم تُلمَس).

**الإجمالي: 4/4 اختبارات مرّت.**

```
tests/test_trigger_renewals_endpoint_missing_commit.py::test_trigger_renewals_endpoint_persists_past_due_after_fix PASSED
tests/test_trigger_renewals_endpoint_missing_commit.py::test_trigger_renewals_endpoint_success_path_no_double_commit_error PASSED
tests/test_financeservice_tenant_binding_fix.py::test_process_auto_renewals_admin_sentinel_full_loop_success_and_past_due PASSED
tests/test_financeservice_tenant_binding_fix.py::test_pay_invoice_same_tenant_still_works_after_removing_self_finance PASSED
4 passed, 1 warning in 78.37s
```

---

## 6) تحديث `PROGRESS_LOG.md`

أُضيف قسم جديد في آخر الملف (السجل تراكمي، القديم لم يُعدَّل):
`## [2026-09-08] تحديث backlog-trigger-renewals-admin-endpoint-missing-commit-silent-write — ✅ اتحل`
— يلخّص الجلستين (تحقيق ثم إصلاح) ويشير لهذا التقرير والتقرير السابق.

---

## 7) الحالة النهائية

**`backlog-trigger-renewals-admin-endpoint-missing-commit-silent-write`
→ ✅ اتحل بالكامل، مؤكَّد حيًا (قبل وبعد الإصلاح).**

النطاق التزم بالحرف بالتعليمة: تعديل واحد فقط داخل `trigger_renewals`
(3 أسطر)، صفر لمس على `router.py` أو `process_auto_renewals`. الفروع
الأخرى (SUCCESS/FAILED) بقيت آمنة كما كانت، وتأكَّد عدم وجود أي أثر
جانبي (double-commit) من التعديل.
