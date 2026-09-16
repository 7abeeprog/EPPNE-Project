# جلسة تخطيط: بنية Critical Event Dispatch عبر Celery

**النطاق:** فحص read-only بحت. **لا يوجد أي تعديل كود في هذه الجلسة.**
الهدف: تجهيز خطة بناء طبقة "Critical Event Dispatch عبر Celery" فوق
`EventBus` الحالي — بنية فقط، بلا أي handler حقيقي.

---

## 1) `EventBus.publish()` الحالية كاملة

الملف: `eppne-backend/app/core/event_bus.py` (84 سطر بالكامل، معروض هنا
كامل كما طُلب):

```python
# app/core/event_bus.py
"""
نظام الأحداث (Event Bus) – يربط الأتمتة بباقي القطاعات عبر Redis Pub/Sub.
يسمح بتشغيل سير العمل تلقائياً عند وقوع أحداث معينة في النظام.
"""
import json
import asyncio
from typing import Callable, Dict, Any, Optional
from redis.asyncio import Redis
from app.core.config import settings


class EventBus:
    """ناقل الأحداث المركزي للمنصة السيادية."""

    def __init__(self, redis_client: Optional[Redis] = None):
        """
        تهيئة ناقل الأحداث باستخدام عميل Redis (افتراضي من الإعدادات).
        """
        self.redis = redis_client or Redis.from_url(settings.REDIS_URL)
        self._handlers: Dict[str, list[Callable]] = {}

    async def publish(self, event_name: str, payload: Dict[str, Any]) -> None:
        """
        نشر حدث إلى القناة المحددة.
        أي سير عمل مشترك على هذا الحدث سيتم تشغيله تلقائياً.
        """
        channel = f"events:{event_name}"
        message = json.dumps({
            "event": event_name,
            "payload": payload,
            "timestamp": asyncio.get_event_loop().time()
        })
        await self.redis.publish(channel, message)

    async def subscribe(self, event_name: str, callback: Callable) -> None:
        """الاستماع لحدث معين وتنفيذ الدالة عند وقوعه."""
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        self._handlers[event_name].append(callback)

    async def listen(self, event_name: str) -> None:
        """حلقة استماع مستمرة لحدث معين."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(f"events:{event_name}")

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        if event_name in self._handlers:
                            for handler in self._handlers[event_name]:
                                await handler(data["payload"])
                    except Exception as e:
                        print(f"Error handling event {event_name}: {e}")
        finally:
            await pubsub.unsubscribe(f"events:{event_name}")
            await pubsub.close()

    async def listen_all(self) -> None:
        """الاستماع لجميع الأحداث (حلقة رئيسية)."""
        # يمكن استخدامها للربط مع جميع الأحداث المعروفة
        pass


# ========== دالة مساعدة لتشغيل سير العمل من الحدث ==========
async def trigger_workflow_from_event(
    db_session,
    workflow_repo,
    workflow_id: int,
    payload: Dict[str, Any]
) -> None:
    """
    دالة مساعدة لتشغيل سير العمل عند وقوع حدث.
    تستدعي run_workflow_background مع البيانات الواردة.
    """
    from app.domains.automation.service import run_workflow_background
    await run_workflow_background(
        db=db_session,
        workflow_id=workflow_id,
        triggered_by=f"event:{payload.get('event', 'unknown')}",
        payload=payload
    )
```

**ملاحظة سياق:** `self.redis` هنا فعليًا هو نفس الـSingleton
`RedisClientWrapper` في 22 من 23 دومين (راجع
`test_eventbus_publish_fix.py` — إصلاح سابق كان محتاج method
`publish()` على الـwrapper نفسه، غير مرتبط بمهمتنا هنا لكن يوضح إن
`event_bus.py` نقطة مركزية فعلًا بيمر منها كل دومين تقريبًا).

### أفضل نقطة لإضافة استدعاء Celery الإضافي

**السطر 34** — مباشرة بعد `await self.redis.publish(channel, message)`
وقبل نهاية الـmethod (السطر 34 هو آخر سطر في `publish()` حاليًا):

```python
        await self.redis.publish(channel, message)
        # ⬇ نقطة الإضافة المقترحة (لا يوجد تعديل فعلي في هذه الجلسة)
        # celery_app.send_task("events.dispatch_critical_event",
        #                       args=[event_name, payload], queue="events")
```

**ليه هنا بالضبط:**
- توقيع `publish()` (`-> None`) وسلوكها الخارجي يفضلوا زي ما هم — الـ22
  دومين اللي بينادوا `await self.event_bus.publish(...)` (راجع قسم 4)
  مش هيحسّوا بأي فرق، صفر كسر متوقَّع.
- `Redis.publish()` (Pub/Sub الحالي) بيفضل شغّال بالضبط زي ما هو —
  إضافة Celery **بجانبه** مش بدل منه، فأي `subscribe()`/`listen()`
  حاليين (لو موجودين فعليًا في أي مكان — لم يُعثر على استدعاء فعلي لـ
  `subscribe`/`listen` بره `event_bus.py` نفسها في الفحص الحالي) يفضلوا
  شغالين زي ما هم.
- الإضافة داخل الـmethod نفسها (مش في كل الـ22 call site) يعني نقطة
  تعديل واحدة بس لتفعيل الـdispatch لكل الأحداث دفعة واحدة مستقبلًا،
  بدل تعديل كل دومين على حدة.

---

## 2) نمط `import_string` / استدعاء ديناميكي — موجود ولا محتاج نضيفه؟

**النتيجة: غير موجود إطلاقًا في المشروع.** فحص شامل لـ
`import_string|importlib.import_module|importlib.util` في كل
`eppne-backend/` رجّع **صفر نتائج**.

لكن المشروع عنده **بديل مكافئ فعليًا** بيعتمد عليه Celery نفسه —
الاستدعاء بالاسم النصي (string-based task name) بدل import مباشر:

- `app/core/celery_config.py` (`beat_schedule`) بيربط جداول زمنية
  بمهام عبر اسمها النصي فقط، بلا أي import:
  ```python
  "check-past-due-subscriptions": {
      "task": "saas.check_past_due_subscriptions",   # ⬅ اسم نصي، لا import
      "schedule": crontab(hour=3, minute=0),
      "options": {"queue": "saas"},
  },
  ```
- `app/core/celery_app.py` بيعمل `autodiscover_tasks(['app.tasks',
  'app.domains'], related_name='tasks', force=True)` — فكل الـtasks
  بتتسجل تلقائيًا في سجل Celery الداخلي بأسمائها (`name="..."` في
  الـdecorator)، وأي استدعاء لاحق بالاسم (سواء من beat أو من
  `celery_app.send_task(name, ...)`) بيتحل تلقائيًا بلا أي import
  صريح لملف الـtask.

**أما الاستدعاء الفعلي من كود الخدمات (service layer) فبيعتمد دايمًا
على import مباشر + `.delay()`** — مفيش أي استدعاء ديناميكي بالاسم في
runtime حاليًا. الأماكن اللي لقيتها:
- `app/domains/employment/service.py:567,639` → `generate_payroll_task.delay(...)`, `pay_payroll_task.delay(...)`
- `app/domains/service_marketplace/service.py:258` → `deploy_service_task.delay(...)`
- `app/domains/communications/service.py:81,184` → `send_notification_task.delay(...)`

**التوصية:** لا داعي لإضافة `import_string` أو
`importlib.import_module` من الصفر. الأنسب لمعمارية EventBus تحديدًا
هو **`celery_app.send_task("events.dispatch_critical_event", args=[...])`**
— لأن:
1. بيطابق النمط النصي المستخدَم بالفعل في `celery_config.py`.
2. بيتفادى استيراد صريح لملف task محدد جوّه `app/core/event_bus.py`
   (لو استوردنا مباشرة من `app.tasks.events` مثلًا جوّه `app/core/`،
   وفي نفس الوقت `app.tasks` بتتـautodiscover وبتستورد دومينز بتستورد
   `EventBus` نفسها من `app.core` — فيه احتمال دائرة استيراد
   (circular import) لازم تتفحّص لو اخترنا الـimport المباشر بدل
   `send_task`).
3. `importlib.import_module` العادي يفضل خيار بديل صالح لو حبينا حقنة
   يدوية لاحقًا لخريطة event→handler، لكنه مش ضروري لمجرد تمرير
   الحدث لـCelery — `send_task` بالاسم كافي تمامًا لهذه الطبقة
   (بنية فقط، بلا handler حقيقي حسب النطاق المطلوب).

---

## 3) نمط تسجيل Celery task قياسي (مرجع: `saas.check_past_due_subscriptions`)

المصدر: `eppne-backend/app/tasks/saas_tasks.py:297-306`

```python
@celery_app.task(
    name="saas.check_past_due_subscriptions",
    bind=True,
    max_retries=3,
    default_retry_delay=3600,        # ساعة واحدة بين المحاولات (لأنها مهمة يومية)
    acks_late=True,                   # 🔥 تأكيد بعد التنفيذ
    time_limit=1800,                  # 30 دقيقة كحد أقصى
    soft_time_limit=1500,             # 25 دقيقة إنذار
)
def check_past_due_subscriptions_task(self):
    ...
    try:
        async def _run():
            async with SessionLocal() as db:
                ...
        result = _run_async(_run())
        ...
    except Exception as e:
        logger.error(...)
        raise self.retry(exc=e, countdown=3600)
```

**الشكل القياسي المؤكَّد** لأي task جديد متسق مع المشروع:
- `name="<domain>.<action>"` صريح دايمًا (مش الاسم التلقائي لدالة
  Python) — علشان يتربط بـ`task_routes` في `celery_config.py`
  (`"saas.*": {"queue": "saas"}` مثلًا).
- `bind=True` دايمًا لو محتاجين `self.retry(...)`.
- `max_retries` + (`default_retry_delay` أو `countdown` صريح جوّه
  `self.retry(exc=e, countdown=...)`).
- `acks_late=True` صريح على مستوى الـtask (رغم إنه مضبوط عالميًا في
  `celery_app.py:conf.update(task_acks_late=True)` أصلًا — التكرار
  الصريح موجود في كل الأمثلة زي دي).
- `time_limit` + `soft_time_limit` لأي task ممكن ياخد وقت.
- منطق async جوّه sync task عبر `async def _run(): ... ; _run_async(_run())`
  — الجسر القياسي بين Celery (sync) والكود الفعلي (async/SQLAlchemy
  async session)، وده لازم يتبع لو الـdispatch task الجديدة هتحتاج
  تعمل أي I/O داخلها (مش مطلوب في هذه المرحلة لأن الـhandler وهمي).
- **لازم يتسجل في طابور مناسب** — `celery_config.py` عنده طوابير
  محددة فقط (`default`, `saas`, `academy`, `commerce`, `affiliate`,
  `agritech.*`). **لا يوجد طابور `events` حاليًا** — أي task جديدة
  لـEvent Dispatch محتاجة إما طابور جديد `events` يُضاف لـ
  `task_queues`/`task_routes`، أو استخدام `default` مؤقتًا.

---

## 4) هل `EventBus.publish()` fire-and-forget بحتة فعلًا؟

**نعم، مؤكَّد بالكامل.** فحص كل الاستخدامات الفعلية في 22 دومين +
مهمتين (`app/tasks/agritech.py`, `app/domains/ai_agents/service.py`)
— **كل استدعاء واحد منهم بالشكل:**

```python
await self.event_bus.publish("insurance.subscription.created", {...})
```

**بدون أي التقاط لقيمة الإرجاع** (لا `result = await ...`, ولا فحص
لاستثناء مخصص بعدها بشكل مختلف عن أي await عادي). ده متوقَّع أصلًا
لأن `publish()` معلن `-> None` صراحة (سطر 23 في الملف)، فمفيش نتيجة
أصلًا تُنتظر.

**دليل إضافي مباشر على أن "non-blocking + fire-and-forget" هو النمط
المقبول فعليًا في المشروع لاستدعاءات Celery تحديدًا** — موجود جنبًا
إلى جنب مع `event_bus.publish()` نفسها في نفس الدالة:

`eppne-backend/app/domains/service_marketplace/service.py:256-260`
```python
await self.db.commit()

deploy_service_task.delay(license_obj.id, buyer_tenant_id)   # ⬅ sync call، بلا await، بلا executor

await self.event_bus.publish("service.purchased", {
    "license_id": license_obj.id,
    ...
})
```

يعني: استدعاء Celery (`.delay()`) بالفعل بيُستخدم داخل async method
كاستدعاء **sync عادي غير منتظَر (unawaited)** بلا أي `run_in_executor`
أو تغليف إضافي — نفس النمط اللي هنحتاجه بالضبط لو ضفنا
`celery_app.send_task(...)` جوّه `EventBus.publish()` (سطر 34):
استدعاء sync بسيط (enqueue عبر kombu، رجوعه فوري) بلا `await` وبلا
انتظار نتيجة الـtask، فيفضل التعديل المقترح **non-blocking** بنفس
مستوى القبول المعمول به حاليًا في المشروع — بدون أي حاجة لتغيير
`publish()` لتصبح تنتظر شيء جديد.

---

## الخلاصة (بنية مقترحة فقط — بلا تنفيذ)

1. task جديدة اسمها `events.dispatch_critical_event` في ملف جديد
   (مثلًا `app/tasks/events.py`) بنفس شكل القسم 3، بـhandler وهمي
   (`pass` أو logging بسيط) — بلا منطق حقيقي، متسقة مع النطاق
   المطلوب.
2. طابور `events` جديد يُضاف لـ`task_queues`/`task_routes` في
   `celery_config.py` (أو استخدام `default` مؤقتًا لو الهدف بنية
   أقل بأقل تغيير ممكن).
3. سطر واحد إضافي جوّه `EventBus.publish()` (بعد سطر 34) ينادي
   `celery_app.send_task("events.dispatch_critical_event",
   args=[event_name, payload], queue="events")` — بالاسم النصي (مش
   import مباشر)، sync، غير منتظَر، بلا كسر لأي استخدام حالي في الـ22
   دومين.

**هذه الجلسة فحص read-only فقط — لم يتم تعديل أي ملف كود.**
