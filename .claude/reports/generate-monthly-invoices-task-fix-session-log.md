# جلسة إصلاح — `generate_monthly_invoices_task` بالكامل (constructor + دالة مفقودة)

**التاريخ:** 2026-09-09
**النطاق:** بناء + إصلاح `generate_monthly_invoices_task` فقط (ثانية من
الأربعة المذكورين في
`.claude/reports/saas-nonexistent-methods-investigation-session-log.md`،
بعد `check_expired_trials_task` — راجع
`.claude/reports/check-expired-trials-task-fix-session-log.md`).
الاثنان الباقيان (`send_trial_expiry_reminders_task`,
`cleanup_cancelled_subscriptions_task`) **خارج نطاق هذه الجلسة عمدًا**
— لسه مفتوحين.

التصميم مُتفَق عليه بالكامل من المستخدم قبل التنفيذ: هذه المهمة تخص
الاشتراكات `ACTIVE` بـ`auto_renew=False` فقط (العميل اختار الدفع
اليدوي، بعكس `process_auto_renewals` اللي تخص `auto_renew=True`). لكل
اشتراك منهم مستحق الفاتورة الشهرية، تُصدر فاتورة `PENDING` بلا أي خصم
فوري من المحفظة — الدفع الفعلي بيحصل لاحقًا عبر `pay_invoice` الموجودة
أصلًا.

---

## 1) المشكلة (بَجان متراكبان، مش بَج واحد)

### أ) `TypeError` في الـconstructor

`app/tasks/saas_tasks.py` — `generate_monthly_invoices_task` كانت
بتستدعي:
```python
service = SaaSControlService(db)
```
بينما `SaaSControlService.__init__` (`app/domains/saas/service.py:59`)
عندها `tenant_id: int` إجباري بلا `default` → `TypeError: missing 1
required positional argument: 'tenant_id'` — نفس بَج
`backlog-process-auto-renewals-task-constructor-typeerror` المُصلَح في
`process_auto_renewals_task`/`check_past_due_subscriptions_task`/
`check_expired_trials_task`.

### ب) دالة `generate_monthly_invoices` غير موجودة أصلًا

الكود كان بيستدعي `service.generate_monthly_invoices()` مُعلَّمة بـ
`# type: ignore[attr-defined]` وتعليق "تأكد من وجود الدالة" — `grep`
شامل قبل البدء أكَّد غيابها الكامل عن `SaaSControlService`.

---

## 2) الإصلاح

### أ) `app/tasks/saas_tasks.py` — `generate_monthly_invoices_task`

```python
# [2026-09-09] نفس نمط process_auto_renewals_task/
# check_expired_trials_task — tenant_id=0 كـsentinel إداري،
# generate_monthly_invoices بتفحص كل tenant عبر sub.tenant_id
# مش self.tenant_id، فمش متأثرة بالقيمة دي.
service = SaaSControlService(db, 0)
issued_count = await service.generate_monthly_invoices()
await db.commit()

logger.info(f"✅ Monthly invoices generated: {issued_count} invoices issued.")
return {
    "status": "success",
    "issued_count": issued_count,
    "generated_at": datetime.utcnow().isoformat()
}
```
(`# type: ignore[attr-defined]` اتشال — الدالة بقت موجودة فعليًا.
تحديث docstring المهمة برضه ليعكس النطاق الحقيقي: فوترة يدوية
لـ`auto_renew=False`، مش "كل المستأجرين النشطين" كما كان مكتوبًا
بالغلط سابقًا.)

### ب) `app/domains/saas/repository.py` — استعلام جديد `get_subscriptions_for_manual_billing`

اتضافت مباشرة قبل `get_past_due_subscriptions`، بنفس بنية
`get_subscriptions_for_renewal` الموجودة تمامًا لكن بفلتر معكوس على
`auto_renew`:

```python
async def get_subscriptions_for_manual_billing(self, tenant_id: Optional[int] = None) -> List[TenantSubscription]:
    """اشتراكات ACTIVE بـauto_renew=False مستحقة الفاتورة الشهرية
    (next_billing_date <= الآن) — نفس معيار الاستحقاق في
    get_subscriptions_for_renewal، لكن لعملاء الدفع اليدوي (بعكسها
    اللي تخص auto_renew=True). تُستخدَم من generate_monthly_invoices
    [2026-09-09]. بلا فلتر tenant_id افتراضيًا (عبر كل المستأجرين)."""
    now = datetime.now(timezone.utc)
    query = select(TenantSubscription).where(
        and_(
            TenantSubscription.status == "ACTIVE",
            TenantSubscription.auto_renew == False,
            TenantSubscription.next_billing_date <= now
        )
    )
    if tenant_id is not None:
        query = query.where(TenantSubscription.tenant_id == tenant_id)
    result = await self.db.execute(query)
    return list(result.scalars().all())
```

**قرار تصميم:** دالة منفصلة تمامًا، مش توسيع `get_subscriptions_for_renewal`
بباراميتر إضافي — الاسمان والغرضان مختلفان جوهريًا (تجديد تلقائي
مقابل فوترة يدوية)، وتوسيع الدالة الموجودة بفلتر `auto_renew`
اختياري كان سيغيّر توقيعها بلا داعٍ فعلي (كل مستدعييها الحاليين
يريدون `auto_renew=True` تحديدًا). هذا مطابق للنمط الموصوف صراحة في
التوجيه الأصلي.

### ج) `app/domains/saas/service.py` — دالة `generate_monthly_invoices` الجديدة

اتضافت قبل `check_past_due_subscriptions` مباشرة:

```python
async def generate_monthly_invoices(self, tenant_id: Optional[int] = None) -> int:
    subscriptions = await self.repo.get_subscriptions_for_manual_billing(tenant_id)
    issued_count = 0

    for sub in subscriptions:
        sub_id = cast(int, sub.id)
        sub_tenant_id = cast(int, sub.tenant_id)
        try:
            plan = await self.repo.get_plan_by_id_admin(cast(int, sub.plan_id))
            if not plan:
                continue

            async with self.db.begin_nested():
                await self._generate_invoice(
                    tenant_id=sub_tenant_id,
                    subscription_id=sub_id,
                    plan=plan,
                )

                await self.repo.update_subscription(
                    sub_id,
                    sub_tenant_id,
                    next_billing_date=datetime.now(timezone.utc) + timedelta(days=30),
                )

            await self.db.commit()
            issued_count += 1
            logger.info(f"Monthly invoice generated: subscription {sub_id}")

        except Exception as e:
            logger.error(f"Monthly invoice generation failed: subscription {sub_id} - {str(e)}")

    return issued_count
```

ملاحظات تصميم:
- **`_generate_invoice` الموجودة أصلًا مُعاد استخدامها كما هي** — بلا
  أي تعديل عليها. هي نفس الدالة المستخدمة جوّه `process_auto_renewals`
  (idempotent عبر hash من `tenant_id:subscription_id:period`).
- **صفر استدعاء لـ`FinanceService`/`get_or_create_system_account`/
  `transfer`** — الفرق الجوهري المتعمَّد عن `process_auto_renewals`؛
  الفاتورة تُصدر بحالة `PENDING` فقط، والدفع الفعلي يحصل لاحقًا عبر
  `pay_invoice` الموجودة.
- `next_billing_date += 30 يوم` بعد الإصدار — **نفس منطق
  `process_auto_renewals` بالحرف** (`datetime.now(timezone.utc) +
  timedelta(days=30)`)، عشان الاشتراك ميرجعش مستحقًا في نفس الشهر.
- `async with self.db.begin_nested()` حول الفاتورة + تحديث
  `next_billing_date` معًا — لو أي منهما فشل، الاتنين يترجعوا سوا
  (لا فاتورة يتيمة بلا تحديث تاريخ، ولا العكس)، بنفس فلسفة
  `process_auto_renewals`.
- `try/except` حول كل اشتراك على حدة — فشل واحد ما يوقفش معالجة
  الباقي، مطابق للنمط الموحَّد في باقي مهام `saas_tasks.py`.
- بلا فلتر `tenant_id` افتراضيًا (عبر كل المستأجرين)، بنفس نمط
  `process_auto_renewals`/`check_past_due_subscriptions`.
- بترجع `int` (عدد الفواتير المُصدرة فعليًا في هذا التشغيل، مش عدد
  المرشَّحين للفحص) — مطابق تمامًا لتوقع الكود المستدعي في
  `saas_tasks.py`.

---

## 3) اختبار حي فعلي — بيانات مزروعة + تشغيل فعلي + تحقق مستقل

### أ) حالة القاعدة قبل الزرع

```sql
SELECT status, auto_renew, count(*) FROM saas_tenant_subscriptions GROUP BY status, auto_renew ORDER BY 1,2;

  status   | auto_renew | count
-----------+------------+-------
 ACTIVE    | f          |     1   -- id=2، next_billing_date مستقبلي (2026-09-17)، مش مستحق
 ACTIVE    | t          |    13
 ACTIVE    |            |     9
 CANCELLED | f          |     1
```

### ب) الزرع (SQL مباشر، `docker exec eppne_db psql -d eppne_v2`)

```sql
INSERT INTO saas_tenant_subscriptions (tenant_id, plan_id, status, auto_renew, start_date, next_billing_date, idempotency_key)
VALUES
  (1, 48, 'ACTIVE', false, now() - interval '35 days', now() - interval '1 hour', 'TEST-GENMONTH-MANUAL-...'),
  (1, 48, 'ACTIVE', true,  now() - interval '35 days', now() - interval '1 hour', 'TEST-GENMONTH-AUTO-...')
RETURNING id, ...;

 id  | tenant_id | plan_id | status | auto_renew |       next_billing_date
-----+-----------+---------+--------+------------+--------------------------------
 163 |         1 |      48 | ACTIVE | f          | 2026-09-08 20:05:11.185845+00   -- الهدف
 164 |         1 |      48 | ACTIVE | t          | 2026-09-08 20:05:11.185845+00   -- كنترول
```
`tenant_id=1`/`plan_id=48` نفس التينانت/الخطة الموثَّقة والمُستخدَمة في
جلسة `check_expired_trials_task` (`throwaway-test-users.md`).
`price_monthly=0.00000000` لخطة 48 — لا يؤثر على صحة الاختبار لأن
المسار بالكامل بلا `FinanceService` أصلًا.

### ج) التشغيل الفعلي (مرة أولى)

```python
import app.main
from app.tasks.saas_tasks import generate_monthly_invoices_task
result = generate_monthly_invoices_task.run()
```
**النتيجة:**
```
[INFO] Monthly invoice generated: subscription 163
[INFO] ✅ Monthly invoices generated: 1 invoices issued.
TASK RESULT: {'status': 'success', 'result': {'status': 'success', 'issued_count': 1, 'generated_at': '2026-09-08T21:06:53...'}}
```

### د) التحقق المستقل على القرص (بعد التشغيل مباشرة)

```sql
SELECT id, tenant_id, status, auto_renew, next_billing_date, updated_at FROM saas_tenant_subscriptions WHERE id IN (163,164);

 id  | tenant_id | status | auto_renew |       next_billing_date       |          updated_at
-----+-----------+--------+------------+-------------------------------+-------------------------------
 164 |         1 | ACTIVE | t          | 2026-09-08 20:05:11.185845+00 | 2026-09-08 21:05:11.185845+00  -- بلا تغيير (نفس microseconds من الـINSERT)
 163 |         1 | ACTIVE | f          | 2026-10-08 21:06:51.951817+00 | 2026-09-08 21:06:50.145125+00  -- +30 يوم فعليًا، updated_at تغيّر

SELECT id, tenant_id, subscription_id, invoice_number, amount, currency, status FROM saas_invoices WHERE subscription_id IN (163,164);

 id | tenant_id | subscription_id |  invoice_number  |   amount   | currency | status
----+-----------+------------------+------------------+------------+----------+---------
 12 |         1 |             163 | INV-6EEA4EADE936 | 0.00000000 | MR_USDT  | PENDING
```
**id=163 (الهدف، auto_renew=false):** فاتورة `PENDING` حقيقية اتصدرت،
`next_billing_date` اتحدّث فعليًا لـ+30 يوم بالظبط.
**id=164 (الكنترول، auto_renew=true):** **صفر تغيير** — `updated_at`
لسه بنفس microseconds لحظة الزرع (لم يُلمَس إطلاقًا)، صفر فاتورة له.
**إثبات مباشر إن الفلترة صح ومفيش تداخل مع `process_auto_renewals`.**

**صفر خصم من أي محفظة:**
```sql
SELECT count(*) FROM transactions WHERE created_at > now() - interval '10 minutes';
 count
-------
     0
```

### هـ) اختبار idempotency (تشغيل ثانٍ فوري)

```python
result = generate_monthly_invoices_task.run()
```
```
TASK RESULT: {..., 'issued_count': 0, ...}
```
id=163 مبقاش مرشَّحًا (next_billing_date اتحرك للمستقبل) — صفر فاتورة
مكررة، صفر استعلام فاشل.

### و) التنظيف

```sql
DELETE FROM saas_invoices WHERE subscription_id IN (163,164);
DELETE FROM saas_tenant_subscriptions WHERE id IN (163,164);
```
تأكيد بعدي: `GROUP BY status, auto_renew` رجع بالظبط لنفس الحالة قبل
الزرع (`ACTIVE/f: 1، ACTIVE/t: 13، ACTIVE/NULL: 9، CANCELLED/f: 1`) —
صفر أثر متبقٍّ في القاعدة الحية من هذا الاختبار.

---

## 4) Regression — كل اختبار موجود يلمس `SaaSControlService`

نفس الخمسة ملفات المفحوصة في جلسة `check_expired_trials_task`:
```
tests/test_trigger_renewals_endpoint_missing_commit.py
tests/test_financeservice_tenant_binding_fix.py
tests/test_referral_affiliate_unified_system.py
tests/test_saas_cancel_subscription_silent_write.py
tests/test_saas_active_subscription.py
```
```
FAILED tests/test_saas_active_subscription.py::test_realestate_rent_unit_saas_check_passes
FAILED tests/test_saas_active_subscription.py::test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug
2 failed, 14 passed, 11 warnings in 174.93s
```
**نفس الفشلان الاثنان الموجودان مسبقًا وموثَّقان بالكامل قبل هذه
الجلسة** (بَج fixture/بيانات محفظة معروف ومنفصل تمامًا في دومين
`realestate`، لا علاقة له بهذا التعديل). **صفر regression ناتج عن
التعديلات هنا.**

---

## 5) الملفات المعدَّلة

- `app/tasks/saas_tasks.py` — `generate_monthly_invoices_task`:
  تصحيح الـconstructor + إزالة `# type: ignore[attr-defined]` +
  تحديث docstring النطاق.
- `app/domains/saas/repository.py` — إضافة
  `get_subscriptions_for_manual_billing` (دالة جديدة بالكامل، صفر
  تعديل على `get_subscriptions_for_renewal` الموجودة).
- `app/domains/saas/service.py` — إضافة `generate_monthly_invoices`
  (دالة جديدة بالكامل، صفر تعديل على `process_auto_renewals` أو أي
  دالة موجودة أخرى).
- `PROGRESS_LOG.md` — إدخال جديد يوثِّق الإصلاح (الإدخال القديم لم
  يُعدَّل — سياسة المشروع append-only).

**صفر تعديل** على الاثنين الباقيين (`send_trial_expiry_reminders_task`,
`cleanup_cancelled_subscriptions_task`) أو الملفات المرتبطة بيهم.

---

## 6) الحالة المتبقية (خارج نطاق هذه الجلسة)

| المهمة | الحالة |
|---|---|
| `check_expired_trials_task` | ✅ اتحل بالكامل واتأكد حيًا [2026-09-08] |
| `generate_monthly_invoices_task` | ✅ **اتحل بالكامل واتأكد حيًا (هذه الجلسة)** |
| `send_trial_expiry_reminders_task` | 🔴 لسه مفتوح — غير مجدولة حاليًا، الدالة والconstructor لسه معطوبين |
| `cleanup_cancelled_subscriptions_task` | 🔴 لسه مفتوح — غير مجدولة، ويحتاج قرار نطاق صريح (PDPL/GDPR) قبل أي بناء فعلي |

تفاصيل كل بند متبقٍّ موثَّقة في
`.claude/reports/saas-nonexistent-methods-investigation-session-log.md`.
