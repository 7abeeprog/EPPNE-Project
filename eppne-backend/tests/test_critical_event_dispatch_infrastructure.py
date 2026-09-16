"""
regression test لجلسة `critical-event-dispatch-infrastructure-implementation`.
تقرير الجلسة: .claude/reports/critical-event-dispatch-infrastructure-implementation-session-log.md

النطاق: بنية Critical Event Dispatch عبر Celery فوق EventBus الحالي —
بلا أي handler حقيقي (CRITICAL_EVENT_HANDLERS فاضي عمدًا حاليًا).

التعديل الفعلي في EventBus.publish() (app/core/event_bus.py):
```python
await self.redis.publish(channel, message)

if event_name in CRITICAL_EVENT_HANDLERS:
    celery_app.send_task("events.dispatch_critical_event",
                          args=[event_name, payload], queue="events")
```

هذا الملف يغطي حالتين:
1) "صفر تأثير" (القاموس فاضي فعليًا الآن): أي حدث موجود بالفعل في
   الإنتاج (insurance.subscription.created) لازم يفضل يشتغل بالضبط زي ما
   كان — redis.publish بينفذ، وصفر استدعاء لـcelery_app.send_task طالما
   الحدث مش مسجَّل في CRITICAL_EVENT_HANDLERS.
2) المسار الجديد نفسه (عبر monkeypatch مؤقت لـCRITICAL_EVENT_HANDLERS،
   بما إنه فاضي في الإنتاج ومفيش أي حدث حرج حقيقي لسه): تأكيد إن
   celery_app.send_task بتتنادى بالـname/args/queue الصح، بلا أي استثناء
   إضافي من كود الـdispatch الجديد، وإن الـtask نفسها (dispatch_critical_event_task)
   مسجَّلة في سجل Celery باسمها الصريح.
"""
import json
import uuid
from typing import Any, cast
from unittest.mock import patch

import pytest
import pytest_asyncio

from app.core.redis_client import redis_client
from app.core.event_bus import EventBus
from app.core import event_bus as event_bus_module
from app.core.celery_app import celery_app
from app.core.celery_config import task_queues, task_routes
from app.tasks.events import dispatch_critical_event_task


@pytest_asyncio.fixture(autouse=True)
async def _redis_event_loop_isolation():
    yield
    await redis_client.close()


async def _capture_one_message(channel: str, publish_action, timeout: float = 5.0):
    client = await redis_client.get_client()
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(channel)
        await pubsub.get_message(timeout=2.0)
        await publish_action()
        import asyncio
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
# 1) صفر تأثير على السلوك الحالي — القاموس فاضي فعليًا في الإنتاج
# ============================================================

@pytest.mark.asyncio
async def test_existing_event_still_publishes_with_empty_critical_handlers():
    """insurance.subscription.created — نفس نمط insurance/service.py:264
    الحرفي. لازم يفضل يشتغل بالضبط زي قبل هذه الجلسة: redis.publish
    بينفذ، subscriber مستقل بيستلم الرسالة، بلا أي استثناء إضافي."""
    event_bus = EventBus(cast(Any, redis_client))
    event_name = "insurance.subscription.created"
    channel = f"events:{event_name}"
    marker = uuid.uuid4().hex[:10]
    payload = {
        "subscription_id": 999011, "tenant_id": 1, "user_id": 1, "policy_id": 42,
        "regtest_marker": marker,
    }

    with patch.object(celery_app, "send_task") as mock_send_task:
        async def _publish():
            await event_bus.publish(event_name, payload)

        msg = await _capture_one_message(channel, _publish)

    assert msg is not None, "insurance.subscription.created: صفر رسالة — رجوع محتمل لكسر Redis Pub/Sub الحالي"
    data = json.loads(msg["data"])
    assert data["event"] == event_name
    assert data["payload"] == payload

    mock_send_task.assert_not_called()  # الحدث مش في CRITICAL_EVENT_HANDLERS (فاضي) → صفر dispatch


# ============================================================
# 2) المسار الجديد — عبر monkeypatch مؤقت لـCRITICAL_EVENT_HANDLERS
# ============================================================

@pytest.mark.asyncio
async def test_critical_event_triggers_celery_dispatch_without_breaking_redis_publish(monkeypatch):
    """بما إن CRITICAL_EVENT_HANDLERS فاضي فعليًا في الإنتاج، بنسجّل حدث
    اختباري مؤقت فيه (مش حدث إنتاجي حقيقي) عشان نتأكد إن المسار الجديد
    بيشتغل صح لما يتفعّل مستقبلًا، بلا ما نلمس أي حدث حقيقي."""
    event_name = f"regtest.critical_event.{uuid.uuid4().hex[:8]}"
    monkeypatch.setitem(event_bus_module.CRITICAL_EVENT_HANDLERS, event_name, "regtest_handler")

    event_bus = EventBus(cast(Any, redis_client))
    channel = f"events:{event_name}"
    payload = {"regtest": True}

    with patch.object(celery_app, "send_task") as mock_send_task:
        async def _publish():
            await event_bus.publish(event_name, payload)

        msg = await _capture_one_message(channel, _publish)

    assert msg is not None, "redis.publish لازم يفضل يشتغل حتى لو الحدث حرج ومتسجل"
    mock_send_task.assert_called_once_with(
        "events.dispatch_critical_event", args=[event_name, payload], queue="events"
    )


def test_dispatch_critical_event_task_registered_with_standard_shape():
    """التأكد إن الـtask الجديدة متسجلة في سجل Celery باسمها الصريح،
    وبنفس الشكل القياسي (§3 من جلسة التخطيط: bind/max_retries/acks_late)."""
    assert "events.dispatch_critical_event" in celery_app.tasks
    registered = celery_app.tasks["events.dispatch_critical_event"]
    assert registered.name == "events.dispatch_critical_event"
    assert dispatch_critical_event_task.max_retries == 3
    assert dispatch_critical_event_task.acks_late is True


def test_dispatch_critical_event_task_body_is_noop_logging_only():
    """الجسم وهمي فعلًا — logger.info بس، بلا أي استدعاء handler حقيقي
    (CRITICAL_EVENT_HANDLERS فاضي في الإنتاج، فالمسار "موجود" هيتفّذ
    كـlogger.info فقط)."""
    result = dispatch_critical_event_task.run("some.event", {"k": "v"})
    assert result is None  # صفر return value حقيقي — بنية فقط، بلا معالجة


def test_events_queue_registered_in_celery_config():
    """طابور events جديد بنفس نمط saas/commerce — Queue + route."""
    queue_names = {q.name for q in task_queues}
    assert "events" in queue_names
    assert task_routes.get("events.*", {}).get("queue") == "events"
