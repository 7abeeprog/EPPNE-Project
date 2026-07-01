from fastapi import Request, HTTPException
from redis import asyncio as aioredis
from app.core.config import settings

redis_client = None

async def get_redis():
    global redis_client
    if redis_client is None:
        redis_client = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client

async def rate_limit(request: Request, key: str, limit: int, per_seconds: int = 60):
    redis = await get_redis()
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, per_seconds)
    if current > limit:
        raise HTTPException(status_code=429, detail="تم تجاوز حد الطلبات المسموح به")