# جلسة إصلاح — `send_trial_expiry_reminders_task` بالكامل (constructor + دالة مفقودة)

**التاريخ:** 2026-09-09
**النطاق:** بناء + إصلاح `send_trial_expiry_reminders_task` فقط — تالت
واحدة من الأربعة المذكورين في
`.claude/reports/saas-nonexistent-methods-investigation-session-log.md`.
الرابع (`cleanup_cancelled_subscriptions_task`) **خارج نطاق هذه الجلسة
عمدًا** — لسه مفتوح، يحتاج قرار نطاق صريح PDPL/GDPR أولًا.

---

## 1) المشكلة (بَجان متراكبان، نفس نمط `check_expired_trials_task`)

### أ) `TypeError` في الـconstructor

`app/tasks/saas_tasks.py` — `send_trial_expiry_reminders_task` كانت
بتستدعي:
```python
service = SaaSControlService(db)
```
بينما `SaaSControlService.__init__` (`app/domains/saas/service.py:59`)
عندها `tenant_id: int` إجباري بلا `default` → `TypeError: missing 1
required positional argument: 'tenant_id'` مؤكَّد نظريًا (نفس بَج
`process_auto_renewals_task`/`check_past_due_subscriptions_task`/
`check_expired_trials_task`).

### ب) دالة `send_trial_expiry_reminders` غير موجودة أصلًا

الكود كان بيستدعي `service.send_trial_expiry_reminders()` مُعلَّمة بـ
`# type: ignore[attr-defined]` وتعليق "تأكد من وجود الدالة" — غياب
كامل عن `SaaSControlService`، مؤكَّد بـ`grep` قبل البدء.

---

## 2) الإصلاح

### أ) `app/tasks/saas_tasks.py` — `send_trial_expiry_reminders_task`

```python
# [2026-09-09] نفس نمط check_past_due_subscriptions_task —
# tenant_id=0 كـsentinel إداري، send_trial_expiry_reminders
# بتفحص كل tenant عبر sub.tenant_id مش self.tenant_id، فمش
# متأثرة بالقيمة دي.
service = SaaSControlService(db, 0)
reminders_sent = await service.send_trial_expiry_reminders()
```
(`# type: ignore[attr-defined]` اتشال — الدالة بقت موجودة فعليًا.)
الدوكستring في أعلى المهمة اتصحّح كمان — كانت بتقول "تُرسل إشعارات
In-App وبريد إلكتروني" بالغلط؛ بقت توضّح صراحة إن `EMAIL` ممنوعة
(stub فاضي، backlog منفصل).

### ب) `app/domains/saas/service.py` — دالة `send_trial_expiry_reminders` الجديدة

اتضافت بعد `check_and_expire_trials` مباشرة، بنفس بنية
`check_past_due_subscriptions` تمامًا:

```python
async def send_trial_expiry_reminders(self, tenant_id: Optional[int] = None) -> int:
    from app.domains.communications.service import CommunicationsService

    subscriptions = await self.repo.get_trial_subscriptions(tenant_id, expired_only=False)
    comm_service = CommunicationsService(self.db)
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(days=2)
    reminders_sent = 0

    for sub in subscriptions:
        trial_end = sub.trial_end_date
        if trial_end is None or not (now <= trial_end <= window_end):
            continue

        sub_id = cast(int, sub.id)
        sub_tenant_id = cast(int, sub.tenant_id)

        try:
            admin_id = await self._get_tenant_admin_id(sub_tenant_id)

            await comm_service.send_notification(
                user_id=admin_id,
                title="تنبيه: الفترة التجريبية توشك على الانتهاء",
                body="باقي يومين بس على انتهاء الفترة التجريبية.",
                data={"subscription_id": sub_id},
                channel="IN_APP",
                idempotency_key=f"SUB-TRIAL-REMIND-{sub_id}",
            )

            reminders_sent += 1
            logger.info(f"Trial expiry reminder sent: subscription {sub_id}")

        except Exception as e:
            logger.error(f"Trial expiry reminder failed: subscription {sub_id} - {str(e)}")

    return reminders_sent
```

ملاحظات تصميم:
- **`get_trial_subscriptions(tenant_id, expired_only=False)`** — مش
  `expired_only=True` زي `check_and_expire_trials`، لأن المطلوب هنا
  اشتراكات **لسه سارية** وقربت تنتهي، مش المنتهية بالفعل. الدالة دي
  اتوسّعت أصلًا في جلسة `check_expired_trials_task` بباراميترين
  اختياريين — لم يُلمَس أي سلوك افتراضي موجود.
- **فلتر النافذة محلي في `send_trial_expiry_reminders` نفسها**
  (`now <= trial_end_date <= now + 2 days`)، مش داخل `get_trial_
  subscriptions` — بنفس فلسفة الفصل بين "جلب كل TRIAL" و"منطق
  التذكير المحدد" الموثَّقة في جلسة `check_expired_trials_task` (عشان
  `_cancel_related_free_trials` في `academy/service.py` تفضل شغالة
  صح بلا فلتر).
- `channel="IN_APP"` فقط، `idempotency_key=f"SUB-TRIAL-REMIND-
  {sub_id}"` — نفس نمط `send_notification` المستخدَم حرفيًا في
  `check_past_due_subscriptions`.
- `try/except` حول كل اشتراك على حدة — فشل واحد ما يوقفش فحص الباقي،
  مطلوب صراحة في التوجيه ومطابق لنمط `check_past_due_subscriptions`.
- بترجع `int` مباشرة (عدد التذكيرات اللي اتبعتت فعليًا عبر
  `send_notification` بلا استثناء) — مطابق تمامًا لتوقع الكود
  المستدعي في `saas_tasks.py`.

---

## 3) اختبار حي فعلي — بيانات مزروعة + تشغيلتان منفصلتان (idempotency) + تحقق مستقل

### أ) الزرع (SQL مباشر، `docker exec eppne_db psql -d eppne_v2`)

```sql
INSERT INTO saas_tenant_subscriptions (tenant_id, plan_id, status, trial_end_date, auto_renew)
VALUES
  (1, 48, 'TRIAL', now() + interval '1.5 days', true),  -- id=173، لازم يتبعتله تذكير
  (1, 48, 'TRIAL', now() + interval '7 days',   true),  -- id=174، لازم ما يتبعتلوش
  (1, 48, 'TRIAL', now() + interval '1.5 days', true)   -- id=175، لاختبار idempotency
RETURNING id, tenant_id, plan_id, status, trial_end_date;
```
`tenant_id=1` = "Local Test Tenant" (`admin_id=1`)، `plan_id=48` —
نفس البيانات المرجعية المستخدَمة في جلسة `check_expired_trials_task`.
قبل الزرع: `SELECT count(*) FROM saas_tenant_subscriptions WHERE
status='TRIAL'` رجع `0` — عزل تام للاختبار.

### ب) التشغيلة الأولى

سكريبت Python منفصل (`import app.main` أولًا، ثم استدعاء مباشر لجسم
المهمة عبر `send_trial_expiry_reminders_task.run()`):
```
2026-09-09 00:27:33 [INFO] Trial expiry reminder sent: subscription 173
2026-09-09 00:27:38 [INFO] Trial expiry reminder sent: subscription 175
2026-09-09 00:27:38 [INFO] ✅ Trial expiry reminders sent: 2 notifications.
TASK RESULT: {'status': 'success', 'result': {'status': 'success', 'reminders_sent': 2, 'sent_at': '...'}}
```
`174` (7 أيام) اتفحص بس اتفضل بره النافذة — صفر لوج ليه، مطابق تمامًا
للتوقع.

### ج) التشغيلة الثانية (idempotency)

**ملاحظة تقنية مهمة عن سكريبت الاختبار نفسه (مش عن الكود المُنفَّذ):**
استدعاء `.run()` مرتين في نفس عملية Python واحدة بيرمي `AttributeError:
'NoneType' object has no attribute 'send'` بسبب تسريب event loop مغلق
من `_run_async` (نفس التفصيلة الموثَّقة مسبقًا في جلسة
`past-due-grace-period-notifications-implementation-session-log.md`
§"ملاحظة تقنية عن سكريبت الاختبار نفسه"). الحل: تشغيل السكريبت **كعملية
Python منفصلة تمامًا** للمرة الثانية:
```
2026-09-09 00:29:14 [INFO] Trial expiry reminder sent: subscription 173
2026-09-09 00:29:14 [INFO] Trial expiry reminder sent: subscription 175
TASK RESULT: {'status': 'success', 'result': {'status': 'success', 'reminders_sent': 2, 'sent_at': '...'}}
```
`reminders_sent: 2` برضو — **متوقَّع**، لأن الكود بيعتبر أي
`send_notification` رجع بلا استثناء "مُرسَل" (حتى لو كان idempotent
duplicate رجّع الصف الموجود مسبقًا)، بنفس فلسفة `check_past_due_
subscriptions`. الدليل الحاسم على الـidempotency الفعلية هو صفوف
جدول `notifications`، مش الرقم المرجَع من الـtask.

### د) التحقق المستقل على القرص (بعد التشغيلتين)

```sql
SELECT id, user_id, idempotency_key, title, channel, created_at
FROM notifications WHERE idempotency_key LIKE 'SUB-TRIAL-REMIND-%'
ORDER BY idempotency_key;

 id | user_id |   idempotency_key    |                   title                   | channel |          created_at
----+---------+----------------------+--------------------------------------------+---------+-------------------------------
 30 |       1 | SUB-TRIAL-REMIND-173 | تنبيه: الفترة التجريبية توشك على الانتهاء | IN_APP  | 2026-09-08 21:27:33.732633+00
 31 |       1 | SUB-TRIAL-REMIND-175 | تنبيه: الفترة التجريبية توشك على الانتهاء | IN_APP  | 2026-09-08 21:27:38.702557+00
```
**صفان بالظبط**، `created_at` كلاهما من التشغيلة الأولى (21:27) —
التشغيلة الثانية (21:29) **صفر صف جديد**. صفر `SUB-TRIAL-REMIND-174`
— التذكير اتبعت للاشتراكين المستهدَفين بس، مطابق تمامًا للتوقع.

حالة الاشتراكات التلاتة بعد التشغيلتين:
```sql
SELECT id, status, trial_end_date FROM saas_tenant_subscriptions WHERE id IN (173,174,175);

 id  | status |        trial_end_date
-----+--------+-------------------------------
 173 | TRIAL  | 2026-09-10 09:26:08.771102+00
 174 | TRIAL  | 2026-09-15 21:26:08.771102+00
 175 | TRIAL  | 2026-09-10 09:26:08.771102+00
```
**التلاتة لسه `TRIAL` بلا أي تغيير** — الدالة دي بترسل تذكيرات بس، ما
بتلمسش `status` إطلاقًا (بعكس `check_and_expire_trials`).

### هـ) التنظيف

```sql
DELETE FROM notifications WHERE idempotency_key LIKE 'SUB-TRIAL-REMIND-%';
DELETE FROM saas_tenant_subscriptions WHERE id IN (173,174,175);
```
تأكيد بعدي: `count(*) WHERE status='TRIAL'` = `0`، `count(*) WHERE
idempotency_key LIKE 'SUB-TRIAL-REMIND-%'` = `0` — صفر أثر متبقٍّ في
القاعدة الحية من هذا الاختبار.

---

## 4) Regression — كل اختبار موجود يلمس `SaaSControlService`/`get_trial_subscriptions`

نفس الخمسة ملفات اختبار المحدَّدة في جلسة `check_expired_trials_task`:
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
2 failed, 14 passed, 11 warnings in 167.61s
```
**نفس الفشلان الاثنان الموجودان مسبقًا وموثَّقان بالكامل قبل هذه
الجلسة** في `PROGRESS_LOG.md` — بَج معروف ومنفصل تمامًا في دومين
`realestate` (مشكلة fixture/بيانات محفظة)، لا علاقة له بـSaaS trial
reminders أو بأي تعديل في هذه الجلسة. **صفر regression ناتج عن
التعديلات هنا.**

---

## 5) الملفات المعدَّلة

- `app/tasks/saas_tasks.py` — `send_trial_expiry_reminders_task`:
  تصحيح الـconstructor + إزالة `# type: ignore[attr-defined]` +
  تصحيح الدوكستring (شيل ذِكر EMAIL).
- `app/domains/saas/service.py` — إضافة `send_trial_expiry_reminders`
  (دالة جديدة بالكامل، لا تعديل على أي دالة موجودة).
- `PROGRESS_LOG.md` — إدخال جديد يوثِّق الإصلاح ويحدِّث حالة
  `send_trial_expiry_reminders_task` (الإدخالات القديمة لم تُعدَّل —
  سياسة المشروع append-only).

**صفر تعديل** على `cleanup_cancelled_subscriptions_task` أو الملفات
المرتبطة بيه — لسه خارج النطاق.

---

## 6) الحالة المتبقية (خارج نطاق هذه الجلسة)

| المهمة | الحالة |
|---|---|
| `check_expired_trials_task` | ✅ اتحل بالكامل واتأكد حيًا [2026-09-08] |
| `generate_monthly_invoices_task` | ✅ اتحل بالكامل واتأكد حيًا [2026-09-09] |
| `send_trial_expiry_reminders_task` | ✅ **اتحل بالكامل واتأكد حيًا** (هذه الجلسة) |
| `cleanup_cancelled_subscriptions_task` | 🔴 لسه مفتوح — غير مجدولة، ويحتاج قرار نطاق صريح (PDPL/GDPR) قبل أي بناء فعلي (راجع `.claude/reports/saas-nonexistent-methods-investigation-session-log.md` §4) |
