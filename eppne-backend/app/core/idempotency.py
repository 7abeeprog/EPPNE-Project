# app/core/idempotency.py
"""
نظام منع التكرار (Idempotency) للعمليات المالية والحرجة.
"""
import json
import logging
from typing import Any, Optional, Callable, Awaitable
from app.core.redis_client import redis_client
from app.core.errors import IdempotencyError

logger = logging.getLogger(__name__)

DEFAULT_IDEMPOTENCY_TTL_SECONDS = 86400  # 24 ساعة
IDEMPOTENCY_KEY_PREFIX = "idempotent:"


async def check_idempotency(key: str, ttl_seconds: int = DEFAULT_IDEMPOTENCY_TTL_SECONDS) -> bool:
    """التحقق من المفتاح وحجزه ذرياً باستخدام SET NX."""
    redis_key = f"{IDEMPOTENCY_KEY_PREFIX}{key}"
    client = await redis_client.get_client()
    
    # 🔥 nx=True تعني Set if Not eXists
    is_new = await client.set(redis_key, "LOCKED", ex=ttl_seconds, nx=True)
    return is_new is True


async def store_idempotency_result(key: str, result: Any) -> None:
    """تخزين نتيجة العملية بعد النجاح."""
    redis_key = f"{IDEMPOTENCY_KEY_PREFIX}{key}"
    client = await redis_client.get_client()
    serialized = json.dumps(result, default=str, ensure_ascii=False)
    await client.set(redis_key, serialized, ex=DEFAULT_IDEMPOTENCY_TTL_SECONDS)


async def get_idempotency_result(key: str) -> Optional[Any]:
    """استرجاع النتيجة المخزنة مسبقاً."""
    redis_key = f"{IDEMPOTENCY_KEY_PREFIX}{key}"
    client = await redis_client.get_client()
    cached = await client.get(redis_key)
    
    if cached is None or cached == "LOCKED":
        return None
    try:
        return json.loads(cached)
    except json.JSONDecodeError:
        logger.warning(f"Corrupted idempotency result for key: {key}")
        return None


async def safe_execute_with_idempotency(
    key: str, 
    func: Callable[[], Awaitable[Any]], 
    ttl_seconds: int = DEFAULT_IDEMPOTENCY_TTL_SECONDS
) -> Any:
    """تنفيذ آمن مع منع التكرار."""
    is_allowed = await check_idempotency(key, ttl_seconds)
    
    if not is_allowed:
        cached_result = await get_idempotency_result(key)
        if cached_result is not None:
            logger.info(f"🔄 Idempotency hit for key: {key}")
            return cached_result
        raise IdempotencyError("Duplicate request is still processing, please wait.")
    
    try:
        result = await func()
        await store_idempotency_result(key, result)
        return result
    except Exception as e:
        redis_key = f"{IDEMPOTENCY_KEY_PREFIX}{key}"
        client = await redis_client.get_client()
        await client.delete(redis_key)
        logger.error(f"❌ Idempotent execution failed: {e}")
        raise