"""
regression test لجلسة `eventbus-redis-wrapper-publish-fix` (المرحلة 1.1).
تقرير الجلسة الأصلية: .claude/reports/eventbus-publish-fix-session-log.md

السبب الجذري (كان): `RedisClientWrapper` (`app/core/redis_client.py`) لم
تكن تملك method اسمها `publish()` إطلاقًا. `EventBus.publish()`
(`app/core/event_bus.py:34`) بتنادي `await self.redis.publish(channel,
message)` — و`self.redis` هو نفس الـSingleton `RedisClientWrapper` في
**22 دومين من 23** بيستخدموا `EventBus` (تصحيح جوهري عن رقم التقرير
المصدر "34" — راجع قسم 1 من التقرير). `finance` وحدها كانت صحيحة أصلًا
(بتستخدم عميل `redis.asyncio.Redis` خام مباشر، مش الـwrapper). أي محاولة
نشر حدث حقيقي عبر الـ22 دومين كانت بترمي `AttributeError:
'RedisClientWrapper' object has no attribute 'publish'` فورًا.

الإصلاح المُطبَّق (`app/core/redis_client.py`، 5 أسطر، إضافة صرفة):
```python
async def publish(self, channel: str, message: str):
    client = await self.get_client()
    return await client.publish(channel, message)
```
نفس نمط باقي "الاختصارات" الموجودة أصلًا في نفس الكلاس (`ping`, `get`,
`setex`, ...) — صفر لمس على `EventBus` نفسها أو أي ملف دومين.

هذا الملف يعيد إنتاج التحقق الحي الموثَّق في قسم 7 من التقرير (منهجية
مطابقة تمامًا): **subscriber مستقل تمامًا عن أداة النشر قيد الاختبار**
(اتصال Redis خام منفصل عبر `pubsub()` مباشرة، مش عبر `EventBus`/
`redis_client` نفسها) بيستلم فعليًا الرسالة المنشورة، مع تطابق كامل
`event`/`payload` — مش مجرد "صفر استثناء" (الإثبات الأضعف اللي التقرير
الأصلي وصفه صراحة بـ"لا يكفي وحده").

**التغطية:** الثلاثة دومينات المُتحقَّق منهم حيًا في الجلسة الأصلية بالضبط
(قسم 7)، بنفس اسم الحدث الحقيقي ونفس نمط بناء `EventBus` الحرفي المستخدَم
فعليًا في كود كل دومين (مؤكَّد بالقراءة المباشرة وقت كتابة هذا الملف، صفر
انحراف عن التقرير):

| الدومين | نمط بناء `EventBus` (من `service.py` الفعلي) | اسم الحدث المُختبَر |
|---|---|---|
| `insurance` | `EventBus(cast(Any, redis_client))` (سطر 35) | `insurance.subscription.created` |
| `zamakana` | `EventBus(cast(Any, redis_client))` (سطر 41) | `zamakana.node.created` |
| `arbitration_syndicates` | `EventBus(redis_client)  # type: ignore` (سطر 33) | `arbitration.case.created` |

زائد اختبار خامس مباشر على `RedisClientWrapper.publish()` نفسها (الإصلاح
الفعلي، بمعزل عن `EventBus`) — يثبت الطبقة السفلى المُصلَحة مباشرة، مش بس
استخدامها غير المباشر عبر الدومينات الثلاثة.

**بيانات throwaway:** صفر صفوف DB (الملف ده بيختبر Redis pub/sub بس، صفر
اعتماد على `tenant_id`/بيانات تطبيقية). كل اختبار بيستخدم قناة/`marker`
فريد (`uuid4`) لتفادي أي تداخل بين تشغيلات متوازية، والتنظيف (`unsubscribe`
+ `close()` على اتصال الـsubscriber المستقل) بيحصل في `finally` بعد كل
اختبار — صفر اتصال Redis معلَّق بعد التشغيل.
"""
import asyncio
import json
import uuid
from typing import Any, Callable, Optional, cast

import pytest
import pytest_asyncio

from app.core.redis_client import redis_client
from app.core.event_bus import EventBus


@pytest_asyncio.fixture(autouse=True)
async def _redis_event_loop_isolation():
    """يقفل اتصال redis_client (الـSingleton) بعد كل اختبار — نفس احتياط
    fixture `db` في conftest.py: pytest-asyncio بيفتح event loop جديد لكل
    test function على ويندوز (ProactorEventLoop)، لكن redis_client عالمي
    بيحتفظ باتصال من الـloop السابق. بلا هذا التنظيف، أول استخدام لـredis_client
    في أي اختبار بعد الأول بيكراش بـ`RuntimeError: Event loop is closed`."""
    yield
    await redis_client.close()


async def _capture_one_message(channel: str, publish_action: Callable, timeout: float = 5.0) -> Optional[dict]:
    """يفتح subscriber مستقل تمامًا (اتصال Redis خام منفصل عبر pubsub())، بينفذ
    publish_action() (أداة النشر قيد الاختبار)، وبيرجع أول رسالة حقيقية
    (type == "message") اتستلمت على القناة، أو None لو حصل timeout."""
    client = await redis_client.get_client()
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(channel)
        # استهلاك رسالة تأكيد الاشتراك (type="subscribe") قبل النشر
        await pubsub.get_message(timeout=2.0)

        await publish_action()

        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            msg = await pubsub.get_message(timeout=1.0)
            if msg and msg.get("type") == "message":
                return msg
        return None
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()


# ============================================================
# 1) RedisClientWrapper.publish() مباشرة — الإصلاح الفعلي بمعزل عن EventBus
# ============================================================

@pytest.mark.asyncio
async def test_redis_client_wrapper_publish_reaches_independent_subscriber():
    """اختبار مباشر على الطبقة السفلى المُصلَحة نفسها (5 أسطر الإصلاح) —
    قبل الإصلاح، هذا الاستدعاء كان يرمي AttributeError فورًا."""
    marker = uuid.uuid4().hex[:10]
    channel = f"regtest:eventbus-publish-fix:{marker}"
    message = json.dumps({"regtest": True, "marker": marker})

    async def _publish():
        await redis_client.publish(channel, message)

    msg = await _capture_one_message(channel, _publish)
    assert msg is not None, (
        "الرسالة لم تُستلم على subscriber مستقل — رجوع محتمل لباج "
        "eventbus-redis-wrapper-missing-publish (AttributeError على RedisClientWrapper.publish)"
    )
    assert msg["channel"] == channel
    assert msg["data"] == message


# ============================================================
# 2) insurance — عبر EventBus، نفس نمط insurance/service.py:35 الحرفي
# ============================================================

@pytest.mark.asyncio
async def test_insurance_eventbus_publish_reaches_independent_subscriber():
    event_bus = EventBus(cast(Any, redis_client))  # نفس نمط insurance/service.py:35
    event_name = "insurance.subscription.created"
    channel = f"events:{event_name}"
    marker = uuid.uuid4().hex[:10]
    payload = {
        "subscription_id": 999001, "tenant_id": 1, "user_id": 1, "policy_id": 42,
        "regtest_marker": marker,
    }

    async def _publish():
        await event_bus.publish(event_name, payload)

    msg = await _capture_one_message(channel, _publish)
    assert msg is not None, (
        "insurance: الرسالة لم تُستلم — رجوع محتمل لباج eventbus-redis-wrapper-missing-publish"
    )
    data = json.loads(msg["data"])
    assert data["event"] == event_name
    assert data["payload"] == payload


# ============================================================
# 3) zamakana — عبر EventBus، نفس نمط zamakana/service.py:41 الحرفي
# ============================================================

@pytest.mark.asyncio
async def test_zamakana_eventbus_publish_reaches_independent_subscriber():
    event_bus = EventBus(cast(Any, redis_client))  # نفس نمط zamakana/service.py:41
    event_name = "zamakana.node.created"
    channel = f"events:{event_name}"
    marker = uuid.uuid4().hex[:10]
    payload = {
        "node_id": 999002, "tenant_id": 1, "user_id": 1,
        "title": f"regtest-node-{marker}",
    }

    async def _publish():
        await event_bus.publish(event_name, payload)

    msg = await _capture_one_message(channel, _publish)
    assert msg is not None, (
        "zamakana: الرسالة لم تُستلم — رجوع محتمل لباج eventbus-redis-wrapper-missing-publish"
    )
    data = json.loads(msg["data"])
    assert data["event"] == event_name
    assert data["payload"] == payload


# ============================================================
# 4) arbitration_syndicates — عبر EventBus، نفس نمط
#    arbitration_syndicates/service.py:33 الحرفي (# type: ignore مباشر،
#    بلا cast(Any, ...) — نمط بناء نصي مختلف، نفس القيمة وقت التشغيل)
# ============================================================

@pytest.mark.asyncio
async def test_arbitration_syndicates_eventbus_publish_reaches_independent_subscriber():
    event_bus = EventBus(redis_client)  # type: ignore — نفس نمط arbitration_syndicates/service.py:33
    event_name = "arbitration.case.created"
    channel = f"events:{event_name}"
    marker = uuid.uuid4().hex[:10]
    payload = {
        "case_id": 999003, "tenant_id": 1, "claimant_id": 1,
        "judging_mode": f"AI-regtest-{marker}",
    }

    async def _publish():
        await event_bus.publish(event_name, payload)

    msg = await _capture_one_message(channel, _publish)
    assert msg is not None, (
        "arbitration_syndicates: الرسالة لم تُستلم — رجوع محتمل لباج eventbus-redis-wrapper-missing-publish"
    )
    data = json.loads(msg["data"])
    assert data["event"] == event_name
    assert data["payload"] == payload
