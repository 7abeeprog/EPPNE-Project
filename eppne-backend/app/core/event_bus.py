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