# جلسة فحص read-only — 4 مهام Celery في saas_tasks.py بتستدعي دوال غير موجودة

**النطاق:** فحص read-only بحت، صفر تعديل كود. صفر استعلامات كتابة على
قاعدة البيانات (كل استعلامات SQL أدناه `SELECT` فقط، عبر
`docker exec eppne_db psql`).

**التاريخ:** 2026-09-08

**المهام الأربعة محل الفحص:**
1. `generate_monthly_invoices_task`
2. `check_expired_trials_task`
3. `send_trial_expiry_reminders_task`
4. `cleanup_cancelled_subscriptions_task`

**ملاحظة أولية مهمة:** الاكتشاف الأساسي (أن الدوال الأربعة غير موجودة
على `SaaSControlService`) موثَّق بالفعل في `PROGRESS_LOG.md` تحت
`[2026-09-08] backlog-saas-tasks-calling-nonexistent-methods`، وموثَّق
بتفصيل أكبر في
`.claude/reports/past-due-grace-period-notifications-investigation-session-log.md`
§3ج/§4. هذا التقرير **يعيد التحقق من كل بند بالتفصيل لكل مهمة على حدة**
(الكود الكامل، الجدولة الفعلية، البيانات الحية) تحضيرًا للتصميم، ويضيف
معلومة جديدة لم تكن موثقة سابقًا: **بيانات حية فعلية من قاعدة البيانات**
(عدد TRIAL/CANCELLED الفعلي الآن)، بالإضافة لتأكيد وجود بَج ثانٍ منفصل
(`TypeError` في الـconstructor) متراكب فوق بَج الدوال المفقودة في كل
الأربعة.

---

## 0) خلاصة تنفيذية سريعة (جدول مقارنة)

| المهمة | مجدولة في `beat_schedule`؟ | الدالة المطلوبة موجودة؟ | بَج `TypeError` constructor؟ | بيانات حقيقية للاختبار؟ |
|---|---|---|---|---|
| `generate_monthly_invoices_task` | ✅ نعم (أول كل شهر 3ص) | ❌ لا | ✅ موجود (`SaaSControlService(db)` بلا `tenant_id`) | ⚠️ جزئي — يوجد 23 اشتراك ACTIVE لكن **صفر فواتير** حاليًا في `saas_invoices` |
| `check_expired_trials_task` | ✅ نعم (يوميًا 4ص) | ❌ لا | ✅ موجود | ❌ لا — **صفر** اشتراكات `TRIAL` حاليًا في القاعدة |
| `send_trial_expiry_reminders_task` | ❌ لا | ❌ لا | ✅ موجود | ❌ لا — نفس سبب البند السابق |
| `cleanup_cancelled_subscriptions_task` | ❌ لا | ❌ لا | ✅ موجود | ⚠️ اشتراك `CANCELLED` واحد فقط (id=50، tenant_id=1)، عمره ~18 يوم |

**كل الأربعة بلا استثناء تحتاج بناء منطق جديد بالكامل من الصفر** — لا
توجد دالة شبيهة جاهزة نبني عليها بنفس الطريقة اللي بنيت بيها
`process_auto_renewals`/`check_past_due_subscriptions` النهارده (تفاصيل
لكل مهمة تحت). أقرب حاجة موجودة فعليًا هي **دوال repository مساعدة
جزئية** (`get_trial_subscriptions`, `get_past_due_subscriptions` كنمط
مرجعي) مش دوال service كاملة.

---

## 1) `generate_monthly_invoices_task`

### الكود الكامل (`app/tasks/saas_tasks.py:109-141`)

```python
@celery_app.task(
    name="saas.generate_monthly_invoices",
    bind=True,
    max_retries=3,
    default_retry_delay=3600,
    acks_late=True,
    time_limit=3600,                  # ساعة واحدة (عدد كبير من المستأجرين)
    soft_time_limit=3000,             # 50 دقيقة إنذار
)
def generate_monthly_invoices_task(self):
    """
    إنشاء فواتير الشهر الجديد (تُنفذ في أول كل شهر).
    - تولد فواتير لجميع المستأجرين النشطين.
    - تُرسل إشعارات للمستخدمين بالفواتير الجديدة.
    """
    try:
        async def _run():
            async with SessionLocal() as db:  # ✅ استخدام SessionLocal
                service = SaaSControlService(db)
                # 🔥 ملاحظة: تأكد من وجود دالة generate_monthly_invoices في SaaSControlService
                result = await service.generate_monthly_invoices()  # type: ignore[attr-defined]
                await db.commit()

                logger.info(f"✅ Monthly invoices generated: {result}")
                return result

        result = _run_async(_run())
        logger.info("✅ Monthly invoices generation task finished successfully.")
        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"❌ Monthly invoices generation task failed: {str(e)}")
        raise self.retry(exc=e, countdown=3600)
```

### الاستدعاء بالظبط

- `SaaSControlService(db)` — **باراميتر واحد فقط**، بينما الـconstructor
  الفعلي (`app/domains/saas/service.py:59`):
  ```python
  def __init__(self, db: AsyncSession, tenant_id: int):
  ```
  `tenant_id` إجباري بلا `default` → **`TypeError: missing 1 required
  positional argument: 'tenant_id'` مؤكَّد نظريًا، قبل حتى الوصول لسطر
  استدعاء `generate_monthly_invoices()`**. نفس النمط اللي كان مكتشف في
  `process_auto_renewals_task` قبل إصلاحه النهارده (راجع التعليق أعلى
  السطر 65-69 في نفس الملف).
- `service.generate_monthly_invoices()` — **بلا أي باراميترات متوقَّعة**
  (استدعاء بدون args في الكود، والـ`# type: ignore[attr-defined]` يؤكد
  إن الكاتب الأصلي عارف إنها مش موجودة).

### هل فيه دالة شبيهة نبني عليها؟

**لا.** بحث `grep` شامل على `async def ` في `service.py` (622 سطر) لا
يُظهر أي `generate_monthly_invoices` ولا حتى دالة مشابهة بالاسم. أقرب
حاجة موجودة فعليًا هي `_generate_invoice` (خاصة، private، سطر 463-495)
— لكنها **دالة لفاتورة واحدة** (`tenant_id`, `subscription_id`, `plan`
كباراميترات، تُستدعى داخل `process_auto_renewals` لكل اشتراك بيتجدد).
هي **building block** صالح لإعادة الاستخدام (idempotent فعليًا عبر
`idempotency_key = sha256(tenant_id:subscription_id:period)` +
`get_invoice_by_idempotency`)، لكن المهمة المطلوبة (`generate_monthly_
invoices`) لازم تُبنى من الصفر كدالة تلف على **كل الاشتراكات النشطة عبر
كل التينانتات** (مش اشتراك واحد بالـid) وتستدعي `_generate_invoice` لكل
واحد منها — النمط بالظبط زي حلقة `for sub in subscriptions` في
`process_auto_renewals`، لكن بمصدر بيانات مختلف (كل `ACTIVE` وليس فقط
اللي `next_billing_date <= now`).

repository حاليًا عنده `get_subscriptions_for_renewal` (يفلتر
`status=ACTIVE, auto_renew=True, next_billing_date<=now`) — قريب لكن
مش نفس المعنى المطلوب لـ"فاتورة شهرية لكل نشط" (فاتورة شهرية منطقيًا
لازم تتولد لكل اشتراك ACTIVE بغض النظر عن `auto_renew`، والتفريق بين
"فاتورة الشهر" و"تجديد فعلي بخصم من المحفظة" حاجتين مختلفتين محتاجين
قرار تصميم صريح قبل البناء — هل `generate_monthly_invoices` المفروض
تتكرر فوق نفس منطق `process_auto_renewals` ولا تفترض إنها مسار منفصل
تمامًا يُنشئ الفاتورة فقط بدون خصم فوري؟).

### مجدولة فعليًا؟

**نعم.** `app/core/celery_config.py:50-54`:
```python
"generate-monthly-invoices": {
    "task": "saas.generate_monthly_invoices",
    "schedule": crontab(day_of_month=1, hour=3, minute=0),  # أول كل شهر
    "options": {"queue": "saas"},
},
```
→ **أولوية أعلى فورًا**: هتُنفَّذ فعليًا أول يوم من الشهر القادم الساعة
3 صباحًا وتفشل بـ`TypeError` (أو `AttributeError` لو الـconstructor
اتصلح بمعزل قبل بناء الدالة).

### بيانات حقيقية للاختبار؟

استعلام حي (`docker exec eppne_db psql -U eppne -d eppne_v2`):
```
SELECT status, count(*) FROM saas_tenant_subscriptions GROUP BY status;
  status   | count
-----------+-------
 CANCELLED |     1
 ACTIVE    |    23

SELECT status, count(*) FROM saas_invoices GROUP BY status;
 status | count
--------+-------
(0 rows)
```
يوجد **23 اشتراك ACTIVE** صالح كمصدر بيانات لاختبار توليد الفواتير
(مادة خام كافية)، لكن **جدول `saas_invoices` فارغ تمامًا حاليًا (صفر
صف)** — يعني مفيش أي فاتورة قديمة نتحقق منها إن idempotency شغالة صح
أو نقارن نتيجة التوليد بيها. تشغيل أول نسخة من الدالة سيُنشئ أول صفوف
`saas_invoices` في القاعدة من الأساس — لا حاجة لـseed اشتراكات (موجودة
بالفعل)، لكن التحقق من صحة الفواتير المتولدة هيكون "من الصفر" بلا
baseline مقارنة.

---

## 2) `check_expired_trials_task`

### الكود الكامل (`app/tasks/saas_tasks.py:147-183`)

```python
@celery_app.task(
    name="saas.check_expired_trials",
    bind=True,
    max_retries=2,
    default_retry_delay=1800,         # 30 دقيقة
    acks_late=True,
    time_limit=900,                   # 15 دقيقة
    soft_time_limit=600,              # 10 دقائق إنذار
)
def check_expired_trials_task(self):
    """
    التحقق من انتهاء الفترات التجريبية وتعطيل الخدمات.
    - تُنفذ يومياً في الساعة 4 صباحاً.
    - تُرسل تنبيهات للمستخدمين قبل انتهاء الفترة التجريبية بيومين.
    """
    try:
        async def _run():
            async with SessionLocal() as db:  # ✅ استخدام SessionLocal
                service = SaaSControlService(db)
                # 🔥 ملاحظة: تأكد من وجود دالة check_and_expire_trials في SaaSControlService
                expired_count = await service.check_and_expire_trials()  # type: ignore[attr-defined]
                await db.commit()

                logger.info(f"✅ Expired trials checked: {expired_count} subscriptions expired.")
                return {
                    "status": "success",
                    "expired_count": expired_count,
                    "checked_at": datetime.utcnow().isoformat()
                }

        result = _run_async(_run())
        logger.info("✅ Expired trials check task finished successfully.")
        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"❌ Expired trials check task failed: {str(e)}")
        raise self.retry(exc=e, countdown=1800)
```

### الاستدعاء بالظبط

- `SaaSControlService(db)` — نفس بَج الـ`TypeError` أعلاه (تنقيص
  `tenant_id`).
- `service.check_and_expire_trials()` — بلا باراميترات. اسم الدالة
  ("check_and_expire" — فعل مزدوج) يوحي إنها لازم: (أ) تفحص كل
  `TenantSubscription.status == "TRIAL"` عبر كل التينانتات، (ب) تقارن
  `trial_end_date` بالوقت الحالي، (ج) تحوّل المنتهي لـ`EXPIRED`، (د)
  ترجع عدد صحيح (`expired_count`، دالة على `int` مباشرة من نوع الإرجاع
  المتوقَّع في الكود المستدعي — `expired_count` بيتحط مباشرة في
  response بلا `len()` أو معالجة إضافية، فالتوقيع المتوقَّع
  `-> int`).

### هل فيه دالة شبيهة نبني عليها؟

**جزئيًا فقط على مستوى الـrepository، لا وجود على مستوى الـservice.**
`SaaSRepository.get_trial_subscriptions(self, tenant_id: int)`
(`repository.py:123-132`) موجودة فعلاً:
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
لكنها **مقيَّدة بـ`tenant_id` إجباري** (بلا `Optional[int] = None` زي
`get_subscriptions_for_renewal`/`get_past_due_subscriptions`) — يعني
لو المهمة المطلوبة "عبر كل التينانتات" (وهو المتوقَّع لمهمة Celery
مجدولة على مستوى النظام كله، بنفس منطق `check_past_due_subscriptions`
اللي بُني اليوم)، **الدالة دي محتاجة تعديل توقيع أولًا** (إضافة
`Optional[int] = None` بنفس نمط الدالتين التانيتين) قبل أي استخدام —
مش جاهزة "as-is" للاستدعاء من مهمة عامة. كمان لا توجد أي فحص فعلي على
`trial_end_date` داخل هذه الدالة نفسها (بترجع كل TRIAL بلا فلتر تاريخ)
— الفلترة بالتاريخ والتحويل لـEXPIRED لازم يُبنيا بالكامل من الصفر على
مستوى الـservice، بنفس بنية `check_past_due_subscriptions` (loop +
`update_subscription_status` الموجودة أصلًا في repository).

`SaaSRepository.update_subscription_status(subscription_id, tenant_id,
status)` (سطر 287) موجودة وقابلة لإعادة الاستخدام مباشرة للتحويل
لـEXPIRED (نفس الدالة المستخدمة في `check_past_due_subscriptions`).

### مجدولة فعليًا؟

**نعم.** `celery_config.py:55-59`:
```python
"check-expired-trials": {
    "task": "saas.check_expired_trials",
    "schedule": crontab(hour=4, minute=0),  # 4:00 AM يومياً
    "options": {"queue": "saas"},
},
```
→ **أولوية أعلى فورًا**: هتُنفَّذ فعليًا يوميًا 4 صباحًا (خلال أقل من
24 ساعة من أي وقت) وتفشل.

### بيانات حقيقية للاختبار؟

نفس الاستعلام أعلاه: `SELECT status, count(*) FROM
saas_tenant_subscriptions GROUP BY status` → **صفر** صفوف `TRIAL`
حاليًا (فقط `CANCELLED`×1 و`ACTIVE`×23). أسماء الخطط الموجودة تحتوي
كلمة "تجريبية"/"Pilot" في `saas_service_plans.name` (مثلاً
`insurance-pilot-plan`, `transport-pilot-plan`) لكن هذي **أسماء خطط**
فقط، مش حالة اشتراك فعلية `status='TRIAL'` — لا علاقة مباشرة. **لازم
seed صريح** لاشتراك واحد على الأقل بـ`status='TRIAL'` و`trial_end_date`
في الماضي (لاختبار مسار "منتهي") وواحد بـ`trial_end_date` مستقبلي
(لاختبار مسار "لسه ساري، ميتاثرش") قبل أي اختبار حي لهذه الدالة.

---

## 3) `send_trial_expiry_reminders_task`

### الكود الكامل (`app/tasks/saas_tasks.py:189-225`)

```python
@celery_app.task(
    name="saas.send_trial_expiry_reminders",
    bind=True,
    max_retries=2,
    default_retry_delay=3600,
    acks_late=True,
    time_limit=600,
    soft_time_limit=480,
)
def send_trial_expiry_reminders_task(self):
    """
    إرسال تذكيرات للمستخدمين قبل انتهاء الفترة التجريبية بيومين.
    - تُنفذ يومياً.
    - تُرسل إشعارات In-App وبريد إلكتروني.
    """
    try:
        async def _run():
            async with SessionLocal() as db:  # ✅ استخدام SessionLocal
                service = SaaSControlService(db)
                # 🔥 ملاحظة: تأكد من وجود دالة send_trial_expiry_reminders في SaaSControlService
                reminders_sent = await service.send_trial_expiry_reminders()  # type: ignore[attr-defined]
                await db.commit()

                logger.info(f"✅ Trial expiry reminders sent: {reminders_sent} notifications.")
                return {
                    "status": "success",
                    "reminders_sent": reminders_sent,
                    "sent_at": datetime.utcnow().isoformat()
                }

        result = _run_async(_run())
        logger.info("✅ Trial expiry reminders task finished successfully.")
        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"❌ Trial expiry reminders task failed: {str(e)}")
        raise self.retry(exc=e, countdown=3600)
```

### الاستدعاء بالظبط

- `SaaSControlService(db)` — نفس بَج `TypeError` أعلاه.
- `service.send_trial_expiry_reminders()` — بلا باراميترات، متوقَّع
  ترجع `int` (عدد التذكيرات المُرسَلة، بنفس نمط `expired_count` أعلاه).
  الـdocstring يذكر "قبل انتهاء الفترة التجريبية بيومين" و"إشعارات
  In-App وبريد إلكتروني" صراحةً.

### هل فيه دالة شبيهة نبني عليها؟

**لا وجود لأي دالة service بهذا الاسم أو الغرض.** لكن **النمط الكامل
لبناء دالة كهذه موجود بالفعل وجاهز للنسخ شبه الحرفي**:
`check_past_due_subscriptions` (`service.py:335-415`) هي **أقرب مرجع
تصميمي ممكن** — بُنيت النهارده بنفس الغرض بالظبط (فحص دوري + إرسال
تنبيه حسب مرحلة زمنية + `idempotency_key` يمنع تكرار الإرسال لنفس
الاشتراك/المرحلة):
```python
comm_service = CommunicationsService(self.db)
...
await comm_service.send_notification(
    user_id=admin_id,
    title=title,
    body=body,
    data={"subscription_id": sub_id, "day": day_number},
    channel="IN_APP",
    idempotency_key=f"SUB-PASTDUE-{sub_id}-{day_number}",
)
```
نفس الاستدعاء (`CommunicationsService.send_notification`, توقيعها
الكامل مؤكَّد في `communications/service.py:42-51`:
`user_id, title, body, data=None, priority=NORMAL,
channel=IN_APP, idempotency_key=None`) قابل لإعادة الاستخدام حرفيًا
لبناء `send_trial_expiry_reminders`، مع استبدال مصدر البيانات
(`get_past_due_subscriptions` → دالة جديدة تجيب اشتراكات `TRIAL` اللي
`trial_end_date` بينها وبين الآن يومين بالظبط — تحتاج بناء استعلام
جديد في repository، مختلف عن `get_trial_subscriptions` الموجودة
حاليًا لأنها بترجع كل TRIAL بلا فلتر تاريخ).

⚠️ **تحذير موثَّق مسبقًا (`PROGRESS_LOG.md`
backlog-communications-channels-stub)**: قناة `EMAIL` المذكورة في
الـdocstring ("بريد إلكتروني") **غير مُنفَّذة فعليًا** — التسليم
الحقيقي لأي قناة غير `IN_APP` هو stub فاضٍ (لا SMTP حقيقي). أي تصميم
لهذه المهمة يعتمد فعليًا على `channel="EMAIL"` سيبدو ناجحًا (الصف
بيتخزن، الـtask بترجع status="sent" وهمي) لكن **لن يصل فعليًا لأي بريد
حقيقي** حتى يُحل هذا البَج المنفصل أولًا — القرار المعقول هو الاكتفاء
بـ`IN_APP` فقط (بنفس نمط `check_past_due_subscriptions`) لحد ما تكامل
البريد الحقيقي يُبنى.

### مجدولة فعليًا؟

**لا.** بحث في `celery_config.py` (السطور 39-85 كاملة، `beat_schedule`
بأكمله) — **لا يوجد أي مفتاح باسم `send-trial-expiry-reminders` أو
`"task": "saas.send_trial_expiry_reminders"`**. المهمة معرَّفة بـ
`@celery_app.task(name="saas.send_trial_expiry_reminders", ...)` ومقبولة
لو استُدعيت يدويًا (`.delay()`/`.apply_async()`)، لكن **Celery Beat لا
يستدعيها تلقائيًا أبدًا حاليًا**. أولوية أقل نسبيًا من البندين
السابقين (مفيش خطر فشل صامت دوري في الإنتاج الآن)، **لكن لو أُضيفت
جدولتها لاحقًا بدون إصلاح أولًا (زي ما حذّر `PROGRESS_LOG.md` أصلاً)
هتفشل فورًا بنفس النمط**.

### بيانات حقيقية للاختبار؟

نفس نتيجة البند 2 أعلاه: **صفر** اشتراكات `TRIAL` حاليًا. **لازم seed**
اشتراك `TRIAL` بـ`trial_end_date` = الآن + يومين بالظبط (لتفعيل شرط
"تذكير قبل يومين" المذكور في الـdocstring) لاختبار المسار الإيجابي،
وواحد بفارق مختلف (يوم واحد أو 5 أيام مثلاً) للتأكد إن الفلترة صحيحة
ومش بترسل لكل TRIAL بعشوائية.

---

## 4) `cleanup_cancelled_subscriptions_task`

### الكود الكامل (`app/tasks/saas_tasks.py:231-267`)

```python
@celery_app.task(
    name="saas.cleanup_cancelled_subscriptions",
    bind=True,
    max_retries=2,
    default_retry_delay=3600,
    acks_late=True,
    time_limit=1200,
    soft_time_limit=900,
)
def cleanup_cancelled_subscriptions_task(self):
    """
    تنظيف الاشتراكات الملغاة (حذف البيانات المؤقتة، إلغاء الموارد).
    - تُنفذ أسبوعياً.
    - تحذف بيانات المستخدمين وفقاً لسياسة الخصوصية (GDPR/PDPL).
    """
    try:
        async def _run():
            async with SessionLocal() as db:  # ✅ استخدام SessionLocal
                service = SaaSControlService(db)
                # 🔥 ملاحظة: تأكد من وجود دالة cleanup_cancelled_subscriptions في SaaSControlService
                cleaned_count = await service.cleanup_cancelled_subscriptions()  # type: ignore[attr-defined]
                await db.commit()

                logger.info(f"✅ Cancelled subscriptions cleaned: {cleaned_count} subscriptions.")
                return {
                    "status": "success",
                    "cleaned_count": cleaned_count,
                    "cleaned_at": datetime.utcnow().isoformat()
                }

        result = _run_async(_run())
        logger.info("✅ Cleanup cancelled subscriptions task finished successfully.")
        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"❌ Cleanup cancelled subscriptions task failed: {str(e)}")
        raise self.retry(exc=e, countdown=3600)
```

### الاستدعاء بالظبط

- `SaaSControlService(db)` — نفس بَج `TypeError` أعلاه.
- `service.cleanup_cancelled_subscriptions()` — بلا باراميترات، متوقَّع
  ترجع `int` (`cleaned_count`). الـdocstring يذكر صراحةً "حذف البيانات
  المؤقتة، إلغاء الموارد" و**"تحذف بيانات المستخدمين وفقاً لسياسة
  الخصوصية (GDPR/PDPL)"** — ده أخطر بند في الأربعة من ناحية النطاق: مش
  مجرد "تحديث status"، الادعاء صريح بحذف بيانات فعلي.

### هل فيه دالة شبيهة نبني عليها؟

**لا، وهذا البند الأكثر احتياجًا لبناء من الصفر بلا أي مرجع تصميمي
جاهز حتى على مستوى الـrepository.** بفحص `models.py` كاملًا
(`TenantSubscription`, `TenantServiceAccess`, `Invoice`,
`TenantFeatureFlag`) — **لا يوجد أي عمود soft-delete
(`deleted_at`/`is_deleted`) ولا أي جدول "بيانات مؤقتة" مرتبط صراحة
باشتراك ملغى** يمكن حذفه ميكانيكيًا. أقرب حاجة موجودة هي
`update_subscription` (تحديث `status`/`auto_renew` فقط، سطر 270-286 في
repository) — لا علاقة لها بحذف بيانات.

هذا يعني القرار التصميمي هنا **أكبر من مجرد "دالة مفقودة"** — يحتاج
توضيح صريح مسبق (قبل أي بناء) لسؤالين:
1. **"حذف" هنا يعني إيه فعليًا؟** إلغاء `TenantServiceAccess.is_active`
   للخدمة المرتبطة؟ حذف `TenantFeatureFlag` الخاصة بالتينانت للخدمة
   دي؟ حذف فعلي (DELETE) لصفوف من قاعدة البيانات، أم فقط تعطيل
   (soft)؟ الـdocstring الحالي يستخدم لفظ "حذف" صراحةً لكن بلا أي تحديد
   لأي جدول.
2. **بعد أي مهلة زمنية من الإلغاء** يُعتبر الاشتراك "جاهز للتنظيف"؟ لا
   يوجد أي عمود `cancelled_at` منفصل في `TenantSubscription` — الحقل
   الوحيد المتاح هو `updated_at` (بيتحدّث تلقائيًا `onupdate=func.now()`
   لأي تعديل، مش بالضرورة وقت الإلغاء تحديدًا لو تغيّر الصف لاحقًا
   لسبب تاني) — استخدامه كبديل لـ`cancelled_at` فيه هامش خطأ محتاج
   قرار واعي.

بما إن هذا البند يمس **PDPL/GDPR صراحة**، أي بناء فعلي **لازم موافقة
تصميم منفصلة وصريحة قبل التنفيذ** (بما يتوافق مع قاعدة "أي تغيير
معماري كبير يحتاج موافقة صريحة في جلسة منفصلة" — راجع سياسة المشروع)،
مش مجرد إعادة تسمية دالة موجودة زي البندين الأول والتاني.

### مجدولة فعليًا؟

**لا.** نفس فحص `beat_schedule` بالكامل — **لا يوجد أي مفتاح
`cleanup-cancelled-subscriptions` أو `"task":
"saas.cleanup_cancelled_subscriptions"`**. غير مجدولة حاليًا، فمفيش
خطر فشل صامت دوري في الإنتاج الآن.

### بيانات حقيقية للاختبار؟

```
SELECT id, tenant_id, plan_id, status, updated_at, auto_renew, trial_end_date
FROM saas_tenant_subscriptions WHERE status='CANCELLED';

 id | tenant_id | plan_id |  status   |          updated_at           | auto_renew | trial_end_date
----+-----------+---------+-----------+-------------------------------+------------+----------------
 50 |         1 |      48 | CANCELLED | 2026-08-21 01:07:06.813647+00 | f          |
```
**يوجد اشتراك CANCELLED واحد فعلي** (id=50، tenant_id=1، plan_id=48،
`updated_at` بتاريخ 2026-08-21 — أي عمره **~18 يومًا** اعتبارًا من
تاريخ اليوم 2026-09-08). هذا كافٍ كحد أدنى لاختبار "هل الدالة بتلقط
الاشتراك الملغى الصحيح" لكن **غير كافٍ لاختبار منطق العتبة الزمنية**
(اشتراك واحد فقط، عمر واحد فقط) — لو التصميم النهائي يحتاج عتبة زمنية
(مثلاً "بعد 30 يوم من الإلغاء")، هذا الاشتراك الوحيد لن يكون كافيًا
لاختبار الحالتين (قبل/بعد العتبة) بدون seed اشتراك CANCELLED إضافي
بعمر مختلف.

---

## 5) ملاحظة عامة تخص الأربعة (تكرار مؤكَّد)

بحث `grep` شامل لعبارة `SaaSControlService(db)` (باراميتر واحد فقط) في
`app/tasks/saas_tasks.py` يؤكد **الأربعة بلا استثناء** بتستدعي
الـconstructor بنفس الشكل الناقص (`db` فقط، بلا `tenant_id`)، بينما
المهمتان اللي اتصلحتا النهارده (`process_auto_renewals_task`,
`check_past_due_subscriptions_task`) بقيتا تستخدما
`SaaSControlService(db, 0)` صراحةً (نمط "tenant_id=0 إداري" الموثَّق في
`router.py:273`). يعني **أي إصلاح للأربعة لازم يشمل نفس تصحيح
الـconstructor أولًا** (باراميتر ثانٍ `0` بنفس النمط)، بمعزل تمامًا عن
مسألة بناء الدوال المفقودة نفسها — بَجان منفصلان متراكبان فوق بعض، مش
بَج واحد.

---

## 6) خلاصة الأولويات المقترحة للجلسة القادمة (تصميم فقط، بلا تنفيذ هنا)

1. **`check_expired_trials_task`** و**`generate_monthly_invoices_task`**
   — أولوية فورية للتصميم (مجدولتان فعليًا، ستفشلان خلال ساعات/أيام من
   أي تشغيل حي للـworker+beat).
2. **`send_trial_expiry_reminders_task`** — أولوية متوسطة (غير مجدولة
   حاليًا، لكن النمط التصميمي جاهز شبه بالكامل من
   `check_past_due_subscriptions` — أسهل الأربعة بناءً فعليًا).
3. **`cleanup_cancelled_subscriptions_task`** — أولوية أقل من ناحية
   الجدولة (غير مجدولة)، لكن **يحتاج قرار تصميم/نطاق صريح مسبق** (أسئلة
   PDPL/GDPR أعلاه) قبل أي بناء، لأنه الوحيد بلا أي مرجع تصميمي جاهز في
   الكود الحالي.

**لا يوجد أي تعديل كود في هذه الجلسة — فحص read-only بحت بالكامل، بما
في ذلك كل استعلامات قاعدة البيانات (SELECT فقط).**
