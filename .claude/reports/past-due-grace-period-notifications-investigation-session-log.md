# جلسة فحص read-only — فترة سماح PAST_DUE + إشعارات (تحضيرًا للتصميم)

**بدأ التسجيل:** 2026-09-08
**الحالة:** ✅ فحص كامل، **صفر تعديل كود** (النطاق كان read-only بالكامل بناءً على طلب صريح).

**نطاق الجلسة:** فهم الصورة الكاملة قبل تصميم فترة السماح (grace period) + التنبيهات
لاشتراكات SaaS المتأخرة (`PAST_DUE`). خمس نقاط مطلوبة بالحرف:
1. كود `can_access_service` كامل + تحديد بالظبط إيه محتاج يتغيّر عشان فرع `PAST_DUE` يبقى قابل للوصول.
2. هل فيه كود/task موجود بالفعل بيحوّل اشتراك من `ACTIVE` لـ`PAST_DUE`؟
3. هل فيه نظام إشعارات موجود بالفعل؟ شكله + مثال حي.
4. `celery_config.py`/`celery_app.py` — هل فيه beat schedule نقدر نضيف عليه؟
5. توثيق كل ده هنا.

---

## 1) `can_access_service` — الكود الكامل والفرع الميت

**الملف:** `app/domains/saas/service.py:328-350` (كلاس `SaaSControlService`، مُستدعى من 15 دومين تحت الاسم المستعار
`SaaSSubscriptionService` — راجع §5).

```python
async def can_access_service(self, service_code: str) -> bool:
    service = await self.repo.get_service_by_code(service_code)
    if not service:
        return False

    service_id = cast(int, service.id)
    access = await self.repo.get_tenant_service_access(self.tenant_id, service_id)
    if access is None or not cast(bool, access.is_active):
        return False

    subscription = await self.repo.get_active_subscription_via_plan_access(self.tenant_id, service_id)
    if subscription is None:
        return False

    if subscription.status == "PAST_DUE":
        grace_end = subscription.grace_period_end_date
        if grace_end is not None and datetime.now(timezone.utc) < grace_end:
            return True
        else:
            await self.repo.update_subscription_status(cast(int, subscription.id), self.tenant_id, "EXPIRED")
            return False

    return subscription.status in ["ACTIVE", "TRIAL"]
```

### 🔴 لماذا الفرع `PAST_DUE` (سطور 342-348) ميت فعليًا

المشكلة **قبل** الوصول لفرع `PAST_DUE` بسطرين: الاستعلام نفسه اللي بيجيب `subscription` (سطر 338)
مش هيرجّع اشتراك حالته `PAST_DUE` أصلًا — فـ`subscription is None` بيتحقق (سطر 339-340) والدالة بترجع
`False` **قبل ما توصل لفحص `PAST_DUE` نهائيًا**.

**الدليل — `app/domains/saas/repository.py:154-176`:**

```python
async def get_active_subscription_via_plan_access(
    self,
    tenant_id: int,
    service_id: int,
) -> Optional[TenantSubscription]:
    """نفس شكل get_active_subscription بالضبط، لكن الربط بين
    الاشتراك والخدمة عبر saas_plan_service_access (many-to-many)
    بدل ServicePlan.service_id (FK وحيد). جزء من pilot دومين
    insurance فقط — راجع PROGRESS_LOG.md [2026-09-07]."""
    result = await self.db.execute(
        select(TenantSubscription)
        .join(PlanServiceAccess, PlanServiceAccess.plan_id == TenantSubscription.plan_id)
        .where(
            and_(
                TenantSubscription.tenant_id == tenant_id,
                PlanServiceAccess.service_id == service_id,
                TenantSubscription.status.in_(["ACTIVE", "TRIAL"])   # 👈 المشكلة هنا بالظبط
            )
        )
        .order_by(TenantSubscription.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
```

السطر `TenantSubscription.status.in_(["ACTIVE", "TRIAL"])` **يستبعد `PAST_DUE` من الاستعلام نفسه** —
يعني أي اشتراك بحالة `PAST_DUE` أصلًا مش هيترجّع من `get_active_subscription_via_plan_access`، فمستحيل
`subscription.status == "PAST_DUE"` يتحقق في `can_access_service` أبدًا. هذا كود ميت 100% في مساره
الحالي (unreachable dead branch)، مش مجرد بَج منطقي.

### ✅ التغيير الدقيق المطلوب (توصيف فقط — لا تنفيذ)

**تغيير واحد كافٍ:** إضافة `"PAST_DUE"` لقائمة `status.in_([...])` في
`get_active_subscription_via_plan_access` (repository.py:170):

```python
TenantSubscription.status.in_(["ACTIVE", "TRIAL", "PAST_DUE"])
```

بعد هذا التغيير فقط:
- الاستعلام هيرجّع اشتراكات `PAST_DUE` كمان.
- فرع `can_access_service` سطور 342-348 هيبقى قابل للوصول فعليًا، وهيشتغل بمنطقه الحالي بالظبط
  (لو لسه جوّه فترة السماح `grace_period_end_date` → `True`، لو خلصت → `update_subscription_status(...,"EXPIRED")` ثم `False`).
- **ملحوظة جانبية مهمة:** لازم ننتبه إن `order_by(created_at.desc()).limit(1)` بيرجّع **أحدث اشتراك واحد
  بس** — لو الـtenant عنده اشتراك `PAST_DUE` قديم واشتراك `ACTIVE` أحدث لخدمة تانية مربوطة بنفس
  `service_id` (نادر لكن ممكن هيكليًا عبر `PlanServiceAccess` many-to-many)، الترتيب الزمني هو اللي
  بيحسم مش الحالة. هذا سلوك موجود بالفعل قبل أي تعديل (مش تغيير جديد)، لكن يستأهل انتباه وقت تصميم
  فترة السماح لو فيه احتمال تعدد اشتراكات لنفس الخدمة.
- **دالة شقيقة موجودة برضه بنفس العيب بالظبط:** `get_active_subscription` (السطر 134-152 في
  repository.py) — نفس فلتر `status.in_(["ACTIVE","TRIAL"])`. مش مستخدمة داخل `can_access_service`
  حاليًا (اللي بيستخدمها هي `get_active_subscription_via_plan_access` بس)، لكنها **مستخدمة في
  مكانين تانيين**: `create_subscription` (service.py:189 — لمنع اشتراك مزدوج) و
  `get_services_with_access` (repository.py:315 — لعرض حالة الاشتراك في شاشة "خدماتي"). لو الهدف
  من التصميم القادم إظهار حالة `PAST_DUE`/فترة السماح في شاشة "خدماتي" كمان، الدالة دي محتاجة نفس
  التعديل. خارج نطاق `can_access_service` تحديدًا لكن وثيقة الصلة.
- **دالة موازية تمامًا غير مستخدمة حاليًا:** `check_feature_access` (service.py:126-175) — تفحص
  الصلاحية عبر `get_all_active_subscriptions` (كل الاشتراكات النشطة/التجريبية للـtenant، union) بدل
  اشتراك واحد. **صفر استدعاء لها في الكود الحي** (لا router ولا أي service تاني) — بحث شامل أكّد
  إنها معرَّفة بس في `service.py`/`models.py`، مذكورة فقط في docstrings الـmigrations. كود ميت
  منفصل تمامًا عن `can_access_service`، **لا تتأثر ولا تُصلح** بأي تعديل على via_plan_access.

---

## 2) هل فيه كود/task موجود بالفعل بيحوّل `ACTIVE` → `PAST_DUE`؟

**نعم — موجود ومكتمل ومجدوَل فعليًا.** مش مجرد كود معطَّل، ده مسار حي بالكامل.

### أ) التحويل نفسه: `process_auto_renewals` (`app/domains/saas/service.py:266-323`)

دالة تُنفَّذ يوميًا (راجع §4)، بتمر على كل الاشتراكات المستحقة للتجديد
(`get_subscriptions_for_renewal` — `status == "ACTIVE" AND auto_renew == True AND next_billing_date <= now`)،
وتحاول خصم قيمة الخطة عبر `FinanceService.transfer`. لو فشل الخصم بـ `InsufficientBalanceError`:

```python
except InsufficientBalanceError:
    await self.repo.update_subscription(
        cast(int, sub.id),
        target_tenant,
        status="PAST_DUE",
        grace_period_end_date=datetime.now(timezone.utc) + timedelta(days=3),
    )
    results.append({"subscription_id": cast(int, sub.id), "status": "PAST_DUE"})
    logger.warning(f"Auto-renewal failed: subscription {sub.id} - insufficient balance")
```

**ملاحظات مهمة لتصميم فترة السماح:**
- فترة السماح **مضروبة بالفعل** فعليًا في هذا الكود: **3 أيام بالظبط** (`timedelta(days=3)`) —
  مش قيمة نظرية، ده الرقم الحالي المُطبَّق فعلًا كل يوم في الإنتاج (لو الـCelery worker شغّال).
  أي تصميم قادم لازم يقرر صراحة: يُبقي على 3 أيام، ولا يغيّرها — وإما الحالتين تتطلب تعديل هذا السطر.
- الخروج من `PAST_DUE`: `pay_invoice` (service.py:414-453) — لو المستخدم دفع فاتورة `PENDING` مرتبطة
  باشتراك حالته `PAST_DUE`، بيرجّعه `ACTIVE` ويصفّر `grace_period_end_date`. هذا مسار موجود وكامل.
- الفشل النهائي بعد فترة السماح: مُنفَّذ حاليًا **فقط** داخل `can_access_service` نفسها (سطر 347 —
  `update_subscription_status(...,"EXPIRED")`) وهو **lazy/on-demand**: بيحصل بس لما حد يحاول
  يستخدم الخدمة بعد انتهاء فترة السماح، مش عبر أي job دوري مستقل بيمسح كل الاشتراكات المنتهية
  الفترة. يعني لو محدش حاول يوصل للخدمة، الاشتراك ممكن يفضل `PAST_DUE` أبد الدهر بدون أي تحديث حالة
  تلقائي — نقطة تستأهل انتباه في التصميم (هل محتاجين job دوري صريح يحوّل `PAST_DUE` المنتهي
  الفترة → `EXPIRED` بدل الاعتماد بس على lazy check؟).

### ب) الاستدعاء: `process_auto_renewals_task` (`app/tasks/saas_tasks.py:46-96`)

Celery task باسم `saas.process_auto_renewals`، بيستدعي `SaaSControlService.process_auto_renewals()`
كامل (بدون `tenant_id` = كل التينانتس)، مع `commit()` وretry logic (3 محاولات، ساعة بينهم).

### ج) الجدولة: مُفعَّلة بالفعل في beat schedule — راجع §4 لتفاصيل التوقيت.

**الخلاصة الصريحة كما طُلب:** مفيش حاجة ناقصة هنا من ناحية "هل التحويل بيحصل؟" — التحويل بيحصل
تلقائيًا يوميًا 2 صباحًا لو الـworker/beat شغّالين. الفجوة الوحيدة الحقيقية هي **صفر إشعار** يُرسل
وقت التحويل (لا للمستخدم، ولا وقت انتهاء فترة السماح) — راجع §3.

---

## 3) نظام الإشعارات — موجود، لكن بدرجات تفاوتية من الاكتمال

### أ) النظام الحقيقي القابل للاستخدام الآن: `CommunicationsService.send_notification`

**الملف:** `app/domains/communications/service.py:42-91`. نمط كامل ومُستخدَم فعليًا من 3 دومينات
أخرى (transport, automation, realestate) — مش نظرية، ده الـpattern المرجعي الصحيح للقياس عليه.

```python
async def send_notification(
    self,
    user_id: int,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    priority: str = NotificationPriority.NORMAL,
    channel: str = NotificationChannel.IN_APP,
    idempotency_key: Optional[str] = None
) -> Notification:
    """إرسال إشعار – تخزينه أولاً ثم جدولة الإرسال عبر Celery."""
    if idempotency_key:
        existing = await self.repo.get_notification_by_idempotency(idempotency_key)
        if existing:
            return existing

    tenant_id = await self._get_user_tenant(user_id)
    if not tenant_id:
        raise PermissionDeniedError("لا يمكن تحديد المستأجر لهذا المستخدم")

    async with self.db.begin_nested():
        notification = await self.repo.create_notification(
            tenant_id=tenant_id, user_id=user_id, title=title, body=body,
            data=data or {}, priority=priority, channel=channel,
            is_sent=False, idempotency_key=idempotency_key
        )
    await self.db.commit()

    send_notification_task.delay(  # جدولة Celery — راجع (ج) تحت
        notification_id=notification.id, user_id=user_id, title=title,
        body=body, data=data or {}, channel=channel, priority=priority
    )
    return notification
```

**جدول `notifications`** (`app/domains/communications/models.py:31-51`):
`id, tenant_id, user_id, title, body, data(JSONB), channel(EMAIL/SMS/PUSH/WEBSOCKET/IN_APP),
priority(LOW/NORMAL/HIGH/CRITICAL), is_read, is_sent, sent_at, read_at, created_at, idempotency_key(unique)`.

**مثال استخدام حي فعلي** (`app/domains/transport/service.py:873-882`) — النمط اللي دومينات تانية
بتتبعه، ومرشّح مباشر يُقاس عليه لإشعار `PAST_DUE`:

```python
async def _send_notification(self, user_id: int, title: str, body: str):
    try:
        await self.communications.send_notification(
            user_id=user_id, title=title, body=body, channel="IN_APP"
        )
    except Exception as e:
        logger.error(f"Notification failed: {e}")
```

`self.communications = CommunicationsService(db)` مُهيَّأة في `__init__` الدومين. لإشعار `PAST_DUE`
في `saas`، النمط المتوقَّع مشابه: `CommunicationsService(self.db).send_notification(user_id=<admin
المستأجر عبر self._get_tenant_admin_id(...)>, title=..., body=..., channel="IN_APP", idempotency_key=
f"SUB-PASTDUE-{sub.id}-{period}")` — مع الانتباه لاستخدام `idempotency_key` عشان مانبعتش نفس
الإشعار كل يوم لو الـauto-renewal task بتتكرر على نفس الاشتراك.

المستقبِل الطبيعي لإشعار `PAST_DUE` (بدفع الفاتورة) هو نفسه `payer_id` المُستخدَم فعليًا في
`process_auto_renewals` — `await self._get_tenant_admin_id(target_tenant)` (`AcademyTenant.admin_id`،
service.py:65-74) — **مش أي مستخدم عشوائي في التينانت**، ده الشخص اللي بيدفع فعليًا.

### ب) 🔴 تحذير حرج: التسليم الفعلي (FCM/SMTP/Twilio) **مُعطَّل بالكامل — stub فاضي**

`send_notification_task` (المُستدعاة فعليًا عبر `.delay()` أعلاه) مُعرَّفة في **مكانين مختلفين
بنفس الاسم بالظبط** — تضارب تسجيل (task name collision) لم يكن معروفًا قبل هذه الجلسة:

**1. `app/core/celery_app.py:64-75`** (fallback stub صريح):
```python
@shared_task(name="send_notification_task")
def send_notification_task(*args, **kwargs):
    """مهمة إرسال إشعار (مؤقتة - سيتم استبدالها بمهمة حقيقية لاحقاً)"""
    pass

@shared_task(name="send_email_task")
def send_email_task(*args, **kwargs):
    """مهمة إرسال بريد إلكتروني (مؤقتة - سيتم استبدالها بمهمة حقيقية لاحقاً)"""
    pass
```

**2. `app/domains/communications/tasks.py:1-28`** (نسخة "حقيقية" لكن جسمها فاضي برضه، وعلى تطبيق
Celery منفصل تمامًا — `Celery("communications", ...)` مش نفس `celery_app` المركزي):
```python
celery_app = Celery("communications", broker=settings.REDIS_URL)

@celery_app.task
def send_notification_task(notification_id, user_id, title, body, data, channel):
    if channel == "PUSH":
        # tokens = get_user_devices(user_id)
        # for token in tokens: send_fcm(token, title, body, data)
        pass
    elif channel == "EMAIL":
        # email = get_user_email(user_id)
        # send_smtp_email(email, title, body)
        pass
    elif channel == "SMS":
        # phone = get_user_phone(user_id)
        # send_twilio_sms(phone, body)
        pass
    # تحديث حالة الإرسال في قاعدة البيانات بعد النجاح
    # update_notification_status(notification_id, is_sent=True)
    return {"status": "sent", "notification_id": notification_id}
```

كل الفروع الثلاثة (`PUSH`/`EMAIL`/`SMS`) في النسخة التانية **كود مُعلَّق بالكامل (`pass`)** — لا
`send_fcm` ولا `send_smtp_email` ولا `send_twilio_sms` بتتنفذ فعليًا رغم إن الـimports موجودة في
أعلى الملف. والدالة بترجّع `{"status": "sent"}` وهمي دايمًا بغض النظر عن أي حاجة.

**الأثر العملي:** `send_notification.delay(...)` بيتنفذ فعلاً (task بيتقبل من الـbroker)، والصف بيتسجل
في جدول `notifications` (`is_sent=False` دايمًا لأن آخر خطوة `update_notification_status` مُعلَّقة
كمان)، لكن **صفر تسليم فعلي** لأي قناة خارجية (لا FCM push حقيقي، لا إيميل، لا SMS). القناة الوحيدة
اللي ممكن "تشتغل" فعليًا هي `IN_APP` (لأنها مجرد صف في جدول `notifications` يُقرأ لاحقًا عبر
`get_user_notifications` — مفيش إرسال خارجي مطلوب أصلًا لـIN_APP، فهي فعليًا القناة الوحيدة الكاملة
100%).

**أي تصميم يعتمد على إشعار بريد إلكتروني فعلي لـ`PAST_DUE` لازم يعالج هذا الـstub الفاضي أولًا —
وإلا الإشعار هيتسجل بصمت في الجدول بدون ما يوصل لحد فعليًا.** إشعار `IN_APP` وحده هو المسار الوحيد
اللي هيشتغل من أول لحظة بدون أي إصلاح إضافي.

### ج) دوال Celery تانية موجودة اسميًا بس بتستدعي methods مش موجودة أصلًا

اكتشاف جانبي أثناء فحص `saas_tasks.py` (§4) — 3 من أصل 6 tasks معرَّفة فيه بتستدعي دوال على
`SaaSControlService` **غير موجودة إطلاقًا** في `service.py` (بحث شامل بـgrep أكّد الغياب):
`generate_monthly_invoices`, `check_and_expire_trials`, `send_trial_expiry_reminders`,
`cleanup_cancelled_subscriptions`. كل الأربعة معلَّمة `# type: ignore[attr-defined]` مع تعليق
"تأكد من وجود الدالة" — يعني الكاتب نفسه كان عارف إنها غير مؤكَّدة وقت الكتابة. تفصيل كامل في §4.

---

## 4) `celery_config.py` / `celery_app.py` — الـbeat schedule الموجود

### أ) `app/core/celery_app.py` — التطبيق المركزي

- Celery app اسمه `eppne_worker`، broker/backend = `settings.REDIS_URL`.
- تحميل `celery_config` كـ`namespace='CELERY'` (سطر 23).
- Autodiscovery: `['app.tasks', 'app.domains']` مع `related_name='tasks'` — يعني أي ملف `tasks.py`
  جوّه أي دومين بيتسجَّل تلقائيًا (ده اللي خلّى `communications/tasks.py` يتسجَّل، بالتضارب المذكور
  في §3ب).
- **صفر تسجيل** لـ`app.domains.saas.service` هنا مباشرة — الـtasks الفعلية في `app/tasks/saas_tasks.py`
  المنفصل (مش جوّه `app/domains/saas/`).

### ب) `app/core/celery_config.py` — الجدولة الكاملة (`beat_schedule`)

```python
beat_schedule = {
    "process-auto-renewals": {
        "task": "saas.process_auto_renewals",
        "schedule": crontab(hour=2, minute=0),  # 2:00 AM يومياً
        "options": {"queue": "saas"},
    },
    "generate-monthly-invoices": {
        "task": "saas.generate_monthly_invoices",
        "schedule": crontab(day_of_month=1, hour=3, minute=0),
        "options": {"queue": "saas"},
    },
    "check-expired-trials": {
        "task": "saas.check_expired_trials",
        "schedule": crontab(hour=4, minute=0),
        "options": {"queue": "saas"},
    },
    # + agritech (3 مهام), affiliate (مهمة واحدة)
}
```

**حالة كل مهمة saas مجدولة فعليًا في beat_schedule:**

| المهمة المجدولة | التوقيت | الدالة المستدعاة على `SaaSControlService` | موجودة فعلاً؟ |
|---|---|---|---|
| `process-auto-renewals` | يوميًا 2 صباحًا | `process_auto_renewals()` | ✅ موجودة (service.py:266) — هي نفسها مصدر التحويل لـ`PAST_DUE` (§2) |
| `generate-monthly-invoices` | أول كل شهر 3 صباحًا | `generate_monthly_invoices()` | 🔴 **غير موجودة** — استدعاء `.delay()`/تنفيذ مباشر هيرمي `AttributeError` |
| `check-expired-trials` | يوميًا 4 صباحًا | `check_and_expire_trials()` | 🔴 **غير موجودة** — نفس المشكلة |

**مهمتان معرَّفتان في `saas_tasks.py` لكن غير مجدولتين في `beat_schedule` أصلًا** (يعني حتى لو
اشتغلوا، محدش بينادي عليهم تلقائيًا — يحتاجوا استدعاء يدوي):
- `send_trial_expiry_reminders_task` (`saas.send_trial_expiry_reminders`) — واسمها بالظبط
  بيوحي إنها المكان المنطقي لإضافة إشعار `PAST_DUE` عليها لاحقًا، لكنها **مش مجدولة وdالتها الأساسية
  (`send_trial_expiry_reminders`) مش موجودة على `SaaSControlService` أصلًا** — تحتاج بناء من الصفر،
  مش مجرد جدولة.
- `cleanup_cancelled_subscriptions_task` — نفس الوضع.

### ج) الخلاصة لسؤال "هل فيه beat schedule نقدر نضيف عليه مهمة فحص الاشتراكات المتأخرة؟"

**نعم، البنية التحتية جاهزة 100% للإضافة**: `beat_schedule` dict في `celery_config.py` مفتوح
للإضافة المباشرة (نفس نمط `process-auto-renewals` بالظبط)، والـqueue `"saas"` مُعرَّفة بالفعل
(`task_queues` سطر 11). **مفيش حاجة تقنية ناقصة لإضافة `"send-past-due-notifications"` كمهمة
جديدة بنفس النمط.**

لكن **القرار التصميمي المفتوح** هو: هل نضيف مهمة **منفصلة** (زي `check-past-due-subscriptions`)
تفحص كل الاشتراكات `PAST_DUE` يوميًا وترسل تذكير + تحوّل المنتهية الفترة لـ`EXPIRED` بشكل استباقي
(بدل الاعتماد على lazy check جوّه `can_access_service` — راجع الملاحظة في §2أ)، أو نُلحق منطق
الإشعار **جوّه** `process_auto_renewals` نفسها وقت لحظة التحويل لـ`PAST_DUE` (سطر 309-317 في
service.py) زي ما `pay_invoice` بيرجّع الحالة لـ`ACTIVE`. الخياران ممكنان تقنيًا بنفس البنية
الموجودة — القرار محتاج موافقة صريحة في جلسة التصميم القادمة (زي ما نص `eppne-project` skill
ينص: أي تغيير معماري كبير يحتاج موافقة منفصلة قبل التنفيذ).

---

## 5) ملخص تنفيذي (للجلسة القادمة — التصميم)

1. **الفرع `PAST_DUE` في `can_access_service` ميت لسبب واحد بسيط ومحدد**: استعلام
   `get_active_subscription_via_plan_access` (repository.py:170) بيستبعد `PAST_DUE` من
   `status.in_([...])`. إضافة `"PAST_DUE"` لهذه القائمة كافية لتفعيل الفرع الموجود بالفعل — الفرع
   نفسه لا يحتاج أي تعديل منطقي.
2. **التحويل `ACTIVE → PAST_DUE` موجود، مكتمل، ومجدوَل يوميًا فعليًا** (`process_auto_renewals` عبر
   beat schedule 2 صباحًا) — فترة السماح الحالية **3 أيام مضروبة بالفعل في الكود**. لا "بناء من
   الصفر" مطلوب هنا، فقط قرار: نُبقي 3 أيام أو نغيّرها.
3. **نظام إشعارات `IN_APP` كامل وجاهز فعليًا** (`CommunicationsService.send_notification` + جدول
   `notifications`) ومُستخدَم كنمط في 3 دومينات أخرى — هذا المسار الجاهز للاستخدام الفوري.
   **الإيميل/SMS/Push غير موجودين فعليًا رغم وجود الواجهة** — كلاهما stub فاضي (`pass`) في مكانين
   متضاربين بنفس اسم الـtask. أي متطلب "إشعار بالإيميل" في التصميم القادم لازم يتعامل مع هذا الـstub
   كعمل منفصل، مش تفصيلة تُحل تلقائيًا.
4. **البنية التحتية لـCelery beat جاهزة للإضافة المباشرة** بنفس نمط `process-auto-renewals` —
   القرار المفتوح الوحيد هو مكان منطق الإشعار (مهمة دورية منفصلة، ولا جوّه `process_auto_renewals`
   نفسها) وهل نضيف job دوري صريح يحوّل `PAST_DUE` المنتهي الفترة → `EXPIRED` بدل الاعتماد فقط على
   lazy check جوّه `can_access_service`.
5. **اكتشافات جانبية غير مرتبطة مباشرة بنطاق فترة السماح، لكن تستأهل مهمة منفصلة لاحقًا:**
   - 3 من 6 مهام Celery في `saas_tasks.py` بتستدعي دوال غير موجودة على `SaaSControlService`
     (`generate_monthly_invoices`, `check_and_expire_trials`, وكمان `send_trial_expiry_reminders`,
     `cleanup_cancelled_subscriptions` رغم عدم جدولتهم) — هتفشل بـ`AttributeError` فور التنفيذ.
   - تضارب تسجيل اسم `send_notification_task` بين `celery_app.py` (stub) و`communications/tasks.py`
     (نسخة "حقيقية" لكن جسمها فاضي كمان، على Celery app منفصل تمامًا).
   - `check_feature_access` (service.py) دالة صلاحيات موازية كاملة لكن **غير مستخدمة إطلاقًا** —
     كود ميت منفصل، لا علاقة له بـ`can_access_service`.

**لم يُعدَّل أي ملف كود في هذه الجلسة.**
