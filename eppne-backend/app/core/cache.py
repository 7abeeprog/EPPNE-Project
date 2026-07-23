# app/core/cache.py
import hashlib
import json
from functools import wraps
from typing import Callable, Any
from app.core.redis_client import redis_client

CACHE_KEY_PREFIX = "cache:"

def cache_result(ttl: int = 300, key_prefix: str = "cache"):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key_data = {"func": func.__name__, "args": args, "kwargs": kwargs}
            key_str = json.dumps(key_data, sort_keys=True, default=str)
            cache_key = f"{CACHE_KEY_PREFIX}{key_prefix}:{hashlib.md5(key_str.encode()).hexdigest()}"
            
            cached = await redis_client.get_json(cache_key)
            if cached is not None:
                return cached
            
            result = await func(*args, **kwargs)
            await redis_client.set_json(cache_key, result, ex=ttl)
            return result
        return wrapper
    return decorator


class CacheManager:
    @staticmethod
    async def invalidate(pattern: str) -> int:
        """إبطال الكاش باستخدام SCAN (آمن تماماً مع int)."""
        client = await redis_client.get_client()
        pattern_full = f"{CACHE_KEY_PREFIX}{pattern}" if not pattern.startswith(CACHE_KEY_PREFIX) else pattern
        
        deleted_count = 0
        cursor = 0  # 🔥 يجب أن تكون int وليس str
        while True:
            cursor, keys = await client.scan(cursor, match=pattern_full, count=100)
            if keys:
                deleted_count += await client.delete(*keys)
            if cursor == 0:
                break
        return deleted_count

    @staticmethod
    async def invalidate_user_cache(user_id: int) -> int:
        return await CacheManager.invalidate(f"*user:{user_id}*")

    @staticmethod
    async def invalidate_by_tag(tag: str) -> int:
        return await CacheManager.invalidate(f"*{tag}*")


async def invalidate_cache(pattern: str) -> int:
    """دالة توافقية Async لإبطال الكاش."""
    return await CacheManager.invalidate(pattern)