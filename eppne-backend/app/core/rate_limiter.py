# app/core/rate_limiter.py
import functools
import time
from typing import Optional
from fastapi import Request
from app.core.redis_client import redis_client
from app.core.errors import RateLimitError

RATE_LIMIT_PREFIX = "rate_limit:"

def rate_limit(max_requests: int, window_seconds: int = 60):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            request: Optional[Request] = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                return await func(*args, **kwargs)

            client_ip = request.client.host if request.client else "unknown"
            path = request.url.path
            key = f"{RATE_LIMIT_PREFIX}{path}:{client_ip}"
            
            current_time = int(time.time() * 1000)
            min_score = current_time - (window_seconds * 1000)
            
            client = await redis_client.get_client()
            
            lua_script = """
            local key = KEYS[1]
            local now = tonumber(ARGV[1])
            local min_score = tonumber(ARGV[2])
            local max_requests = tonumber(ARGV[3])
            local window_ms = tonumber(ARGV[4])
            
            redis.call('ZREMRANGEBYSCORE', key, 0, min_score)
            local current_count = redis.call('ZCARD', key)
            
            if current_count < max_requests then
                redis.call('ZADD', key, now, now .. ':' .. math.random())
                redis.call('PEXPIRE', key, window_ms)
                return 1
            else
                return 0
            end
            """
            
            try:
                # 🔥 إضافة # type: ignore لتجاوز تحذير Pylance حول Awaitable
                result = await client.eval(  # type: ignore
                    lua_script,
                    1,
                    key,
                    str(current_time),
                    str(min_score),
                    str(max_requests),
                    str(window_seconds * 1000)
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Rate limiter error: {e}")
                return await func(*args, **kwargs)

            if result != 1:
                raise RateLimitError(
                    f"تجاوزت الحد المسموح به ({max_requests} طلب لكل {window_seconds} ثانية)."
                )
                
            return await func(*args, **kwargs)
        return wrapper
    return decorator