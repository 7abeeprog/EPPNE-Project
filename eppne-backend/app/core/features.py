# app/core/features.py
from app.core.redis_client import redis_client
import json

# مفاتيح Redis للنظام
SYSTEM_SUSPENDED_KEY = "system:ai_agents:suspended"
SYSTEM_SUSPENDED_TTL = 3600 * 24 * 30  # 30 يوم

class SystemFeatures:
    @staticmethod
    async def get_system_suspended() -> bool:
        """
        قراءة حالة النظام العامة من Redis (Fast Path).
        إذا لم يكن المفتاح موجوداً، نفترض أن النظام يعمل (False).
        """
        value = await redis_client.get(SYSTEM_SUSPENDED_KEY)
        if value is None:
            return False
        try:
            return json.loads(value) == True
        except:
            return False

    @staticmethod
    async def set_system_suspended(status: bool):
        """
        تحديث حالة النظام في Redis (يُستدعى من لوحة الإدارة).
        """
        await redis_client.setex(
            SYSTEM_SUSPENDED_KEY,
            SYSTEM_SUSPENDED_TTL,
            json.dumps(status)
        )