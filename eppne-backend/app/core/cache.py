# app/core/cache.py
import hashlib
import json
from functools import wraps
from typing import Callable
from app.core.redis_client import redis_client

def cache_result(ttl: int = 300, key_prefix: str = "cache"):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key_data = {"func": func.__name__, "args": args, "kwargs": kwargs}
            key_str = json.dumps(key_data, sort_keys=True)
            cache_key = f"{key_prefix}:{hashlib.md5(key_str.encode()).hexdigest()}"
            
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
    async def invalidate(pattern: str):
        keys = await redis_client.keys(pattern)
        if keys:
            await redis_client.delete(*keys)

    @staticmethod
    async def invalidate_cache(pattern: str):
        """هذا هو الاسم الذي يطلبه المشروع حالياً"""
        await CacheManager.invalidate(pattern)

    @staticmethod
    async def invalidate_user_cache(user_id: int):
        await CacheManager.invalidate(f"*user:{user_id}*")

    # --- إضافة للتوافقية مع الملفات القديمة ---
def invalidate_cache(pattern: str):
    """دالة توافقية تمنع ظهور ImportError في القطاعات التي تستخدم الاسم القديم"""
    import asyncio
    # نقوم بتشغيل دالة الإلغاء بشكل متزامن للتوافق
    return asyncio.run(CacheManager.invalidate(pattern))
# ------------------------------------------