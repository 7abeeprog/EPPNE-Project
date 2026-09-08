# إصلاح ضيق: FinanceService tenant binding في SaaSControlService

**النطاق:** `app/domains/saas/service.py` بس. صفر لمس على `FinanceService`
نفسها (`finance/service.py`) ولا أي دومين تاني — الخيار (ب) من التقييم في
`.claude/reports/financeservice-tenant-binding-investigation-session-log.md`
§4.

---

## 1) جدول: كل دالة كانت بتستخدم `self.finance`

فحصت كل دالة في `SaaSControlService` (`grep -n "self\.finance"` قبل
التعديل — سطرين استخدام فقط بجانب `__init__`):

| الدالة | بتستخدم تينانت الـinstance (`self.tenant_id`) ولا تينانت مختلف؟ | التينانت الصح المُستخدَم في الإصلاح |
|---|---|---|
| `process_auto_renewals` (سطر 291 الأصلي) | **تينانت مختلف** — بتلوب على اشتراكات عبر تينانتات متعددة (`get_subscriptions_for_renewal(tenant_id)` بلا فلتر لو `None`)، كل اشتراك له `sub.tenant_id` الحقيقي بتاعه، منفصل تمامًا عن `self.tenant_id` اللي اتبنت بيه الـ`SaaSControlService` نفسها (زي السنتينل `0` في `saas_tasks.py:69`/`router.py:273`) | `FinanceService(self.db, sub_tenant_id)` — تُبنى **من جديد داخل كل تكرار من الحلقة** |
| `pay_invoice` (سطر 515 الأصلي) | **نفس تينانت الـinstance** — `invoice = await self.get_invoice(invoice_id)` بتجيب فاتورة مفلترة أصلًا بـ`self.tenant_id` (`repo.get_invoice_by_id(invoice_id, self.tenant_id)`)، فمستحيل تكون فاتورة تينانت تاني | `FinanceService(self.db, self.tenant_id)` — تُبنى محليًا جوّه الدالة (مش من `self.finance` الثابتة) |

مفيش دالة تالتة بتستخدم `self.finance` — الاثنين دول كل الاستخدامات
الموجودة فعليًا في الملف.

---

## 2) التعديل الفعلي

**(أ)** حذف `self.finance = FinanceService(db, tenant_id)` من `__init__`
(كان سطر 63):

```python
def __init__(self, db: AsyncSession, tenant_id: int):
    self.db = db
    self.tenant_id = tenant_id
    self.repo = SaaSRepository(db)
```

**(ب) `process_auto_renewals`** — بناء `FinanceService` جديدة لكل اشتراك
على حدة، بتينانت الاشتراك الحقيقي (`sub_tenant_id`)، مش تينانت الـinstance:

```python
payer_id = await self._get_tenant_admin_id(sub_tenant_id)
system_account = await get_or_create_system_account(self.db, sub_tenant_id)
finance = FinanceService(self.db, sub_tenant_id)   # 👈 جديد، محلي لكل تكرار
async with self.db.begin_nested():
    tx = await finance.transfer(...)               # بدل self.finance.transfer
```

**(ج) `pay_invoice`** — بناء `FinanceService` محلية بنفس `self.tenant_id`
(نفس القيمة اللي كانت بتُستخدَم عبر `self.finance` الثابتة، لكن الآن
مبنية عند وقت الاستدعاء الفعلي مش عند إنشاء الـinstance):

```python
payer_id = await self._get_tenant_admin_id(self.tenant_id)
system_account = await get_or_create_system_account(self.db, self.tenant_id)
finance = FinanceService(self.db, self.tenant_id)   # 👈 جديد، محلي
async with self.db.begin_nested():
    try:
        tx = await finance.transfer(...)             # بدل self.finance.transfer
```

**صفر تغيير في أي منطق تاني** — نفس ترتيب الاستدعاءات، نفس الـ
`begin_nested()`/`commit()` الموجودين أصلًا، نفس الـidempotency keys.

---

## 3) الاختبار الحي — نفس السيناريو اللي فشل قبل الإصلاح، بالظبط

**السيناريو (مطابق لـ`past-due-grace-period-notifications-implementation-
session-log.md` §9-ج):** اشتراكان حقيقيان تحت تينانت 1 (`Local Test
Tenant`)، مستحقّان فعليًا للتجديد (`next_billing_date` في الماضي)،
عبر `SaaSControlService(db, 0)` — **نفس نمط السنتينل الإداري الحقيقي**
المُستخدَم في `saas_tasks.py:69`/`router.py:273`:

- اشتراك رخيص (1.00 MR_USDT) — يفترض **SUCCESS**.
- اشتراك باهظ عمدًا (999999.00 MR_USDT) — يفترض
  `InsufficientBalanceError` → **PAST_DUE**.

**قبل الإصلاح (موثَّق سابقًا):** الاثنان فشلا بنفس
`NotFoundError("المستلم غير موجود")` — صفر SUCCESS، صفر PAST_DUE.

**بعد الإصلاح — النتيجة الفعلية (regression test حقيقي، DB حي
`eppne_db`، صفر mock):**

```
tests/test_financeservice_tenant_binding_fix.py::test_process_auto_renewals_admin_sentinel_full_loop_success_and_past_due PASSED
tests/test_financeservice_tenant_binding_fix.py::test_pay_invoice_same_tenant_still_works_after_removing_self_finance PASSED
```

**تحقق كامل عبر جلسة DB مستقلة (`AsyncSessionLocal()` جديدة، بلا اعتماد
على جلسة الاختبار نفسها):**

| | قبل الإصلاح | بعد الإصلاح |
|---|---|---|
| الاشتراك الرخيص | `NotFoundError` | ✅ `status: SUCCESS`، `tx_hash` حقيقي، `TenantSubscription.status="ACTIVE"` بـ`next_billing_date` محدَّث (+30 يوم)، **فاتورة `Invoice` حقيقية `status="PENDING"` موجودة على القرص** |
| الاشتراك الباهظ | `NotFoundError` | ✅ `status: PAST_DUE`، `TenantSubscription.status="PAST_DUE"` فعليًا على القرص، `grace_period_end_date` مضروب (+3 أيام)، **صفر فاتورة** (صح — التجديد فشل) |

**ملاحظة تقنية مهمة (لم تُلمَس، خارج نطاق اليوم):** فرع
`except InsufficientBalanceError` في `process_auto_renewals` بيعمل
`repo.update_subscription(...)` **بلا `commit()` خاص بيه** (`flush()`
بس عبر الـrepo) — باج مستقل موثَّق مسبقًا في `PROGRESS_LOG.md` ("فرع
except InsufficientBalanceError... بلا أي commit() بعده"). الاختبار
هنا كرر بالضبط نفس بنية `process_auto_renewals_task`
(`saas_tasks.py:74-75`) بإضافة `await db.commit()` **بعد** استدعاء
`process_auto_renewals()` نفسها (نفس اللي التاسك الحقيقي بيعمله) —
مش تعديل على كود `service.py`. بمعنى: التحويل لـ`PAST_DUE` بيتحفظ
فعليًا في الإنتاج الحقيقي (عبر الـcelery task) بفضل الـ`commit()`
الخارجي ده، **لكن** استدعاء `POST /admin/trigger-renewals` (الـendpoint
اليدوي، `router.py:265-275`) **مفيهوش** `commit()` مماثل بعد
`service.trigger_renewals(...)` — يعني لسه معرَّض لنفس فقدان الكتابة
الصامت لو استُخدم الـendpoint اليدوي تحديدًا (لا الـcelery task). هذا
باج منفصل تمامًا (missing-commit)، غير ذي علاقة بربط التينانت، **لم
يُفتح له بند backlog جديد اليوم** — موثَّق هنا فقط كملاحظة سياق لتفسير
ليه الاختبار احتاج `db.commit()` إضافي.

**أثر جانبي حقيقي على البيانات (متوقَّع ومقصود، تينانت الاختبار
المخصَّص):** محفظة `admin_id=1` (تينانت 1، `wallet.id=39`) انخفضت من
`MR_USDT=865.0` إلى `863.0` — معاملتان حقيقيتان بـ1.00 MR_USDT لكل
منهما (اختبار `process_auto_renewals` + اختبار `pay_invoice` المنفصل
تحت). صفر بيانات throwaway متبقية غير ذلك — كل `service`/`plan`/
`subscription`/`invoice` اتزرعت اتنضّفت في `finally`.

---

## 4) Regression — كل دالة تانية فيها `self.finance` أو بتستخدم `SaaSControlService`

```
grep -rn "SaaSControlService(" tests/
```

3 ملفات اختبار بتستخدم `SaaSControlService` مباشرة:

| الملف | عدد الاختبارات | النتيجة |
|---|---|---|
| `tests/test_saas_cancel_subscription_silent_write.py` (`cancel_subscription` — دالة **لا تستخدم** `self.finance` إطلاقًا) | 2 | ✅ 2/2 نجحوا |
| `tests/test_referral_affiliate_unified_system.py` (`SaaSControlService(db, tenant.id)` ضمن سياق أوسع) | 6 | ✅ 6/6 نجحوا |
| `tests/test_saas_active_subscription.py` (`can_access_service` عبر `_check_saas_limits` — دالة **لا تستخدم** `self.finance` أيضًا) | 4 | 🟡 2/4 نجحوا، 2 فشلوا |

**تحليل الفشلين — مؤكَّدان غير مرتبطين بإصلاح اليوم (traceback كامل):**

- `test_realestate_rent_unit_saas_check_passes` — بيفشل جوّه
  `realestate/service.py:465` (`PermissionDeniedError`: صاحب الوحدة
  الفعلي مختلف عن `landlord_id` المُمرَّر للاختبار) — **مشكلة بيانات/fixture
  داخل دومين `realestate` نفسه** (`_get_land_owner_for_unit` بترجع مالك
  تاني عن اللاندلورد اللي الاختبار زرعه)، صفر علاقة بـ`SaaSControlService`
  أو `FinanceService`.
- `test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug`
  — الاسم نفسه بيوثِّق إنها كانت بتتوقَّع كراش `TypeError` (باج قديم
  `execute_agent_action` زيادة `tenant_id=`، Backlog #16) **قبل** ما توصل
  لـ`finance.transfer` أصلًا. الباج ده اتصلح جزئيًا في جلسة سابقة (غير
  مرتبطة باليوم) — فالكود بقى يوصل فعليًا لـ`finance.transfer`، ويفشل
  هناك بـ`InsufficientBalanceError` (المشتري `_create_funded_user(...)`
  **بلا** تمرير `mr_usdt`، يعني رصيده `0` — الاختبار نفسه قديم ومكتوب
  قبل إصلاح باج #16، مش مُحدَّث ليعكس رصيد كافٍ للمسار الجديد).

**دليل قاطع إن الاثنين خارج نطاق اليوم:** `git status` بيأكد إن
`app/domains/realestate/service.py` كان **معدَّل بالفعل (uncommitted)
من قبل بداية هذه الجلسة** (نفس الـsnapshot الأصلي لأول رسالة في
المحادثة) — أي تغيير في سلوك `realestate` مصدره ديف سابق غير مرتبط،
مش تعديل اليوم على `saas/service.py`. كمان: لا `test_realestate_rent_unit_*`
ولا `test_realestate_buy_fractional_ownership_*` بيبنوا
`SaaSControlService` مباشرة أو يلمسوا `self.finance` — بيمروا فقط عبر
`_check_saas_limits`→`can_access_service`، الدالة المؤكَّدة مسبقًا إنها
**لا تستخدم `self.finance`/`FinanceService` إطلاقًا** (راجع قسم 1 فوق).
**صفر لمس، صفر إصلاح لهذين الفشلين اليوم** — خارج النطاق الضيق المطلوب.

---

## 5) تحديث البندين في `PROGRESS_LOG.md`

- `backlog-financeservice-tenant-binding-blocks-cross-tenant-operations`
  → **✅ اتحل** (داخل `SaaSControlService` تحديدًا — النطاق الأوسع عبر
  باقي الدومينات لسه غير ذي صلة، مفيش دومين تاني بيعاني من نفس النمط
  فعليًا، راجع تقرير الفحص الأصلي §3).
- `backlog-process-auto-renewals-task-tenant-zero-noop` → **✅ اتحل
  بالكامل** — الاختبار الحي (قسم 3 فوق) أثبت الحلقة الكاملة شغّالة
  فعليًا لأول مرة: اختيار الاشتراكات عبر كل التينانتات (كان اتصلح
  سابقًا) + تنفيذ العملية المالية الفعلي (SUCCESS حقيقي + PAST_DUE
  حقيقي)، مش بس اختيار الاشتراكات بلا تنفيذ.

تفاصيل التحديث الكاملة مُضافة كقسم جديد في آخر `PROGRESS_LOG.md`
(الملف تراكمي — لا يُعدَّل قديمه).
