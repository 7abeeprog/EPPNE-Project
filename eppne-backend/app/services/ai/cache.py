# app/services/ai/cache.py
"""
آليات التخزين المؤقت للذكاء الاصطناعي (Semantic + Prompt Caching)
"""

import hashlib
import json
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

from app.core.redis_client import redis_client


class SemanticCache:
    """
    التخزين المؤقت الدلالي (Semantic Caching)
    يخزن نتائج الأسئلة المتكررة في Redis مع صلاحية 24 ساعة
    """

    CACHE_TTL = 86400  # 24 ساعة
    CACHE_PREFIX = "ai:semantic:"

    @classmethod
    def _generate_key(cls, prompt: str, model_id: str, context: Optional[Dict] = None) -> str:
        """توليد مفتاح فريد للطلب"""
        # تنظيف المطالبة (إزالة المسافات الزائدة)
        clean_prompt = " ".join(prompt.strip().split())
        
        # بناء البيانات للتجزئة
        data = {
            "prompt": clean_prompt,
            "model": model_id,
            "context": context or {}
        }
        key_str = json.dumps(data, sort_keys=True)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"{cls.CACHE_PREFIX}{key_hash}"

    @classmethod
    async def get(cls, prompt: str, model_id: str, context: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """استرجاع نتيجة من التخزين المؤقت"""
        cache_key = cls._generate_key(prompt, model_id, context)
        cached = await redis_client.get_json(cache_key)
        if cached:
            # تحديث وقت الوصول (للبقاء في الكاش لفترة أطول)
            await redis_client.expire(cache_key, cls.CACHE_TTL)
            return cached
        return None

    @classmethod
    async def set(cls, prompt: str, model_id: str, result: Dict[str, Any], context: Optional[Dict] = None) -> None:
        """تخزين النتيجة في التخزين المؤقت"""
        cache_key = cls._generate_key(prompt, model_id, context)
        # إضافة معلومات إضافية عن التخزين
        result_with_meta = {
            **result,
            "_cached_at": datetime.utcnow().isoformat(),
            "_cached_model": model_id,
        }
        await redis_client.set_json(cache_key, result_with_meta, ex=cls.CACHE_TTL)


class PromptCache:
    """
    التخزين المؤقت للمطالبات (Prompt Caching)
    يستخدم خاصية التخزين المؤقت في Mistral و Kimi
    """

    CACHE_PREFIX = "ai:prompt:"
    CACHE_TTL = 3600  # 1 ساعة

    @classmethod
    def _generate_key(cls, system_prompt: str, user_prompt: str) -> str:
        """توليد مفتاح للمطالبة المؤقتة"""
        data = {
            "system": system_prompt[:500],  # فقط أول 500 حرف لتمثيل المطالبة
            "user": user_prompt[:500],
        }
        key_str = json.dumps(data, sort_keys=True)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"{cls.CACHE_PREFIX}{key_hash}"

    @classmethod
    async def get_cached_response(cls, system_prompt: str, user_prompt: str, model_id: str) -> Optional[str]:
        """استرجاع رد مخزن مؤقتاً"""
        cache_key = cls._generate_key(system_prompt, user_prompt)
        cached = await redis_client.get_json(cache_key)
        if cached and cached.get("model") == model_id:
            return cached.get("response")
        return None

    @classmethod
    async def set_cached_response(cls, system_prompt: str, user_prompt: str, model_id: str, response: str) -> None:
        """تخزين رد مؤقتاً"""
        cache_key = cls._generate_key(system_prompt, user_prompt)
        await redis_client.set_json(cache_key, {
            "model": model_id,
            "response": response,
            "cached_at": datetime.utcnow().isoformat()
        }, ex=cls.CACHE_TTL)


class BatchProcessor:
    """
    التشغيل الدفعي (Batch Processing)
    لتجميع الطلبات غير العاجلة وإرسالها دفعة واحدة بخصم 50%
    """

    BATCH_KEY = "ai:batch:queue"
    BATCH_SIZE = 50
    BATCH_INTERVAL = 60  # ثانية

    @classmethod
    async def add_to_batch(cls, request: Dict[str, Any]) -> str:
        """إضافة طلب إلى قائمة التشغيل الدفعي"""
        batch_id = f"batch_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(str(request).encode()).hexdigest()[:8]}"
        await redis_client.lpush(cls.BATCH_KEY, json.dumps({
            "batch_id": batch_id,
            "request": request,
            "created_at": datetime.utcnow().isoformat()
        }))
        return batch_id

    @classmethod
    async def get_batch(cls, size: int = BATCH_SIZE) -> list:
        """استرجاع دفعة من الطلبات للمعالجة"""
        batch = []
        for _ in range(size):
            item = await redis_client.rpop(cls.BATCH_KEY)
            if item:
                batch.append(json.loads(item))
            else:
                break
        return batch