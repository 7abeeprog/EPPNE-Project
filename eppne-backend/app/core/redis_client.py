# app/core/redis_client.py
import redis.asyncio as redis
from redis.asyncio import ConnectionPool
from typing import Optional
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisClientWrapper:
    """
    غلاف آمن لعميل Redis مع دعم إعادة المحاولة وإدارة الاتصال.
    """
    _client: Optional[redis.Redis] = None
    _pool: Optional[ConnectionPool] = None

    def __init__(self):
        self._client = None
        self._pool = None

    async def initialize(self) -> redis.Redis:
        """
        تهيئة عميل Redis باستخدام إعدادات النظام.
        يجب استدعاؤها عند بدء التشغيل (Lifespan).
        """
        if self._client:
            return self._client

        try:
            # جلب الإعدادات من ملف الإعدادات (settings)
            redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
            redis_password = getattr(settings, "REDIS_PASSWORD", None)
            max_connections = getattr(settings, "REDIS_MAX_CONNECTIONS", 20)

            logger.info(f"🔄 جاري الاتصال بـ Redis على: {redis_url.split('@')[-1] if '@' in redis_url else redis_url}")

            # إنشاء مجمع اتصالات (Connection Pool) لتحسين الأداء مع +10M مستخدم
            self._pool = ConnectionPool.from_url(
                redis_url,
                password=redis_password,
                max_connections=max_connections,
                decode_responses=True,  # تحويل البايت إلى سلسلة نصية تلقائياً
                health_check_interval=30,
                retry_on_timeout=True
            )

            self._client = redis.Redis(connection_pool=self._pool)

            # التحقق من الاتصال (Ping)
            await self._client.ping()
            logger.info("✅ تم الاتصال بـ Redis بنجاح.")
            return self._client

        except Exception as e:
            logger.error(f"❌ فشل الاتصال بـ Redis: {str(e)}")
            # يمكنك اختيار رفع الاستثناء أو الاستمرار في وضع Offline Mode
            raise ConnectionError(f"تعذر الاتصال بـ Redis: {str(e)}")

    async def get_client(self) -> redis.Redis:
        """
        إرجاع العميل الحالي، وإن لم يكن موجوداً يقوم بتهيئته.
        """
        if not self._client:
            return await self.initialize()
        return self._client

    async def close(self):
        """
        إغلاق جميع الاتصالات بشكل آمن (يُستدعى عند إيقاف التطبيق).
        """
        if self._client:
            await self._client.close(close_connection_pool=True)
            logger.info("🔒 تم إغلاق اتصال Redis.")
            self._client = None
            self._pool = None

    # ========== عمليات مساعدة سريعة (اختصارات) ==========
    async def ping(self):
        client = await self.get_client()
        return await client.ping()

    async def get(self, key: str) -> Optional[str]:
        client = await self.get_client()
        return await client.get(key)

    async def setex(self, key: str, time: int, value: str):
        client = await self.get_client()
        return await client.setex(key, time, value)

    async def set(self, key: str, value: str, ex: Optional[int] = None):
        client = await self.get_client()
        return await client.set(key, value, ex=ex)

    async def delete(self, key: str):
        client = await self.get_client()
        return await client.delete(key)

    async def exists(self, key: str) -> bool:
        client = await self.get_client()
        return await client.exists(key) > 0

    async def incr(self, key: str) -> int:
        client = await self.get_client()
        return await client.incr(key)

    async def expire(self, key: str, time: int):
        client = await self.get_client()
        return await client.expire(key, time)

    # ========== عمليات التخزين المؤقت الجماعية (للـ Cache Aside) ==========
    async def get_json(self, key: str):
        """جلب قيمة JSON وتحويلها إلى قاموس (dict)"""
        val = await self.get(key)
        if val:
            import json
            return json.loads(val)
        return None

    async def set_json(self, key: str, value: dict, ex: Optional[int] = None):
        """تخزين قاموس (dict) كـ JSON في Redis"""
        import json
        return await self.set(key, json.dumps(value, default=str), ex=ex)

# ==========================================
# إنشاء كائن عام واحد (Singleton) لاستخدامه في جميع أنحاء التطبيق
# ==========================================
redis_client = RedisClientWrapper()

# ==========================================
# دالة مساعدة للاستيراد المباشر في الـ Lifespan (main.py)
# ==========================================
async def get_redis() -> redis.Redis:
    """تابع تبعية (Dependency) لـ FastAPI للحصول على عميل Redis"""
    return await redis_client.get_client()