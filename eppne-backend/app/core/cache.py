# app/core/cache.py
import functools
import json
from redis import asyncio as aioredis
from app.core.config import settings

# إنشاء عميل Redis
redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

def cache_result(expire=300):
    """مزخرف لتخزين نتائج الدوال في Redis"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # إنشاء مفتاح فريد بناءً على اسم الدالة والمعاملات
            key = f"cache:{func.__name__}:{json.dumps(args)}:{json.dumps(kwargs)}"
            
            # محاولة جلب النتيجة من الكاش
            cached = await redis_client.get(key)
            if cached:
                return json.loads(cached)
            
            # تنفيذ الدالة الأصلية إذا لم يوجد كاش
            result = await func(*args, **kwargs)
            
            # حفظ النتيجة في Redis
            await redis_client.setex(key, expire, json.dumps(result))
            return result
        return wrapper
    return decorator

async def invalidate_cache(func_name: str):
    """دالة لمسح الكاش عند حدوث تحديث للبيانات"""
    keys = await redis_client.keys(f"cache:{func_name}:*")
    if keys:
        await redis_client.delete(*keys)