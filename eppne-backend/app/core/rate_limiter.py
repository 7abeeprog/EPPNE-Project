# app/core/rate_limiter.py
import functools
from fastapi import Request
from redis import asyncio as aioredis
from app.core.config import settings
from app.core.errors import RateLimitError

redis_client = None

async def get_redis():
    global redis_client
    if redis_client is None:
        redis_client = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client

def rate_limit(max_requests: int, window_seconds: int = 60):
    """
    مزخرف (Decorator) لتحديد معدل الطلبات.
    يتم استخدامه فوق الـ Endpoints للحد من الهجمات أو الضغط.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 1. محاولة استخراج كائن Request من معاملات الـ Endpoint
            request: Request = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            # إذا لم يتم العثور على Request، نستمر في التنفيذ (لبيئات الاختبار)
            if not request:
                return await func(*args, **kwargs)

            # 2. الاتصال بـ Redis
            redis = await get_redis()
            
            # 3. إنشاء مفتاح فريد يعتمد على IP المستخدم ومسار الـ API
            client_ip = request.client.host if request.client else "unknown"
            key = f"rate_limit:{request.url.path}:{client_ip}"
            
            # 4. زيادة العداد والتحقق
            current = await redis.incr(key)
            if current == 1:
                # تعيين وقت انتهاء الصلاحية عند أول طلب
                await redis.expire(key, window_seconds)
            
            if current > max_requests:
                # نستخدم خطأ النظام السيادي المخصص الذي أنشأناه سابقاً
                raise RateLimitError("تم تجاوز حد الطلبات المسموح به، يرجى المحاولة لاحقاً")
                
            return await func(*args, **kwargs)
        return wrapper
    return decorator