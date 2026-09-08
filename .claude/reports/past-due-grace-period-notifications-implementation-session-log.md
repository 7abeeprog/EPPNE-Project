# جلسة تنفيذ — فترة سماح PAST_DUE + تنبيهات (خيار ب، مُوافَق عليه)

**بدأ التسجيل:** 2026-09-08
**الحالة:** ✅ **الجلسة مكتملة بالكامل.** التنفيذ الثابت (كود) + إصلاح ضيق لـ
`process_auto_renewals_task` (`backlog-process-auto-renewals-task-constructor-typeerror`) +
اختبار حي كامل بمرحلتين: الخطوة 1 (تأكيد الإصلاح، بلا `TypeError`) والخطوة 2 (المراحل الثلاث
لـ`check_past_due_subscriptions_task` — يوم 0/2/3، بالإشعارات + تحويل `EXPIRED` + الـidempotency،
كلها ✅ ناجحة حيًا). راجع §6 و§7 تحت.

**نطاق الجلسة:** تنفيذ 3 بنود مُحدَّدة بالضبط (خيار ب من جلسة التصميم):
1. تفعيل فرع `PAST_DUE` الميت في `can_access_service`.
2. مهمة Celery جديدة `check_past_due_subscriptions_task` — تنبيهات مرحلية (يوم 0 / يوم 2 / يوم 3).
3. جدولتها في `beat_schedule`.

**ممنوع صراحةً ولم يُلمَس:** `send_notification_task` نفسها، وأي كود يخص بندي backlog
`backlog-notification-delivery-stub-empty-non-inapp-channels` و
`backlog-saas-tasks-calling-nonexistent-methods` (راجع `PROGRESS_LOG.md` [2026-09-08]).

---

## 1) تفعيل الفرع الميت — `get_active_subscription_via_plan_access`

**الملف:** `app/domains/saas/repository.py` — دالة `get_active_subscription_via_plan_access`
(كانت سطر 154-176، الآن أطول بسبب توثيق إضافي في الـdocstring).

**التغيير الوحيد الفعلي (سطر واحد):**

```diff
-                    TenantSubscription.status.in_(["ACTIVE", "TRIAL"])
+                    TenantSubscription.status.in_(["ACTIVE", "TRIAL", "PAST_DUE"])
```

بهذا التغيير فقط، فرع `PAST_DUE` الموجود بالفعل في `can_access_service` (سطر 342-350 —
لم يُلمَس، منطقه صحيح من الأساس) بقى قابل للوصول: أي اشتراك `PAST_DUE` هيترجّع من الاستعلام
الآن، وفحص `grace_period_end_date` هيشتغل فعليًا بدل ما يوصل أبدًا.

**`get_active_subscription` الشقيقة (repository.py:134-152) — لم تُلمَس عمدًا**، بنفس القصور
بالضبط (`status.in_(["ACTIVE","TRIAL"])` بلا `PAST_DUE`). خارج نطاق اليوم كما طُلب — تُستخدَم
في `create_subscription` (منع اشتراك مزدوج) و`get_services_with_access` (شاشة "خدماتي")، مش في
`can_access_service`. بند منفصل لو احتجنا نظهر `PAST_DUE` في شاشة "خدماتي" لاحقًا.

---

## 2) مهمة Celery جديدة — `check_past_due_subscriptions_task`

### أ) دالة الخدمة: `SaaSControlService.check_past_due_subscriptions`

**الملف:** `app/domains/saas/service.py` — مُضافة مباشرة بعد `process_auto_renewals`
(قبل قسم "4. صلاحيات الوصول").

**قرار تصميمي مهم اتخذته أثناء التنفيذ (يستحق التوثيق صراحةً):** لاحظت إن
`process_auto_renewals` بتقع فعليًا على `self.tenant_id` لو اتنادت بـ`tenant_id=None`
(`target_tenant = tenant_id if tenant_id is not None else self.tenant_id`) — يعني مفيش طريقة
حقيقية تخليها تفحص **كل** المستأجرين في نداء واحد إلا لو `self.tenant_id` نفسه بيمثل "الكل"
(وهو مش بيمثل ده). لتفادي نفس القصور في المهمة الجديدة، صممت `check_past_due_subscriptions`
بشكل مختلف عمدًا: `tenant_id: Optional[int] = None` بيتمرر **مباشرة** لـ
`get_past_due_subscriptions(tenant_id)` بلا أي fallback لـ`self.tenant_id`، وكل عملية على مستوى
الاشتراك الفردي (تحديث الحالة، جلب مدير التينانت) بتستخدم `sub.tenant_id` الحقيقي (تينانت
الاشتراك نفسه) مش `self.tenant_id`. النتيجة: الدالة بتشتغل صح بغض النظر عن قيمة `tenant_id`
اللي اتبنى بيها الـ`SaaSControlService` instance — لم يُعدَّل `process_auto_renewals` نفسها
(خارج النطاق المطلوب اليوم)، فقط الدالة الجديدة اتصممت بطريقة تتفادى نفس الفخ.

```python
async def check_past_due_subscriptions(self, tenant_id: Optional[int] = None) -> List[dict]:
    from app.domains.communications.service import CommunicationsService

    subscriptions = await self.repo.get_past_due_subscriptions(tenant_id)
    comm_service = CommunicationsService(self.db)
    now = datetime.now(timezone.utc)
    results = []

    for sub in subscriptions:
        grace_end = sub.grace_period_end_date
        if grace_end is None:
            logger.warning(f"Past-due subscription {sub.id} has no grace_period_end_date - skipped")
            continue

        remaining = grace_end - now
        if remaining <= timedelta(0):
            day_number = 3
        elif remaining <= timedelta(days=1):
            day_number = 2
        else:
            day_number = 0

        sub_id = cast(int, sub.id)
        sub_tenant_id = cast(int, sub.tenant_id)

        try:
            admin_id = await self._get_tenant_admin_id(sub_tenant_id)

            if day_number == 0:
                title = "تأخر الدفع"
                body = "دفعتك اتأخرت، عندك 3 أيام سماح."
            elif day_number == 2:
                title = "تنبيه: فترة السماح توشك على الانتهاء"
                body = "باقي يوم واحد بس على انتهاء فترة السماح."
            else:
                title = "تم إيقاف الخدمة"
                body = "الخدمة اتوقفت بسبب انتهاء فترة السماح."

            await comm_service.send_notification(
                user_id=admin_id, title=title, body=body,
                data={"subscription_id": sub_id, "day": day_number},
                channel="IN_APP",
                idempotency_key=f"SUB-PASTDUE-{sub_id}-{day_number}",
            )

            if day_number == 3:
                await self.repo.update_subscription_status(sub_id, sub_tenant_id, "EXPIRED")
                await self.db.commit()

            results.append({"subscription_id": sub_id, "day": day_number, "status": "NOTIFIED"})

        except Exception as e:
            logger.error(f"Past-due check failed: subscription {sub_id} - {str(e)}")
            results.append({"subscription_id": sub_id, "status": "FAILED", "error": str(e)})

    return results
```

**منطق تحديد المرحلة (`day_number`):** مبني على `remaining = grace_end - now`، مش على عدّاد
أيام منفصل مُخزَّن — بيستنتج المرحلة من `grace_period_end_date` نفسها (المضروبة فعليًا 3 أيام
في `process_auto_renewals`، بلا تغيير هنا):
- `remaining <= 0` → يوم 3 (انتهت الفترة فعلاً).
- `0 < remaining <= 1 يوم` → يوم 2 (يوم واحد أو أقل متبقي).
- `remaining > 1 يوم` → يوم 0 (لسه بداية الفترة، أكتر من يوم متبقي).

**لماذا التصميم ده آمن من التكرار حتى لو الـtask اتنفذت أكتر من مرة على نفس الاشتراك في نفس
المرحلة:** `idempotency_key=f"SUB-PASTDUE-{sub_id}-{day_number}"` — `CommunicationsService.
send_notification` بتفحص `idempotency_key` أولًا (`get_notification_by_idempotency`) وترجع
الصف الموجود بدل إرسال تاني لو لقت تطابق. يعني حتى لو الاشتراك فضل في نطاق "يوم 0" (`remaining
> 1 يوم`) لمدة يومين متتاليين من التشغيل اليومي، الإشعار هيتبعت مرة واحدة بس.

**المستقبِل:** `await self._get_tenant_admin_id(sub_tenant_id)` — نفس الدالة والنمط
المُستخدَم فعليًا في `process_auto_renewals` (`payer_id = await self._get_tenant_admin_id
(target_tenant)`)، بترجع `AcademyTenant.admin_id` — نفس الشخص اللي بيدفع فعليًا.

**قناة الإشعار:** `channel="IN_APP"` حصريًا، كما طُلب — القناة الكاملة فعليًا الوحيدة حاليًا
(راجع بند backlog القنوات المُعطَّلة، لم يُلمَس هنا).

**فشل فردي مايوقفش باقي الاشتراكات:** `try/except` حول كل اشتراك على حدة (نفس نمط
`process_auto_renewals`) — لو `_get_tenant_admin_id` رمى `NotFoundError` (تينانت محذوف مثلًا)
أو أي استثناء تاني، بيتسجل بـ`logger.error` ويُضاف كـ`FAILED` في النتائج، والحلقة بتكمل لباقي
الاشتراكات.

### ب) دالة الـrepository: `get_past_due_subscriptions`

**الملف:** `app/domains/saas/repository.py` — مُضافة مباشرة بعد `get_subscriptions_for_renewal`.

```python
async def get_past_due_subscriptions(self, tenant_id: Optional[int] = None) -> List[TenantSubscription]:
    query = select(TenantSubscription).where(TenantSubscription.status == "PAST_DUE")
    if tenant_id is not None:
        query = query.where(TenantSubscription.tenant_id == tenant_id)
    result = await self.db.execute(query)
    return list(result.scalars().all())
```

بلا فلتر `tenant_id` افتراضيًا (`None` = كل المستأجرين) — نفس نمط `get_subscriptions_for_renewal`
بالضبط في شكل التوقيع، لكن بمعنى مختلف: هنا `None` معناها فعليًا "كل التينانتس" في كل الحالات
(مش بديل عن `self.tenant_id` كما في `process_auto_renewals`).

### ج) مهمة Celery: `check_past_due_subscriptions_task`

**الملف:** `app/tasks/saas_tasks.py` — مُضافة كقسم "7" جديد في نهاية الملف (بعد
`cleanup_cancelled_subscriptions_task`)، بنفس بنية/إعدادات `process_auto_renewals_task` بالحرف
(`bind=True, max_retries=3, default_retry_delay=3600, acks_late=True, time_limit=1800,
soft_time_limit=1500`).

```python
@celery_app.task(
    name="saas.check_past_due_subscriptions",
    bind=True, max_retries=3, default_retry_delay=3600,
    acks_late=True, time_limit=1800, soft_time_limit=1500,
)
def check_past_due_subscriptions_task(self):
    try:
        async def _run():
            async with SessionLocal() as db:
                service = SaaSControlService(db, 0)
                results = await service.check_past_due_subscriptions()
                await db.commit()
                ...
        result = _run_async(_run())
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"❌ Past-due subscriptions check task failed: {str(e)}")
        raise self.retry(exc=e, countdown=3600)
```

**⚠️ ملاحظة صريحة عن `SaaSControlService(db, 0)`:** `SaaSControlService.__init__` بياخد
`tenant_id: int` **إجباري بلا default**. المهام التانية في نفس الملف (`process_auto_renewals_task`
وغيرها) بتستدعي `SaaSControlService(db)` **بدون** `tenant_id` إطلاقًا — اكتشاف جانبي جديد أثناء
كتابة هذه المهمة، **غير موثَّق سابقًا في أي تقرير**: هذا هيرمي `TypeError: missing 1 required
positional argument` فور محاولة الإنشاء، **قبل حتى الوصول لأي منطق داخل الدالة**. يعني
`process_auto_renewals_task` (المهمة اللي مصدر تحويل `ACTIVE→PAST_DUE` أصلًا، §2 من تقرير
التحقيق) على الأرجح **بتفشل حاليًا في كل تنفيذ** لو الـworker شغّال فعليًا — نقطة لم تُختبَر حيًا
في هذه الجلسة ولا الجلسة اللي قبلها (راجع قسم "خارج النطاق" تحت).

لتفادي تكرار نفس الخطأ في المهمة الجديدة، استخدمت `SaaSControlService(db, 0)` — نمط موجود
بالفعل ومُستخدَم في الكود الحي (`app/domains/saas/router.py:273`، مع تعليق أصلي "نمرر
tenant_id=0 مؤقتاً") لحالة "service instance مش مربوط بتينانت واحد بعينه". بعكس استخدام
`router.py:273` (اللي `trigger_renewals` بتاعه بيقع فعليًا على `self.tenant_id=0` كـfallback،
فبيفشل صامتًا/فاضي لو اتنادى بلا `tenant_id` — بج قائم منفصل)، الـ`0` هنا **آمن فعليًا** لأن
`check_past_due_subscriptions` (§أ أعلاه) مصممة عمدًا تتجاهل `self.tenant_id` بالكامل وتستخدم
`sub.tenant_id` الحقيقي لكل اشتراك.

### د) لماذا `process_auto_renewals_task` (`SaaSControlService(db)` بلا tenant_id) خارج نطاق
التصحيح اليوم رغم اكتشافه أثناء التنفيذ

هذا اكتشاف **جديد** (مش من بندي الـbacklog المُوثَّقين [2026-09-08] صباحًا — دول كانوا عن دوال
غير موجودة وقنوات إشعار معطَّلة، مش عن `TypeError` في الـconstructor). طبقًا للتعليمة الصريحة
لهذه الجلسة (3 بنود محددة بالضبط، وممنوع لمس أي حاجة تانية)، **لم يُلمَس** `process_auto_renewals_task`
ولا أي مهمة تانية موجودة في `saas_tasks.py`. يُوصى بفتح بند backlog رابع منفصل له في جلسة
توثيق قادمة (نفس نمط الجلسة اللي وثّقت البندين السابقين) — **لم يُضَف لـ`PROGRESS_LOG.md` في
هذه الجلسة** لأنها جلسة تنفيذ كود، مش توثيق، وطلب المستخدم كان محدد بثلاث بنود تنفيذ فقط.

---

## 3) الجدولة — `beat_schedule`

**الملف:** `app/core/celery_config.py`، مُضافة مباشرة بعد `process-auto-renewals`:

```python
"check-past-due-subscriptions": {
    "task": "saas.check_past_due_subscriptions",
    "schedule": crontab(hour=3, minute=0),  # 3:00 AM يومياً (بعد process-auto-renewals بساعة)
    "options": {"queue": "saas"},
},
```

الترتيب الزمني كما طُلب: `process-auto-renewals` (2 صباحًا — يحوّل `ACTIVE→PAST_DUE`) ثم
`check-past-due-subscriptions` (3 صباحًا — يفحص وينبّه/ينهي `PAST_DUE`)، على نفس الـqueue
`"saas"` الموجودة بالفعل.

---

## 4) الملفات المُعدَّلة (ملخص)

| الملف | التغيير |
|---|---|
| `app/domains/saas/repository.py` | `get_active_subscription_via_plan_access`: إضافة `"PAST_DUE"` لـ`status.in_`. + دالة جديدة `get_past_due_subscriptions`. |
| `app/domains/saas/service.py` | دالة جديدة `check_past_due_subscriptions` (بعد `process_auto_renewals`). |
| `app/tasks/saas_tasks.py` | مهمة Celery جديدة `check_past_due_subscriptions_task` (قسم 7، نهاية الملف). |
| `app/core/celery_config.py` | إدخال `beat_schedule` جديد `check-past-due-subscriptions` (3 صباحًا). |

**لم يُلمَس:** `get_active_subscription` (الشقيقة)، `send_notification_task`، `celery_app.py`،
أي دالة من الأربعة الناقصة (`generate_monthly_invoices`, `check_and_expire_trials`,
`send_trial_expiry_reminders`, `cleanup_cancelled_subscriptions`)، `process_auto_renewals_task`
أو أي مهمة Celery موجودة أخرى.

**فحص صحة الصياغة فقط (لا تنفيذ حي):**

```
python -m py_compile app/domains/saas/repository.py app/domains/saas/service.py \
  app/tasks/saas_tasks.py app/core/celery_config.py
→ SYNTAX_OK
```

---

## 5) الاختبار الحي — تحديث نهائي

الاختبار الحي **اكتمل بالكامل** عبر جلستين متتاليتين: الخطوة 1 (§6 تحت — كشفت
`backlog-process-auto-renewals-task-constructor-typeerror` وأوقفت الجلسة للسؤال، ثم الإصلاح
الضيق §6-د)، والخطوة 2 (§7 تحت — المراحل الثلاث لـ`check_past_due_subscriptions_task`، كلها
ناجحة).

---

## 6) الاختبار الحي — الخطوة 1 (أولوية قصوى): تأكيد `process_auto_renewals_task`

**بيئة الاختبار:** `venv/Scripts/python.exe` (Python 3.12.10)، DB حقيقية متصلة
(`postgresql+asyncpg://eppne:***REDACTED***@127.0.0.1:5435/eppne_v2` — تأكَّد الاتصال حيًا عبر
`docker compose ps` → `eppne_db` بحالة `Up 2 weeks (healthy)`، ومنفذ 5435 مفتوح فعليًا). صفر
تعديل كود في هذه الخطوة — فحص/تشغيل فقط.

### أ) استدعاء مباشر — `SaaSControlService(db)` بلا `tenant_id`

```python
from app.domains.saas.service import SaaSControlService
class FakeDB: pass
svc = SaaSControlService(FakeDB())
```

**النتيجة الفعلية:**
```
TypeError: SaaSControlService.__init__() missing 1 required positional argument: 'tenant_id'
```

### ب) تشغيل الـtask نفسها فعليًا — `process_auto_renewals_task.run()`

استدعاء مباشر لجسم المهمة (نفس الكود اللي هيتنفذ لو الـCelery beat/worker شغّالين ونادوا
عليها فعليًا الساعة 2 صباحًا) عبر `.run()` — بيا تنفيذ جسم الدالة بالضبط، بما فيه منطق
`self.retry`.

**النتيجة الفعلية (traceback كامل):**

```
❌ Auto-renewals task failed: SaaSControlService.__init__() missing 1 required positional argument: 'tenant_id'
Traceback (most recent call last):
  ...
  File "app/tasks/saas_tasks.py", line 96, in process_auto_renewals_task
    raise self.retry(exc=e, countdown=3600)
  File "celery/app/task.py", line 720, in retry
    raise_with_context(exc or Retry('Task can be retried', None))
  File "app/tasks/saas_tasks.py", line 90, in process_auto_renewals_task
    result = _run_async(_run())
  File "app/tasks/saas_tasks.py", line 65, in _run
    service = SaaSControlService(db)
              ^^^^^^^^^^^^^^^^^^^^^^
TypeError: SaaSControlService.__init__() missing 1 required positional argument: 'tenant_id'
```

### ج) الخلاصة — التأكيد إيجابي 100%

**البج مؤكَّد حيًا، مش نظريًا.** `process_auto_renewals_task` — المصدر التلقائي الوحيد
الموثَّق حاليًا للتحويل `ACTIVE → PAST_DUE` — **بترمي `TypeError` فورًا في كل تنفيذ فعلي**، عند
سطر `service = SaaSControlService(db)` (`saas_tasks.py:65`)، **قبل** أي وصول لأي منطق داخل
`process_auto_renewals()` نفسها. حتى `self.retry(...)` في بلوك `except` الخاص بالمهمة مش بيغطي
المشكلة — بيعيد رفع نفس الـ`TypeError` (لأن السياق هنا خارج broker/worker حقيقي، فـCelery
بيرجّع للاستثناء الأصلي بدل جدولة إعادة محاولة فعلية؛ وحتى لو كان جوّه worker حقيقي، إعادة
المحاولة 3 مرات بفاصل ساعة مش هتغيّر النتيجة — نفس الكود، نفس الخطأ في كل محاولة).

**الأثر المؤكَّد الآن (مش "محتمل" بعد النهارده):** التحويل التلقائي `ACTIVE → PAST_DUE` **مش
بيحصل فعليًا في الإنتاج حاليًا**، بغض النظر عن وجود الكود الكامل والجدولة الصحيحة
(`beat_schedule` 2 صباحًا). أي اشتراك `PAST_DUE` موجود فعليًا في قاعدة البيانات النهارده
لازم يكون اتحط يدويًا أو عبر مسار تاني غير `process_auto_renewals_task` — مش نتيجة تشغيل
تلقائي ناجح.

**التوقف هنا كما طُلب صراحةً — الخطوة 2 (seed اشتراك `PAST_DUE` واختبار
`check_past_due_subscriptions_task`) لم تبدأ، بانتظار قرار المستخدم صراحةً:** هل نُصلح
`process_auto_renewals_task` (وعلى الأرجح باقي المهام الخمسة في نفس الملف بنفس القصور —
`generate_monthly_invoices_task`, `check_expired_trials_task`,
`send_trial_expiry_reminders_task`, `cleanup_cancelled_subscriptions_task`) أولًا رغم إنه
خارج نطاق اليوم الأصلي، أم نكمل للخطوة 2 (seed يدوي مباشر في DB، بدون المرور بالمهمة
المكسورة) عشان نختبر `check_past_due_subscriptions_task` بمعزل تام — بالضبط زي ما نص الشرط
البديل في التعليمة ("لو process_auto_renewals_task شغالة فعلًا... كمّل للخطوة 2") لكن هنا
الشرط **مش متحقق** (هي مش شغالة)، فالتعليمة الصريحة تقول نقف ونسأل، مش نكمل تلقائيًا.

### د) القرار — إصلاح ضيق (`process_auto_renewals_task` بس)، وإعادة الخطوة 1

المستخدم قرر: إصلاح ضيق لمكان واحد فقط — `SaaSControlService(db)` → `SaaSControlService(db, 0)`
داخل `process_auto_renewals_task` حصريًا (`app/tasks/saas_tasks.py:69` بعد التعديل). **لم
تُلمَس** `generate_monthly_invoices_task`/`check_expired_trials_task` (بند backlog منفصل تمامًا
— دوال غير موجودة، مش نفس مشكلة الـconstructor) ولا `send_trial_expiry_reminders_task`/
`cleanup_cancelled_subscriptions_task`.

**التحقق المطلوب قبل التعديل (بنفس دقة تحقيق `check_past_due_subscriptions`):** قراءة
`process_auto_renewals` (service.py:266-268) تُظهر:

```python
async def process_auto_renewals(self, tenant_id: Optional[int] = None) -> List[dict]:
    target_tenant = tenant_id if tenant_id is not None else self.tenant_id
    subscriptions = await self.repo.get_subscriptions_for_renewal(target_tenant)
```

**⚠️ تصحيح دقيق لفرضية التعليمة:** الدالة **بتاخد `tenant_id` كـparameter منفصل فعلًا**، لكنها
**مش بتتجاهل `self.tenant_id` بالكامل** — لو اتنادت بـ`tenant_id=None` (وهو بالظبط اللي بيحصل،
لأن `saas_tasks.py` بينادي `service.process_auto_renewals()` **بلا أي argument**)، بتقع على
`self.tenant_id` كـfallback. هذا **يختلف عن** `check_past_due_subscriptions` اللي بنيتها
اليوم عمدًا لتتجاهل `self.tenant_id` بالكامل وتمرر `tenant_id` مباشرة لـ`get_past_due_
subscriptions` بلا fallback. يعني: بعد التعديل لـ`(db, 0)`، `target_tenant` هيبقى **دايمًا
= 0** (مش `None`، ومش "كل التينانتس") — و`get_subscriptions_for_renewal(0)` هيفلتر
`tenant_id == 0` تحديدًا. تأكَّد بالاستعلام المباشر (§د-1 تحت) إن **مفيش تينانت بـid=0**
في القاعدة، فالنتيجة العملية: التعديل بيصلح الـ`TypeError` (الهدف المطلوب فعلًا اليوم)، لكن
**مايخليش** `process_auto_renewals_task` تعالج تينانتات حقيقية — هتفضل ترجع نتيجة فاضية
(`total: 0`) طالما اتنادت بلا `tenant_id` صريح، **بغض النظر** عن وجود اشتراكات حقيقية مستحقة
فعليًا لأي تينانت تاني. هذا **قصور مختلف تمامًا وأعمق** من الـ`TypeError` — قصور بنيوي في
طريقة استدعاء الدالة، مش في الـconstructor. تم توثيقه بصراحة تحت (§د-3) كاكتشاف جديد، **لم
يُصلَح اليوم** (خارج نطاق "الإصلاح الضيق" المطلوب صراحةً) — راجع أيضًا نفس القصور بالحرف في
`trigger_renewals` (service.py:525-528) المُوثَّق مسبقًا في §2ج.

**التعديل الفعلي المُطبَّق (سطر واحد + تعليق توضيحي):**

```diff
-                service = SaaSControlService(db)
+                # [2026-09-08] كان SaaSControlService(db) بلا tenant_id — TypeError مؤكَّد
+                # حيًا في كل تنفيذ (راجع backlog-process-auto-renewals-task-constructor-
+                # typeerror في PROGRESS_LOG.md). tenant_id=0 نفس نمط
+                # check_past_due_subscriptions_task/router.py:273 الإداري.
+                service = SaaSControlService(db, 0)
```

فحص `py_compile` نجح فورًا. **لم يُلمَس** أي سطر تاني في الملف — الـ4 نداءات المتبقية
(`generate_monthly_invoices_task`, `check_expired_trials_task`,
`send_trial_expiry_reminders_task`, `cleanup_cancelled_subscriptions_task`) لسه
`SaaSControlService(db)` بلا `tenant_id`، مؤكَّد بـ`grep` بعد التعديل.

### د-1) إعادة اختبار الخطوة 1 — تأكيد الإصلاح

**استدعاء مباشر:**
```python
svc = SaaSControlService(FakeDB(), 0)
# → NO ERROR - instantiated: <...> tenant_id= 0
```

**تشغيل المهمة كاملة (`process_auto_renewals_task.run()`) — ضد نفس DB الحية:**

أول محاولة (بلا `import app.main`) طلعت `sqlalchemy.exc.InvalidRequestError` مختلف تمامًا
(`AcademyTenant` مش مُسجَّلة في الـmapper registry) — **مش بج إنتاجي**، ده أثر جانبي لتشغيل
سكريبت معزول بلا تحميل كل الدومينات (بعكس التطبيق الحقيقي اللي بيحمّل كل الـ34 راوتر عبر
`app.main` عند الإقلاع، فكل الموديلات بتتسجل تلقائيًا). بعد `import app.main` أول سطر
(تسجيل كل الموديلات، بلا تشغيل uvicorn فعلي):

```
TASK RESULT (no exception): {'status': 'success', 'result':
  {'status': 'success', 'total': 0, 'successful': 0, 'failed': 0, 'skipped': 0, 'details': []}}
```

**✅ صفر `TypeError` — الإصلاح المطلوب نجح ومؤكَّد حيًا.** الـ`Total: 0` **متوقَّع وصحيح في
اللحظة دي**، مش أثر جانبي مقلق: تحقَّق مباشرةً بـSQL خام إن `(أ)` مفيش تينانت بـid=0 في
`academy_tenants`، و`(ب)` عدد الاشتراكات المستحقة فعليًا للتجديد **عبر كل التينانتات** (بلا أي
فلتر tenant_id) = **0 كمان** في هذه اللحظة تحديدًا — يعني مفيش نشاط حقيقي فات علينا في هذا
الاختبار بالذات، والنتيجة الفاضية مش دليل كافٍ لوحدها على وجود/غياب قصور "تينانت 0". القصور
البنيوي (§د أعلاه) **حقيقة ثابتة بالقراءة المباشرة للكود + تأكيد "مفيش تينانت id=0"**، مش محتاج
seed إضافي لإثباته — لكنه **لم يُختبَر حيًا بوجود اشتراك حقيقي مستحق فعلي** (خارج نطاق الإصلاح
الضيق المطلوب اليوم، فلم يُنفَّذ هذا الاختبار الإضافي).

### د-2) اكتشاف جديد غير مُصلَح — توصية بند backlog خامس (لم يُضَف لـ`PROGRESS_LOG.md` اليوم)

`process_auto_renewals_task` بعد الإصلاح الضيق **بتشتغل بلا كراش، لكن هتفضل ترجع نتيجة فاضية
دايمًا** طالما استدعاء `service.process_auto_renewals()` في نفس الملف فاضل بلا `tenant_id`
صريح (لأن `target_tenant` بيقع على `self.tenant_id=0` دايمًا، وصفر تينانت حقيقي بـid=0). يعني
التحويل التلقائي `ACTIVE → PAST_DUE` **لسه مش بيحصل فعليًا للتينانتات الحقيقية** رغم اختفاء
الكراش — قصور مختلف عن `backlog-process-auto-renewals-task-constructor-typeerror` (اللي بقى
✅ اتصلح النهارده)، يستحق بند backlog منفصل خامس (مثلًا
`backlog-process-auto-renewals-task-tenant-zero-noop`) في جلسة توثيق قادمة. **لم يُضَف
لـ`PROGRESS_LOG.md` في هذه الجلسة** — طلب المستخدم كان إصلاح ضيق + اختبار، مش جلسة توثيق
backlog جديدة.

---

## 7) الاختبار الحي — الخطوة 2: المراحل الثلاث لـ`check_past_due_subscriptions_task`

بما إن السبب اللي أوقف الجلسة (§6ج) اتصلح (§6-د)، كمّلت مباشرة للخطوة 2 كما طلب المستخدم —
بلا انتظار تعليمة تالتة منفصلة.

### أ) إعداد الاختبار

سكريبت throwaway مستقل (`test_past_due_stages.py`، في الـscratchpad — مش جزء من المشروع، صفر
أثر على الكود)، بنفس منهجية `tests/test_saas_cancel_subscription_silent_write.py` الموجودة
بالفعل (`_seed_active_subscription` — زرع عبر `SaaSRepository` ORM مباشرة، `tenant_id=1`
"Local Test Tenant" الموثَّق في `throwaway-test-users.md`، تنظيف كامل في `finally`). تأكَّد قبل
البدء عبر SQL مباشر إن **صفر اشتراكات `PAST_DUE` موجودة فعليًا** في القاعدة (عزل تام لنتائج
الاختبار)، وإن تينانت 1 له `admin_id=1` (المستقبِل المتوقَّع للإشعارات).

**زُرع:** `service_id=116`, `plan_id=119`, `subscription_id=137` — `tenant_id=1`,
`status="PAST_DUE"`, `grace_period_end_date=now+3 أيام` (بداية المرحلة "يوم 0").

**تشغيل المهمة فعليًا** عبر `check_past_due_subscriptions_task.run()` (نفس أسلوب الخطوة 1) —
مع تحقق مستقل بعد كل استدعاء من جدول `notifications` عبر `SessionLocal()` جديدة (بلا الاعتماد
على الـsession اللي نفَّذت المهمة، بنفس منهجية "قراءة مستقلة" المُستخدَمة في اختبارات
`silent-write` السابقة بالمشروع).

⚠️ **ملاحظة تقنية عن سكريبت الاختبار نفسه (مش عن الكود المُنفَّذ):** كل استدعاء `asyncio.run()`
منفصل بيفتح/يقفل event loop جديد، واتصالات `asyncpg` المُجمَّعة (connection pool) في `engine`
المركزي مربوطة بالـloop اللي اتعمل بيه — فاحتجت `engine.dispose()` بين كل استدعاء لتفادي
"Event loop is closed". هذا تفصيلة خاصة بسكريبت اختبار معزول بينادي `asyncio.run()` أكتر من
مرة في نفس العملية — **مش موجود في الاستخدام الحقيقي** (Celery worker بيفتح loop واحد طول عمره
عبر `_run_async`، فمش متأثر). أيضًا، `logger.info`/`logger.error` اللي فيها إيموجي (✅/❌) كانت
بترمي `UnicodeEncodeError` على الـconsole المحلي (codepage `cp1256` الافتراضي على Windows) —
**ده أثر بيئة تطوير محلي فقط** (بيئات الإنتاج الحاوية عادة UTF-8 افتراضيًا)، ملحوظة هامشية غير
مرتبطة بمنطق الكود، لم يُفتح لها بند backlog (خارج نطاق اليوم، وعلى الأرجح غير قابل لإعادة
الإنتاج في بيئة إنتاج حقيقية).

### ب) نتائج المراحل الثلاث — كاملة، من سجل التشغيل الفعلي

| المرحلة | `grace_period_end_date` | نتيجة المهمة (`day`) | صف `notifications` جديد؟ | حالة الاشتراك بعدها |
|---|---|---|---|---|
| يوم 0 (أول تشغيلة) | الآن + 3 أيام | `day: 0, status: NOTIFIED` | ✅ نعم — `id=27`, `idempotency_key=SUB-PASTDUE-137-0` | `PAST_DUE` (بلا تغيير) |
| يوم 0 (تشغيلة تانية، نفس النافذة) | (بلا تغيير) | `day: 0, status: NOTIFIED` | **❌ لأ — نفس العدد (1 صف)** | `PAST_DUE` |
| يوم 2 | الآن + 12 ساعة | `day: 2, status: NOTIFIED` | ✅ نعم — `id=28`, `idempotency_key=SUB-PASTDUE-137-2` (إجمالي 2 صف) | `PAST_DUE` (بلا تغيير — صح، يوم 2 مش هيّنهي الاشتراك) |
| يوم 2 (تشغيلة تانية، نفس النافذة) | (بلا تغيير) | — | **❌ لأ — نفس العدد (2 صف)** | `PAST_DUE` |
| يوم 3 | الآن − ساعة (انتهت) | `day: 3, status: NOTIFIED` | ✅ نعم — `id=29`, `idempotency_key=SUB-PASTDUE-137-3` (إجمالي 3 صفوف) | **`EXPIRED`** ✅ |
| بعد الانتهاء (تشغيلة تالتة) | (بلا تغيير) | `total: 0` (مفيش `PAST_DUE` تاني يتفحص) | **❌ لأ — نفس العدد (3 صفوف)** | `EXPIRED` (مستقر) |

**تفاصيل صفوف `notifications` الثلاثة (قراءة مستقلة من الجدول، `channel=IN_APP` لكل الثلاثة،
`user_id=1` = `admin_id` تينانت 1 كما هو متوقَّع من `_get_tenant_admin_id`):**

```
id=27  idempotency_key=SUB-PASTDUE-137-0  title="تأخر الدفع"
id=28  idempotency_key=SUB-PASTDUE-137-2  title="تنبيه: فترة السماح توشك على الانتهاء"
id=29  idempotency_key=SUB-PASTDUE-137-3  title="تم إيقاف الخدمة"
```

(النصوص العربية ظهرت مشوَّهة/mojibake في الطرفية المحلية أثناء التشغيل بسبب `cp1256` — أثر
عرض طرفية بحت، مش تلف بيانات: القيم مصدرها literals عربية صحيحة UTF-8 في الكود المصدري
(`service.py`)، وasyncpg/Postgres بيخزّنوا UTF-8 دايمًا بغض النظر عن codepage الطرفية —
`idempotency_key`/`id`/العدد/التوقيت كلها تأكَّدت نظيفة وصحيحة 100%، وهي الدليل الحاسم هنا،
مش النص المعروض.)

### ج) تأكيد الشروط الثلاثة المطلوبة صراحةً

- **(أ) وصول الإشعار الصحيح، تحقق من صف `notifications`:** ✅ مؤكَّد — 3 صفوف مستقلة، وحدة لكل
  مرحلة، بـ`idempotency_key` مطابق للتصميم بالضبط (`SUB-PASTDUE-{sub_id}-{day}`)، ومستقبِل
  صحيح (`user_id=1`، مدير تينانت 1).
- **(ب) تحويل `EXPIRED` عند يوم 3:** ✅ مؤكَّد — `status` اتحول من `PAST_DUE` إلى `EXPIRED`
  بالظبط عند تشغيلة يوم 3، وفضل مستقر (`EXPIRED`) في التشغيلة اللي بعدها كمان (مفيش رجوع
  عرضي لـ`PAST_DUE`).
- **(ج) الـidempotency (تشغيل نفس المرحلة مرتين ما يبعتش إشعار مكرر):** ✅ مؤكَّد لمرحلتين
  منفصلتين (يوم 0، يوم 2) — تشغيل كل مرحلة مرتين متتاليتين نتج عنه **نفس عدد الصفوف بالظبط** في
  الحالتين، صفر تكرار. (يوم 3 اتأكَّد إضافيًا بطريقة مكافئة: التشغيلة اللي بعد التحويل لـ
  `EXPIRED` رجعت `total: 0` — الاشتراك خرج من نطاق الاستعلام تمامًا، فمفيش فرصة لتكرار حتى
  نظريًا.)

### د) التنظيف

`finally` block في السكريبت شغَّل الحذف (`notifications` + `TenantSubscription` +
`ServicePlan` + `ServiceCatalog` الخاصين بالاختبار) وأكَّد `"CLEANED UP throwaway rows."` في
آخر السجل — **صفر بيانات throwaway متبقية في القاعدة** بعد الجلسة. سكريبت الاختبار نفسه في
مجلد الـscratchpad المؤقت (خارج المشروع تمامًا)، لم يُضَف لأي مكان في `eppne-backend/`.

---

## 8) خلاصة نهائية للجلسة كاملة

| البند | الحالة |
|---|---|
| 1. تفعيل فرع `PAST_DUE` الميت (`can_access_service`) | ✅ منفَّذ (كود فقط، لم يُختبَر حيًا في هذه الجلسة — خارج طلب اليوم) |
| 2. `check_past_due_subscriptions_task` + جدولتها | ✅ منفَّذ **ومُختبَر حيًا بالكامل** (3 مراحل، 3 شروط تحقق) |
| 3. `process_auto_renewals_task` — إصلاح `TypeError` | ✅ مُصلَح ومُختبَر حيًا (اكتشاف اليوم، خارج الخطة الأصلية) |
| اكتشاف جديد غير مُصلَح | 🔴 `process_auto_renewals_task` بعد الإصلاح بترجع نتيجة فاضية دايمًا (`tenant_id=0` سنتينل بلا تينانت حقيقي بهذا الـid) — يحتاج بند backlog خامس منفصل، لم يُفتح اليوم |

---

## 9) جلسة تانية — إصلاح `tenant_id=0`-noop "بالطريقة الصح"، واكتشاف جديد أعمق (لم يُحسم بعد)

### أ) الخطوة 1 — فحص كل نقاط الاستدعاء قبل أي تعديل

```
grep -rn "process_auto_renewals(\|trigger_renewals(" --include="*.py" .
```

**3 نقاط استدعاء فقط في المشروع بالكامل:**

| الموقع | القصد | بيعتمد على الـfallback؟ |
|---|---|---|
| `app/tasks/saas_tasks.py:71` — `service.process_auto_renewals()` | Celery beat يومي — **قصده كل التينانتات** | نعم (`tenant_id` مش متمرر إطلاقًا) |
| `app/domains/saas/router.py:265-274` — `POST /admin/trigger-renewals` (`tenant_id: Optional[int] = Query(None, ...)`, `get_current_superuser`) | admin endpoint — `tenant_id` **اختياري صراحةً** في الـquery param | نعم لو الأدمن ماحددش `tenant_id` (الحالة الشائعة المتوقَّعة لـ"شغّل التجديد دلوقتي لكل حد") |
| `app/domains/saas/service.py:607-610` — `trigger_renewals` (بتنادي `process_auto_renewals(target)`) | نفس منطق الـfallback بالحرف: `target = tenant_id if tenant_id is not None else self.tenant_id` | نعم — **نفس القصور بالحرف**، عبر `router.py:273` (`SaaSControlService(db, 0)`) |

**الخلاصة: صفر استخدام حي بيعتمد على الـfallback (`self.tenant_id`) عمدًا لتحديد تينانت حقيقي
بعينه.** الاستخدام الوحيد اللي بيمرر `tenant_id` صريح وحقيقي هو `/admin/trigger-renewals?
tenant_id=5` (تينانت محدد فعليًا في الـquery) — ده **مش متأثر** بأي تعديل مقترح، لأن
`tenant_id is not None` بيفضل بيدّي الأولوية لأي قيمة مُمرَّرة صراحةً في كل الحالات. **باقي
كل الحالات** (الـtask بلا argument، والـendpoint بلا query param) قصدها الفعلي "كل
التينانتات"، مش "تينانت 0 الوهمي" — مطابق تمامًا لتوقُّع التعليمة. تم المتابعة للخطوة 2 بلا
توقف.

⚠️ **ملحوظة مهمة (توثيقية فقط، لم تُلمَس):** `trigger_renewals`/`router.py:273` عندهم **نفس
القصور بالحرف** ولسه غير مُصلَحين — التعليمة الصريحة لهذه الجلسة غطّت `process_auto_renewals`
(service.py) و`process_auto_renewals_task` (saas_tasks.py) بس. يعني `POST /admin/trigger-
renewals` **بلا** `tenant_id` query param لسه هيقع على نفس الـfallback المكسور (`self.
tenant_id=0`) ويرجع نتيجة فاضية — قصور منفصل لم يُطلَب إصلاحه اليوم، موصى بفتح بند backlog
له أو تضمينه في نفس الإصلاح لو حابب.

### ب) الخطوة 2 — التعديل

**`get_subscriptions_for_renewal` (repository.py) — لم تحتج أي تعديل:** كانت بالفعل تدعم
`tenant_id=None` كـ"بلا فلتر = كل التينانتات" (نفس نمط `get_past_due_subscriptions` بالضبط) —
القصور كان في طبقة الـservice فقط (`process_auto_renewals` بتحوّل `None` لـ`self.tenant_id`
قبل ما توصل للـrepository أصلًا).

**`process_auto_renewals` (service.py:266+) — التعديل الفعلي:**
- إزالة `target_tenant = tenant_id if tenant_id is not None else self.tenant_id`، وتمرير
  `tenant_id` مباشرة لـ`get_subscriptions_for_renewal(tenant_id)`.
- كل الاستخدامات الداخلية لـ`target_tenant` (`_get_tenant_admin_id`,
  `get_or_create_system_account`, `update_subscription` مرتين، `_generate_invoice`) اتبدّلت
  بـ`sub_tenant_id = cast(int, sub.tenant_id)` — تينانت الاشتراك الحقيقي، بنفس نمط
  `check_past_due_subscriptions` بالضبط.

**`process_auto_renewals_task` (saas_tasks.py:71) — التعديل الفعلي:**
```diff
-                results = await service.process_auto_renewals()
+                results = await service.process_auto_renewals(tenant_id=None)
```
(`SaaSControlService(db, 0)` نفسها لم تتغيّر — كما طُلب صراحةً.)

فحص `py_compile` نجح فورًا على الملفين.

### ج) الخطوة 3 — الاختبار الحي: اكتشاف جديد أعمق، **لم يُحسم**

**السياق:** بدل استخدام تينانت 0 الوهمي، زرعت اشتراكين حقيقيين **مستحقين فعليًا للتجديد**
تحت تينانت 1 (Local Test Tenant، `admin_id=1`، محفظة `MR_USDT=865.0` مؤكَّدة كافية):
- `sub_a` (id=138): خطة رخيصة (1.00 MR_USDT) — يفترض مسار **SUCCESS**.
- `sub_b` (id=139): خطة باهظة عمدًا (999999.00 MR_USDT، أكبر من أي رصيد ممكن) — يفترض مسار
  **`InsufficientBalanceError` → `PAST_DUE`**.

**النتيجة الفعلية — الاثنان فشلا، لكن بخطأ مختلف تمامًا عن المتوقَّع:**

```json
{
  "status": "success",
  "result": {
    "status": "success", "total": 1, "successful": 0, "failed": 0, "skipped": 0,
    "details": [
      {"subscription_id": 140, "status": "FAILED", "error": "المستلم غير موجود"}
    ]
  }
}
```

(نفس النتيجة بالحرف لـ`sub_a`/`sub_b` الاثنين في التشغيلة الكاملة — `total: 2`، الاثنان
`FAILED` بنفس الرسالة.) **لا `SUCCESS` ولا `PAST_DUE`** — **مفيش فاتورة اتولدت**
(`invoice count: 0` للاثنين)، ولا الاشتراكين اتغيّرت حالتهم (فضلوا `ACTIVE` بـ`next_billing_
date` القديم، بلا تحديث).

**السبب الجذري — طبقة تانية أعمق من نفس النمط المعماري، مختلفة عن اللي اتصلح النهارده:**
`SaaSControlService.__init__` (service.py:59-63):
```python
def __init__(self, db: AsyncSession, tenant_id: int):
    self.tenant_id = tenant_id
    ...
    self.finance = FinanceService(db, tenant_id)   # 👈 مربوط بالـconstructor، ثابت طول عمر الـinstance
```
`self.finance` (كائن `FinanceService`) بياخد `tenant_id` **مرة واحدة عند الإنشاء** ويفضل
ثابت — ومُستخدَم داخل `self.finance.transfer(...)` (المُستدعاة من `process_auto_renewals`
لكل اشتراك) في فحص حاسم:
```python
# app/domains/finance/service.py:78-83
receiver = await user_repo.get_by_email(receiver_email, self.tenant_id)  # self.tenant_id هنا = تينانت الـFinanceService، مش تينانت الاشتراك
if not receiver:
    raise NotFoundError("المستلم غير موجود")
```
بما إن `SaaSControlService(db, 0)` (نمط اليوم الإداري) بيبني `self.finance = FinanceService
(db, 0)` **ثابتة على تينانت 0**، فأي بحث عن `system_account` تينانت 1 (أو أي تينانت حقيقي)
عبر `self.finance.transfer` بيفشل — `get_by_email(email, tenant_id=0)` ميرجّعش حساب النظام
الحقيقي (اللي `tenant_id=1`)، فيرمي `NotFoundError` **قبل ما يوصل لمنطق الرصيد أصلًا**
(`InsufficientBalanceError` مستحيل يتحقق، لأن الكود بيوقع في `NotFoundError` أولًا لكل
الحالتين، حتى `sub_a` الرخيصة).

**الفرق الجوهري عن الإصلاح اللي اتعمل النهارده:** الإصلاح الحالي (§ب) صلّح طبقة **اختيار/تكرار
الاشتراكات** (`get_subscriptions_for_renewal` + استخدام `sub.tenant_id` بدل `target_tenant`
داخل `process_auto_renewals`) — **وده اتأكَّد إنه شغّال 100%**: الاثنين (`sub_a`, `sub_b`)
اتلقطوا بنجاح عبر تينانت 1 رغم إن الـservice instance اتبنت بـ`tenant_id=0` (`total: 2`، مش
`0` — الدليل المباشر إن إصلاح اليوم نجح في هدفه المحدد). لكن **طبقة تانية منفصلة تمامًا**
(`self.finance` الثابتة على تينانت الـconstructor) لسه بتفترض تينانت واحد ثابت طول عمر
الـservice instance — نفس *النمط* المعماري (تينانت مربوط بلحظة الإنشاء بدل كل عملية على
حدة)، لكن في مكوّن مختلف (`FinanceService`، مُستخدَم عبر دومينات كتير غير `saas`) ومش جزء من
التعديل المطلوب اليوم.

**لم يُقفل "الحلقة كاملة مع بند اليوم الأصلي" كما طُلب** — مسار `InsufficientBalanceError →
PAST_DUE` **لم يتحقق فعليًا**، لأن `NotFoundError` بيوقف التنفيذ قبل الوصول لفحص الرصيد
أصلًا. هذا مش فشل في تصميم اختبار `sub_b` (السعر الباهظ كان هيضمن `InsufficientBalanceError`
*لو* وصل الكود لمرحلة فحص الرصيد) — المشكلة أسبق من كده.

### د) القرار المطلوب — لم يُحسم، الجلسة متوقفة هنا

**بند `backlog-process-auto-renewals-task-tenant-zero-noop`
لسه 🔴 مفتوح جزئيًا — مش "✅ اتحل" كما طُلب في البند 4، لأن الإصلاح المطلوب اليوم نجح في
جزئه (اختيار الاشتراكات عبر كل التينانتات — مؤكَّد) لكن كشف عن مانع تاني قبل ما "يعالج
الاشتراك فعليًا" بالمعنى الكامل (نجاح تجديد حقيقي أو تحويل `PAST_DUE` حقيقي).** تحديث البند
بمعلومة جزئية "اتحل" هيكون غير دقيق — القرار الصريح مطلوب:

1. **نوسّع النطاق اليوم** ونصلح `self.finance = FinanceService(db, tenant_id)` كمان — الخيار
   الأقرب تقنيًا زي إصلاح اليوم بالظبط: بدل `FinanceService` واحدة ثابتة على الـconstructor،
   نبني واحدة **جديدة لكل اشتراك** جوّه الحلقة (`finance = FinanceService(self.db,
   sub_tenant_id)`) بدل `self.finance` الثابتة. تغيير محدود (سطر واحد داخل الحلقة + إزالة
   `self.finance` من `__init__` أو تركها لباقي الاستخدامات الأحادية-التينانت اللي مش متأثرة).
2. **نسيب المانع ده مفتوح** كبند backlog سادس منفصل (مثلًا
   `backlog-financeservice-tenant-binding-blocks-cross-tenant-auto-renewals`)، ونحدّث
   `backlog-process-auto-renewals-task-tenant-zero-noop` بحالة **جزئية دقيقة** ("طبقة
   الاختيار اتصلحت واتأكدت، طبقة التنفيذ المالي لسه معطوبة بمانع تاني") بدل "اتحل" الكاملة،
   وما نلمسش `FinanceService` النهارده (خارج نطاق الإصلاح الضيق الأصلي).

**بانتظار قرارك قبل أي تعديل إضافي أو أي تحديث نهائي لحالة البند في `PROGRESS_LOG.md`.**
كل بيانات throwaway اتنضّفت بالكامل (تأكَّد `0` صفوف متبقية بـ`REGTEST-RENEW-%`/
`REGTEST-ERRTEXT-%` في `saas_tenant_subscriptions`/`saas_service_plans`/
`saas_service_catalog`) — صفر أثر جانبي على البيانات، لكن صفر تحقق ناجح كمان لمسار
SUCCESS/PAST_DUE الحقيقي المطلوب.
