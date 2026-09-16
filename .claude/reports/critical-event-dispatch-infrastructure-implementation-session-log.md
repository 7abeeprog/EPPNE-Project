# جلسة تنفيذ: بنية Critical Event Dispatch عبر Celery

**النطاق:** بناء بنية "Critical Event Dispatch عبر Celery" فوق
`EventBus` الحالي (Redis Pub/Sub) — **بلا أي handler حقيقي** (pass/logging
بس)، حسب جلسة تخطيط read-only سابقة (راجع
`.claude/reports/critical-event-dispatch-infrastructure-planning-session-log.md`).

---

## 1) ملف جديد `app/core/critical_events.py`

```python
# app/core/critical_events.py
"""
خريطة الأحداث الحرجة (Critical Events) اللي محتاجة تتوصّل عبر Celery
بالإضافة إلى Redis Pub/Sub العادي في EventBus.publish().

بنية فقط حاليًا — القاموس فاضي عمدًا، بلا أي handler حقيقي. أي حدث حرج
جديد يُضاف هنا صراحةً لما يبقى له سبب فعلي (retry مضمون، تتبّع، إلخ).
"""

CRITICAL_EVENT_HANDLERS: dict[str, str] = {
    # يُضاف صراحة لكل حدث حرج جديد — فارغ حاليًا، بنية بس
}
```

فاضي عمدًا حسب المطلوب — صفر حدث حرج حقيقي مسجَّل.

---

## 2) طابور جديد `events` في `celery_config.py`

`task_queues`:
```python
Queue("affiliate", Exchange("affiliate"), routing_key="affiliate"),
Queue("events", Exchange("events"), routing_key="events"),   # ⬅ جديد
```

`task_routes`:
```python
"affiliate.*": {"queue": "affiliate"},
"events.*": {"queue": "events"},   # ⬅ جديد
```

نفس النمط الحرفي المستخدَم لـ`saas`/`commerce`/`affiliate` — صفر تغيير
على أي طابور موجود.

---

## 3) Task جديدة `app/tasks/events.py` — `events.dispatch_critical_event`

```python
# app/tasks/events.py
"""
Task عامة لـCritical Event Dispatch — بنية فقط حاليًا، بلا أي handler
حقيقي. تُستدعى من EventBus.publish() (app/core/event_bus.py) لأي حدث
موجود في CRITICAL_EVENT_HANDLERS (فاضي حاليًا، راجع
app/core/critical_events.py).
"""
from app.core.celery_app import celery_app
from app.core.critical_events import CRITICAL_EVENT_HANDLERS
from app.core.logging_conf import logger


@celery_app.task(
    name="events.dispatch_critical_event",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    time_limit=300,
    soft_time_limit=240,
)
def dispatch_critical_event_task(self, event_name: str, payload: dict):
    try:
        if event_name in CRITICAL_EVENT_HANDLERS:
            logger.info(f"🔥 Critical event dispatched: {event_name} | payload={payload}")
        else:
            logger.info(f"Critical event dispatch skipped (not registered): {event_name}")
    except Exception as e:
        logger.error(f"❌ Critical event dispatch failed for {event_name}: {str(e)}")
        raise self.retry(exc=e, countdown=60)
```

نفس الشكل القياسي المؤكَّد في §3 من جلسة التخطيط
(`saas.check_past_due_subscriptions_task`): `name=` صريح، `bind=True`،
`max_retries`، `acks_late=True`، `time_limit`/`soft_time_limit`. الجسم
وهمي فعلًا: `logger.info` بس، صفر استدعاء handler حقيقي (القاموس فاضي
أصلًا فمفيش أي فرع حقيقي يتفّذ عمليًا حاليًا).

---

## 4) تعديل `EventBus.publish()` — سطر واحد فعليًا

الاستيراد أعلى الملف (`app/core/event_bus.py`):
```python
from app.core.celery_app import celery_app
from app.core.critical_events import CRITICAL_EVENT_HANDLERS
```

الجسم (بعد `await self.redis.publish(channel, message)` مباشرة):
```python
        await self.redis.publish(channel, message)

        if event_name in CRITICAL_EVENT_HANDLERS:
            celery_app.send_task("events.dispatch_critical_event",
                                  args=[event_name, payload], queue="events")
```

استخدام `celery_app.send_task(name_string, ...)` بدل import مباشر لملف
الـtask — بالضبط زي توصية جلسة التخطيط، تفاديًا لأي circular import
محتمل (`event_bus.py` مستورَد من 22 دومين، ولو استوردنا task module
معين مباشرة جوّه `app/core/` كان ممكن يخلق دورة استيراد مع دومينات
تانية).

### فحص circular import فعليًا (مش افتراض)

نُفِّذ بعد التعديل مباشرة، بترتيب تصاعدي في الخطورة:

```
python -c "import app.core.event_bus"          → OK
python -c "import app.core.celery_app"          → OK (2 tasks مسجَّلة أصلًا: send_email_task, send_notification_task — autodiscover_tasks(['app.tasks','app.domains'], related_name='tasks') مبيلقطش saas_tasks.py/events.py فعليًا لأنها مش اسمها الحرفي "tasks.py"، ده سلوك pre-existing غير مرتبط بتعديلنا)
python -c "import app.main"                     → FULL APP IMPORT OK (كل الـ23 دومين + كل الراوترز)
```

**صفر `ImportError`/`ImportWarning` مرتبط بالتعديل.** الرسالة الوحيدة
اللي ظهرت أثناء `import app.main` هي `UnicodeEncodeError` من
`logging_conf.py` (emoji `✅` على console بترميز `cp1256`) — pre-existing
تمامًا، صفر علاقة بالتعديل، لم يمنع اكتمال الاستيراد (`FULL APP IMPORT
OK` طبعت في النهاية).

---

## 5) اختبار حي — `tests/test_critical_event_dispatch_infrastructure.py`

**5/5 PASSED، Redis حقيقي (نفس منهجية `test_eventbus_publish_fix.py`
الأصلية — subscriber مستقل تمامًا عبر `pubsub()` خام)، صفر mock على
طبقة النشر نفسها:**

1. **`test_existing_event_still_publishes_with_empty_critical_handlers`**
   — الاختبار المطلوب صراحةً في الجلسة: نادى `event_bus.publish(...)`
   على `insurance.subscription.created` (حدث إنتاجي حقيقي، نفس نمط
   `insurance/service.py:264` الحرفي). تأكَّد إن:
   - `redis.publish` نفَّذ فعليًا (subscriber مستقل استلم الرسالة
     بالضبط زي `test_eventbus_publish_fix.py` الأصلي).
   - `celery_app.send_task` **لم تُستدعَ إطلاقًا** (`mock_send_task.assert_not_called()`)
     — لأن الحدث مش موجود في `CRITICAL_EVENT_HANDLERS` (فاضي فعليًا).
   - **صفر استثناء إضافي** من كود الـdispatch الجديد.

2. **`test_critical_event_triggers_celery_dispatch_without_breaking_redis_publish`**
   — بما إن القاموس فاضي في الإنتاج ومفيش أي حدث حرج حقيقي بعد، اتسجَّل
   حدث اختباري مؤقت (`monkeypatch.setitem`, مش حدث إنتاجي) عشان نتأكد
   إن المسار الجديد **نفسه** بيشتغل صح لما يتفعّل مستقبلًا:
   - `redis.publish` لسه بينفذ (subscriber مستقل استلم الرسالة).
   - `celery_app.send_task` اتنادت **مرة واحدة بالضبط** بالـ
     `name`/`args`/`queue` الصح (`"events.dispatch_critical_event",
     args=[event_name, payload], queue="events"`).

3. **`test_dispatch_critical_event_task_registered_with_standard_shape`**
   — `"events.dispatch_critical_event"` مسجَّلة فعليًا في
   `celery_app.tasks`، و`max_retries=3`/`acks_late=True` مطابقين للشكل
   القياسي.

4. **`test_dispatch_critical_event_task_body_is_noop_logging_only`** —
   استدعاء الجسم مباشرة (`dispatch_critical_event_task.run(...)`)
   بيرجع `None` — صفر معالجة حقيقية، logging بس.

5. **`test_events_queue_registered_in_celery_config`** — طابور
   `events` موجود في `task_queues` + `task_routes["events.*"]["queue"]
   == "events"`.

```
tests/test_critical_event_dispatch_infrastructure.py::test_existing_event_still_publishes_with_empty_critical_handlers PASSED
tests/test_critical_event_dispatch_infrastructure.py::test_critical_event_triggers_celery_dispatch_without_breaking_redis_publish PASSED
tests/test_critical_event_dispatch_infrastructure.py::test_dispatch_critical_event_task_registered_with_standard_shape PASSED
tests/test_critical_event_dispatch_infrastructure.py::test_dispatch_critical_event_task_body_is_noop_logging_only PASSED
tests/test_critical_event_dispatch_infrastructure.py::test_events_queue_registered_in_celery_config PASSED
5 passed in 2.99s
```

بالإضافة لذلك، أُعيد تشغيل `tests/test_eventbus_publish_fix.py`
(4 اختبارات حية موجودة أصلًا على `insurance`/`zamakana`/
`arbitration_syndicates` عبر `EventBus` حقيقي + Redis حقيقي) بعد
التعديل — **4/4 PASSED بلا أي تغيير**، تأكيد إضافي مستقل إن التعديل صفر
تأثير على الاستخدامات الحالية للـ22 دومين.

---

## 6) Regression — تشغيلة كاملة

**669.55 ثانية**، باستثناء `tests/test_affiliate_service_missing_methods.py`
(نفس `ImportError: cannot import name 'ActionCommission'` مسبق وغير
مرتبط، موثَّق في جلسات سابقة — خارج نطاق هذه الجلسة تمامًا):

```
15 failed, 183 passed, 2 xfailed, 247 warnings in 669.55s (0:11:09)
```

**مطابقة تامة للأساس** (`15 failed, 178 passed, 2 xfailed, 243 warnings`
— جلسة `logistics-entity-membership-implementation`، آخر جلسة موثَّقة في
`PROGRESS_LOG.md` قبل هذه):

- `183 = 178 + 5` (الاختبارات الحية الجديدة في هذه الجلسة).
- `247 = 243 + 4` (تحذيرات `DeprecationWarning` لإغلاق `pubsub`/الاتصال
  — نفس النمط الموجود أصلًا في `test_eventbus_publish_fix.py`، وليست
  تحذيرات جديدة من كود الإنتاج).
- **نفس الـ15 فشل بالحرف** (قورنت الأسماء سطر بسطر مع القائمة الموثَّقة
  في جلسات `health`/`logistics` — تطابق كامل: `test_realestate_insurance_savepoint`،
  `test_saas_active_subscription` (×2)، `test_user_repository_get_by_id_audit`
  (×9)، `test_user_repository_get_user_audit` (×2)). كل واحد فيهم
  pre-existing وموثَّق في تقرير investigation منفصل خاص بيه، **صفر علاقة
  بتعديل EventBus/Celery في هذه الجلسة**.

**صفر regression جديد.**

---

## الملفات المعدَّلة/الجديدة

**معدَّلة (إضافة صرفة، صفر حذف/تعديل على كود موجود):**
- `app/core/event_bus.py` (استيرادان + 3 أسطر جسم، بعد `await
  self.redis.publish(...)` مباشرة).
- `app/core/celery_config.py` (سطر `Queue` + سطر `route`).

**جديدة:**
- `app/core/critical_events.py`
- `app/tasks/events.py`
- `tests/test_critical_event_dispatch_infrastructure.py`

**غير مُلموسة إطلاقًا:** `subscribe()`, `listen()`, `listen_all()`,
`trigger_workflow_from_event()` — كلهم زي ما هم بالحرف. أي دومين من
الـ22 اللي بينادي `event_bus.publish(...)` لم يُلمَس ولا سطر واحد فيه.

---

## نطاق متبقٍّ خارج هذه الجلسة (بنية فقط كما طُلب)

`CRITICAL_EVENT_HANDLERS` لسه فاضي — **صفر حدث حرج حقيقي مسجَّل، صفر
handler فعلي**. أي حدث حرج جديد فعلي (زي `payment.failed` أو
`subscription.expired` مثلًا) وربطه بمنطق retry/تنبيه حقيقي داخل
`dispatch_critical_event_task` قرار منتج/معماري منفصل — يحتاج موافقة
صريحة في جلسة منفصلة قبل أي تنفيذ، حسب قاعدة العمل العامة للمشروع.
