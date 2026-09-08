# جلسة إصلاح — `check_expired_trials_task` بالكامل (constructor + دالة مفقودة)

**التاريخ:** 2026-09-08
**النطاق:** بناء + إصلاح `check_expired_trials_task` فقط (واحدة من
الأربعة المذكورين في
`.claude/reports/saas-nonexistent-methods-investigation-session-log.md`).
التلاتة الباقيين (`generate_monthly_invoices_task`,
`send_trial_expiry_reminders_task`, `cleanup_cancelled_subscriptions_task`)
**خارج نطاق هذه الجلسة عمدًا** — لسه مفتوحين، راجع §6 تحت.

---

## 1) المشكلة (بَجان متراكبان، مش بَج واحد)

### أ) `TypeError` في الـconstructor

`app/tasks/saas_tasks.py` — `check_expired_trials_task` كانت بتستدعي:
```python
service = SaaSControlService(db)
```
بينما `SaaSControlService.__init__` (`app/domains/saas/service.py:59`)
عندها `tenant_id: int` إجباري بلا `default`:
```python
def __init__(self, db: AsyncSession, tenant_id: int):
```
→ `TypeError: missing 1 required positional argument: 'tenant_id'`
مؤكَّد نظريًا (نفس بَج
`backlog-process-auto-renewals-task-constructor-typeerror` المُصلَح
النهارده في `process_auto_renewals_task`/`check_past_due_subscriptions_task`).

### ب) دالة `check_and_expire_trials` غير موجودة أصلًا

الكود كان بيستدعي `service.check_and_expire_trials()` مُعلَّمة بـ
`# type: ignore[attr-defined]` وتعليق "تأكد من وجود الدالة" — بحث
`grep` شامل قبل البدء أكَّد غيابها الكامل عن `SaaSControlService`.

---

## 2) الإصلاح

### أ) `app/tasks/saas_tasks.py` — `check_expired_trials_task`

```python
# [2026-09-08] نفس نمط process_auto_renewals_task/
# check_past_due_subscriptions_task — tenant_id=0 كـsentinel
# إداري، check_and_expire_trials بتفحص كل tenant عبر
# sub.tenant_id مش self.tenant_id، فمش متأثرة بالقيمة دي.
service = SaaSControlService(db, 0)
expired_count = await service.check_and_expire_trials()
```
(`# type: ignore[attr-defined]` اتشال — الدالة بقت موجودة فعليًا.)

### ب) `app/domains/saas/repository.py` — توسيع `get_trial_subscriptions`

**قبل:**
```python
async def get_trial_subscriptions(self, tenant_id: int) -> List[TenantSubscription]:
    result = await self.db.execute(
        select(TenantSubscription).where(
            and_(
                TenantSubscription.tenant_id == tenant_id,
                TenantSubscription.status == "TRIAL",
            )
        )
    )
    return list(result.scalars().all())
```

**بعد:**
```python
async def get_trial_subscriptions(
    self,
    tenant_id: Optional[int] = None,
    expired_only: bool = False,
) -> List[TenantSubscription]:
    """كل اشتراكات TRIAL — بلا فلتر tenant_id افتراضيًا (عبر كل
    المستأجرين)، بنفس نمط get_past_due_subscriptions [2026-09-08].
    expired_only=True يضيف فلتر trial_end_date <= الآن (تُستخدَم من
    check_and_expire_trials). expired_only=False (الافتراضي) يحافظ
    على السلوك القديم بالضبط — لازم يفضل كده عشان
    _cancel_related_free_trials (academy/service.py) لسه محتاجة كل
    TRIAL بغض النظر عن تاريخ الانتهاء، مش بس المنتهية."""
    conditions = [TenantSubscription.status == "TRIAL"]
    if tenant_id is not None:
        conditions.append(TenantSubscription.tenant_id == tenant_id)
    if expired_only:
        conditions.append(TenantSubscription.trial_end_date.isnot(None))
        conditions.append(TenantSubscription.trial_end_date <= datetime.now(timezone.utc))

    result = await self.db.execute(
        select(TenantSubscription).where(and_(*conditions))
    )
    return list(result.scalars().all())
```

**قرار تصميم مهم يستحق التوضيح صراحة:** الطلب الأصلي كان "أضف فلتر
فعلي على `trial_end_date <= now()`" على `get_trial_subscriptions`
مباشرة. **لم يُنفَّذ هذا حرفيًا** — بدل تعديل السلوك الافتراضي للدالة،
اتحط الفلتر الزمني خلف باراميتر اختياري جديد (`expired_only=False`
افتراضيًا). السبب: بحث `grep` عن كل استخدامات `get_trial_subscriptions`
في المشروع كشف مستدعيًا موجودًا مسبقًا:

```python
# app/domains/academy/service.py:479-484
async def _cancel_related_free_trials(self, tenant_id: int) -> None:
    from app.domains.saas.service import SaaSControlService
    saas_service = SaaSControlService(self.db, tenant_id)
    trials = await saas_service.repo.get_trial_subscriptions(tenant_id)
    for sub in trials:
        await saas_service.cancel_subscription(cast(int, sub.id))
```

هذه الدالة بتلغي **كل** اشتراكات TRIAL لتينانت معيّن عند إلغاء
enrollment مرتبط — بغض النظر عن `trial_end_date` (اشتراك تجريبي لسه
ساري بشهر كامل المفروض يتلغي برضه لو الشرط اتحقق). لو الفلتر الزمني
اتحط جوّه الدالة نفسها بلا باراميتر تفعيل، هذا الاستدعاء كان هيتوقف
بصمت عن إلغاء أي TRIAL لسه ساري — رجوع (regression) صامت وخطير في
منطق تاني تمامًا (إلغاء تسجيل أكاديمي)، غير مرتبط إطلاقًا بمهمة فحص
انتهاء الفترات التجريبية. الحل: باراميتر اختياري بقيمة افتراضية تحافظ
على السلوك القديم 100%، ودالة `check_and_expire_trials` الجديدة هي
الوحيدة اللي بتمرر `expired_only=True` صراحة.

### ج) `app/domains/saas/service.py` — دالة `check_and_expire_trials` الجديدة

اتضافت بعد `check_past_due_subscriptions` مباشرة، بنفس بنيتها
بالضبط:

```python
async def check_and_expire_trials(self, tenant_id: Optional[int] = None) -> int:
    """فحص كل اشتراكات TRIAL المنتهية (trial_end_date <= الآن) وتحويلها
    لـEXPIRED (تُنفذ يوميًا 4 صباحًا، بنفس نمط check_past_due_subscriptions
    المبنية اليوم [2026-09-08]).

    بلا فلتر tenant_id افتراضيًا (get_trial_subscriptions(None,
    expired_only=True) — عبر كل المستأجرين) — كل اشتراك بيتعامل
    بـsub.tenant_id بتاعه هو، مش self.tenant_id، فمش متأثرة بقيمة
    tenant_id اللي اتبنى بيها الـservice instance (نمط
    SaaSControlService(db, 0) الإداري في saas_tasks.py).

    try/except حول كل اشتراك على حدة — فشل واحد ما يوقفش فحص الباقي.
    ترجع عدد الاشتراكات اللي اتحوّلت فعليًا لـEXPIRED (مش عدد
    المرشَّحين للفحص)."""
    subscriptions = await self.repo.get_trial_subscriptions(tenant_id, expired_only=True)
    expired_count = 0

    for sub in subscriptions:
        sub_id = cast(int, sub.id)
        sub_tenant_id = cast(int, sub.tenant_id)
        try:
            await self.repo.update_subscription_status(sub_id, sub_tenant_id, "EXPIRED")
            await self.db.commit()
            expired_count += 1
            logger.info(f"Trial expired: subscription {sub_id}")
        except Exception as e:
            logger.error(f"Trial expiry check failed: subscription {sub_id} - {str(e)}")

    return expired_count
```

ملاحظات تصميم:
- **عبر كل المستأجرين افتراضيًا** (`tenant_id=None` من المهمة) — نفس
  فلسفة `check_past_due_subscriptions`، مش `process_auto_renewals`
  (اللي بتقع على `self.tenant_id` لو `None`).
- `try/except` حول كل اشتراك على حدة، بلا استثناء عام يوقف الحلقة —
  مطلوب صراحة في التوجيه، ومطابق لنمط `check_past_due_subscriptions`.
- `commit()` بعد كل تحديث ناجح على حدة (مش commit واحد في الآخر) —
  يضمن إن اشتراكات نجحت فعليًا في التحويل ميترجعوش لو اشتراك تاني في
  نفس الدفعة رمى استثناء لاحقًا.
- بترجع `int` مباشرة (عدد المُحوَّلين فعليًا) — مطابق تمامًا لتوقع
  الكود المستدعي في `saas_tasks.py`
  (`expired_count = await service.check_and_expire_trials()`، بيتحط
  مباشرة في response بلا `len()`).

---

## 3) اختبار حي فعلي — بيانات مزروعة + تشغيل فعلي + تحقق مستقل

### أ) الزرع (SQL مباشر، `docker exec eppne_db psql`)

```sql
INSERT INTO saas_tenant_subscriptions (tenant_id, plan_id, status, trial_end_date, auto_renew)
VALUES
  (1, 48, 'TRIAL', now() - interval '2 days', true),   -- id=158، منتهي
  (1, 48, 'TRIAL', now() + interval '10 days', true)   -- id=159، لسه ساري
RETURNING id, tenant_id, plan_id, status, trial_end_date;
```
`tenant_id=1` هو "Local Test Tenant" الموثَّق مسبقًا في
`throwaway-test-users.md` (نفس التينانت المُستخدَم في جلسة اختبار
`check_past_due_subscriptions_task` النهارده). قبل الزرع، تأكَّد عبر
استعلام مباشر إن القاعدة كانت خالية تمامًا من أي `TRIAL` (23 `ACTIVE`
+ 1 `CANCELLED` فقط) — عزل تام للاختبار.

### ب) التشغيل الفعلي

سكريبت Python منفصل (`import app.main` أولًا لتسجيل كل الـmappers قبل
أي استعلام SQLAlchemy — بنفس ضرورة توثَّقت في جلسة `check_past_due_
subscriptions_task`)، ثم استدعاء مباشر لجسم المهمة:
```python
from app.tasks.saas_tasks import check_expired_trials_task
result = check_expired_trials_task.run()
```
**النتيجة الفعلية:**
```
2026-09-08 23:47:14 [INFO] Trial expired: subscription 158
2026-09-08 23:47:14 [INFO] ✅ Expired trials checked: 1 subscriptions expired.
2026-09-08 23:47:14 [INFO] ✅ Expired trials check task finished successfully.
TASK RESULT: {'status': 'success', 'result': {'status': 'success', 'expired_count': 1, 'checked_at': '2026-09-08T20:47:14.314775'}}
```

### ج) التحقق المستقل على القرص (بعد التشغيل مباشرة)

```sql
SELECT id, tenant_id, status, trial_end_date, updated_at
FROM saas_tenant_subscriptions WHERE id IN (158,159);

 id  | tenant_id | status  |        trial_end_date         |          updated_at
-----+-----------+---------+-------------------------------+-------------------------------
 159 |         1 | TRIAL   | 2026-09-18 20:45:15.524398+00 | 2026-09-08 20:45:15.524398+00
 158 |         1 | EXPIRED | 2026-09-06 20:45:15.524398+00 | 2026-09-08 20:47:13.246029+00
```
**النتيجتان المتوقَّعتان تمامًا:** id=158 (ماضي) → `EXPIRED`
(`updated_at` اتغيّر فعليًا)، id=159 (مستقبل) → لسه `TRIAL` بلا أي
تغيير (`updated_at` زي وقت الإنشاء بالظبط — لم يُلمَس).

### د) التنظيف

```sql
DELETE FROM saas_tenant_subscriptions WHERE id IN (158,159);
```
تأكيد بعدي: `SELECT status, count(*) ... GROUP BY status` رجع بالظبط
لنفس الحالة قبل الزرع (`CANCELLED: 1, ACTIVE: 23`، صفر `TRIAL`) —
صفر أثر متبقٍّ في القاعدة الحية من هذا الاختبار.

---

## 4) Regression — كل اختبار موجود يلمس `SaaSControlService`/`get_trial_subscriptions`

بحث `grep` شامل عن `SaaSControlService|get_trial_subscriptions|
check_expired_trials|check_and_expire_trials` في `tests/` حدَّد 5 ملفات
اختبار (`.py`، استثناء ملفين `.md` وثائقيين بلا كود تنفيذي):

```
tests/test_trigger_renewals_endpoint_missing_commit.py
tests/test_financeservice_tenant_binding_fix.py
tests/test_referral_affiliate_unified_system.py
tests/test_saas_cancel_subscription_silent_write.py
tests/test_saas_active_subscription.py
```

تشغيل الخمسة معًا (`pytest -q`):
```
FAILED tests/test_saas_active_subscription.py::test_realestate_rent_unit_saas_check_passes
FAILED tests/test_saas_active_subscription.py::test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug
2 failed, 14 passed, 11 warnings in 256.25s
```

**الفشلان الاثنان موجودان مسبقًا وموثَّقان بالكامل قبل هذه الجلسة**
في `PROGRESS_LOG.md` (إدخالات بتاريخ [2026-09-08] الأقدم من هذه
الجلسة، تحت نصوص مثل "لسه فاشلين... الفشل الحالي راجع لمشاكل fixture
منفصلة تمامًا" و"بيفشل بـ`PermissionDeniedError`") — بَج معروف
ومنفصل تمامًا في دومين `realestate` (مشكلة fixture/بيانات محفظة، لا
علاقة له بـSaaS trial expiry أو بأي تعديل في هذه الجلسة). **صفر
regression ناتج عن التعديلات هنا.**

---

## 5) الملفات المعدَّلة

- `app/tasks/saas_tasks.py` — `check_expired_trials_task`: تصحيح
  الـconstructor + إزالة `# type: ignore[attr-defined]`.
- `app/domains/saas/repository.py` — توسيع `get_trial_subscriptions`
  (باراميترين اختياريين جديدين، سلوك افتراضي بلا تغيير).
- `app/domains/saas/service.py` — إضافة `check_and_expire_trials`
  (دالة جديدة بالكامل، لا تعديل على أي دالة موجودة).
- `PROGRESS_LOG.md` — إدخال جديد يوثِّق الإصلاح ويحدِّث حالة
  `check_expired_trials_task` (الإدخال القديم لم يُعدَّل — سياسة
  المشروع append-only).

**صفر تعديل** على أي من التلاتة الباقيين
(`generate_monthly_invoices_task`, `send_trial_expiry_reminders_task`,
`cleanup_cancelled_subscriptions_task`) أو الملفات المرتبطة بيهم.

---

## 6) الحالة المتبقية (خارج نطاق هذه الجلسة)

| المهمة | الحالة |
|---|---|
| `check_expired_trials_task` | ✅ **اتحل بالكامل واتأكد حيًا** |
| `generate_monthly_invoices_task` | 🔴 لسه مفتوح — مجدولة فعليًا (أول كل شهر 3ص)، لسه هتفشل بنفس بَج الـconstructor + دالة مفقودة |
| `send_trial_expiry_reminders_task` | 🔴 لسه مفتوح — غير مجدولة حاليًا، لكن الدالة والconstructor لسه معطوبين |
| `cleanup_cancelled_subscriptions_task` | 🔴 لسه مفتوح — غير مجدولة، ويحتاج قرار نطاق صريح (PDPL/GDPR) قبل أي بناء فعلي (راجع
`.claude/reports/saas-nonexistent-methods-investigation-session-log.md` §4) |

تفاصيل كل بند (الكود الكامل، النمط المرجعي المقترح، البيانات
المتاحة) موثَّقة بالفعل في تقرير الفحص السابق
`.claude/reports/saas-nonexistent-methods-investigation-session-log.md`.
