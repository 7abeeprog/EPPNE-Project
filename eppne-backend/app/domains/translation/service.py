# app/domains/translation/service.py (الإصدار النهائي المتكامل)
from sqlalchemy.ext.asyncio import AsyncSession
from hashlib import sha256
import json
from typing import Optional
import httpx
import asyncio
from decimal import Decimal

from app.domains.translation.repository import TranslationRepository
from app.domains.translation.schemas import (
    TranslateRequest, TranslateResponse, 
    BatchTranslateRequest, ChatTranslateRequest, 
    ChatTranslateResponse
)
from app.core.config import settings
from app.core.redis_client import redis_client as get_redis_client

# وهمي مؤقت لقطاع المالية (سيتم ربطه لاحقاً)
class WalletServiceStub:
    @staticmethod
    async def debit(user_id: int, amount_mrusdt: str, reason: str):
        # هنا سيتم استدعاء `/finance/wallet/debit` فعلياً
        return True 

class TranslationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TranslationRepository(db)
        self.redis = get_redis_client()

    async def _get_cached_from_redis(self, tenant_id: int, text_hash: str, target_lang: str) -> Optional[str]:
        key = f"trans:{tenant_id}:{text_hash}:{target_lang}"
        val = await self.redis.get(key)
        return val.decode('utf-8') if val else None

    async def _set_cached_to_redis(self, tenant_id: int, text_hash: str, target_lang: str, translated: str):
        key = f"trans:{tenant_id}:{text_hash}:{target_lang}"
        # وضع صلاحية 30 يومًا لتخفيف الضغط عن PostgreSQL
        await self.redis.setex(key, 2592000, translated)

    async def _get_idempotency(self, key: str) -> Optional[str]:
        if not key:
            return None
        val = await self.redis.get(f"idem:{key}")
        return val.decode('utf-8') if val else None

    async def _set_idempotency(self, key: str, response_json: str):
        if not key:
            return
        # تخزين النتيجة لمدة 24 ساعة لمنع تكرار العمليات
        await self.redis.setex(f"idem:{key}", 86400, response_json)

    async def _debit_wallet(self, user_id: int, text_length: int) -> str:
        """احتساب التكلفة وخصمها (وحدة MRUSDT)"""
        # مثال: 0.001 MRUSDT لكل 1000 حرف، بحد أدنى 0.0001
        chars = max(text_length, 1)
        cost = Decimal('0.001') * (Decimal(chars) / Decimal('1000'))
        cost = max(cost, Decimal('0.0001'))
        cost_str = f"{cost:.8f}"  # دقة عالية
        
        # استدعاء خدمة المحفظة (تم استبداله بالـ Stub هنا)
        # await WalletServiceStub.debit(user_id, cost_str, f"Translation of {chars} chars")
        return cost_str

    async def _call_translation_api(self, text: str, source_lang: str, target_lang: str, context: str = None) -> str:
        """استدعاء Gemini API مع إعادة المحاولة"""
        # الرجاء وضع مفتاح Gemini في settings.GEMINI_API_KEY
        gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
        prompt = f"Translate this text from {source_lang} to {target_lang} (Context: {context or 'general'}):\n\n{text}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(3):  # إعادة المحاولة 3 مرات
                try:
                    response = await client.post(
                        f"{gemini_url}?key={settings.GEMINI_API_KEY}",
                        json={
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"temperature": 0.1}
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    translated = data["candidates"][0]["content"]["parts"][0]["text"]
                    return translated.strip()
                except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
                    if attempt == 2:
                        raise Exception(f"Translation API failed after retries: {str(e)}")
                    await asyncio.sleep(2 ** attempt)  # Exponential Backoff

    async def translate(self, tenant_id: int, user_id: Optional[int], request: TranslateRequest, 
                        ip: Optional[str] = None, ua: Optional[str] = None) -> TranslateResponse:
        text = request.text.strip()
        if not text:
            return TranslateResponse(translated_text="", source_lang=request.source_lang, 
                                     target_lang=request.target_lang, from_cache=False, cost_mrusdt="0")

        # 1. التحقق من Idempotency (إذا أرسل العميل مفتاحاً)
        idem_key = request.idempotency_key or f"{tenant_id}:{user_id}:{text}:{request.target_lang}"
        cached_idem = await self._get_idempotency(idem_key)
        if cached_idem:
            data = json.loads(cached_idem)
            return TranslateResponse(**data)

        # 2. حساب الهاش
        text_hash = sha256(f"{text}:{request.source_lang}".encode()).hexdigest()

        # 3. البحث في Redis (أولاً)
        redis_result = await self._get_cached_from_redis(tenant_id, text_hash, request.target_lang)
        if redis_result:
            # تسجيل في الخلفية (Background) دون انتظار - تحسين أداء
            asyncio.create_task(self._log_hit_and_commit(tenant_id, user_id, text_hash, request, ip, ua, used_cache=True))
            return TranslateResponse(
                translated_text=redis_result,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                from_cache=True,
                cost_mrusdt="0"
            )

        # 4. البحث في PostgreSQL (ثانياً)
        cached_db = await self.repo.get_cache_by_hash(tenant_id, text_hash)
        if cached_db and cached_db.translations.get(request.target_lang):
            translated = cached_db.translations[request.target_lang]
            # تخزين في Redis للزوار القادمين
            await self._set_cached_to_redis(tenant_id, text_hash, request.target_lang, translated)
            asyncio.create_task(self._log_hit_and_commit(tenant_id, user_id, text_hash, request, ip, ua, used_cache=True))
            return TranslateResponse(
                translated_text=translated,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                from_cache=True,
                cost_mrusdt="0"
            )

        # 5. معالجة الدفع (خصم الرصيد) - قبل استدعاء الـ API
        cost = await self._debit_wallet(user_id, len(text))

        # 6. استدعاء API الترجمة الخارجي
        translated = await self._call_translation_api(text, request.source_lang, request.target_lang, request.context)

        # 7. حفظ النتيجة في DB (في معاملة ذرية واحدة)
        await self.repo.save_cache(tenant_id, text_hash, text, request.source_lang, request.target_lang, translated)
        
        # جلب cache_id لتحديث عداد الزيارات (في حالة وجود كاش قديم)
        cache = await self.repo.get_cache_by_hash(tenant_id, text_hash)
        if cache:
            await self.repo.increment_hit_count(cache.id)
        
        # حفظ سجل التدقيق بنفس المعاملة
        await self.repo.log_request(tenant_id, user_id, request.source_lang, request.target_lang, 
                                    len(text), used_cache=False, ip=ip, ua=ua, 
                                    idempotency_key=idem_key, cost=cost)

        # تنفيذ المعاملة الذرية (Commit واحد لكل العمليات السابقة)
        await self.db.commit()

        # 8. تخزين النتيجة في Redis للتخزين المؤقت المستقبلي
        await self._set_cached_to_redis(tenant_id, text_hash, request.target_lang, translated)

        # 9. تخزين Idempotency
        response_obj = {
            "translated_text": translated,
            "source_lang": request.source_lang,
            "target_lang": request.target_lang,
            "from_cache": False,
            "cost_mrusdt": cost
        }
        await self._set_idempotency(idem_key, json.dumps(response_obj))

        return TranslateResponse(**response_obj)

    async def _log_hit_and_commit(self, tenant_id, user_id, text_hash, request, ip, ua, used_cache):
        """تسجيل الطلبات من الـ Cache في معاملة منفصلة لتجنب إبطاء الاستجابة"""
        async with self.db.begin():  # بدء معاملة جديدة
            # جلب cache_id الفعلي لتحديث العداد
            cache = await self.repo.get_cache_by_hash(tenant_id, text_hash)
            if cache:
                await self.repo.increment_hit_count(cache.id)
            await self.repo.log_request(tenant_id, user_id, request.source_lang, request.target_lang,
                                        len(request.text), used_cache=used_cache, ip=ip, ua=ua,
                                        idempotency_key=request.idempotency_key, cost="0")
            await self.db.commit()

    async def batch_translate(self, tenant_id: int, user_id: Optional[int], request: BatchTranslateRequest,
                              ip: Optional[str] = None, ua: Optional[str] = None) -> list[str]:
        results = []
        for text in request.texts:
            resp = await self.translate(tenant_id, user_id, TranslateRequest(
                text=text,
                source_lang=request.source_lang,
                target_lang=request.target_lang
            ), ip=ip, ua=ua)
            results.append(resp.translated_text)
        return results

    async def chat_translate(self, tenant_id: int, user_id: Optional[int], request: ChatTranslateRequest,
                             ip: Optional[str] = None, ua: Optional[str] = None) -> ChatTranslateResponse:
        translated = await self.translate(tenant_id, user_id, TranslateRequest(
            text=request.message,
            source_lang="auto",
            target_lang=request.target_lang,
            context="chat_conversation"
        ), ip=ip, ua=ua)
        return ChatTranslateResponse(
            original=request.message,
            translated=translated.translated_text,
            target_lang=request.target_lang
        )