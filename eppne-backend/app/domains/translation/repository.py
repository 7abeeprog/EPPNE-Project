# app/domains/translation/repository.py (الإصدار النهائي المتكامل)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func as sa_func
from typing import Optional, List
from app.domains.translation.models import TranslationCache, TranslationRequestLog, SupportedLanguage

class TranslationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # --- عمليات ذاكرة التخزين المؤقت (بدون Commit) ---
    async def get_cache_by_hash(self, tenant_id: int, text_hash: str) -> Optional[TranslationCache]:
        result = await self.db.execute(
            select(TranslationCache).where(
                TranslationCache.tenant_id == tenant_id,
                TranslationCache.text_hash == text_hash
            )
        )
        return result.scalar_one_or_none()

    async def save_cache(self, tenant_id: int, text_hash: str, original: str, 
                         source_lang: str, target_lang: str, translated: str):
        # التحقق من وجود الكائن أولاً (لتجنب سباق التحديثات)
        cache = await self.get_cache_by_hash(tenant_id, text_hash)
        if cache:
            translations_dict = dict(cache.translations)
            translations_dict[target_lang] = translated
            cache.translations = translations_dict
        else:
            cache = TranslationCache(
                tenant_id=tenant_id,
                text_hash=text_hash,
                original_text=original,
                source_lang=source_lang,
                translations={target_lang: translated}
            )
            self.db.add(cache)
        # لا نقوم بـ commit() هنا، يُترك للـ Service

    async def increment_hit_count(self, cache_id: int):
        # تحديث ذري بدون الحاجة لجلب الكائن أولاً
        await self.db.execute(
            update(TranslationCache)
            .where(TranslationCache.id == cache_id)
            .values(hit_count=TranslationCache.hit_count + 1)
        )

    # --- سجلات التدقيق (بدون Commit) ---
    async def log_request(self, tenant_id: int, user_id: Optional[int], 
                          source: str, target: str, length: int, 
                          used_cache: bool, ip: Optional[str], 
                          ua: Optional[str], idempotency_key: Optional[str],
                          cost: str = "0"):
        log = TranslationRequestLog(
            tenant_id=tenant_id, 
            user_id=user_id, 
            source_lang=source, 
            target_lang=target,
            text_length=length, 
            used_cache=used_cache,
            ip_address=ip,
            user_agent=ua,
            idempotency_key=idempotency_key,
            cost_mrusdt=cost
        )
        self.db.add(log)

    # --- اللغات المدعومة ---
    async def list_supported_languages(self) -> List[SupportedLanguage]:
        result = await self.db.execute(
            select(SupportedLanguage).where(SupportedLanguage.is_active == True)
        )
        return result.scalars().all()