# app/services/ai/router.py
"""
نظام التوجيه الذكي لتوزيع الطلبات بين النماذج الأربعة
"""

import random
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from app.services.ai.models import (
    AIModelId,
    ModelConfig,
    MODEL_CONFIGS,
    DEFAULT_ROUTING_PERCENTAGES,
    ModelTier,
    TIER_MODELS,
)
from app.services.ai.cache import SemanticCache, PromptCache, BatchProcessor
from app.services.ai.cost_tracker import CostTracker


class TaskType(str, Enum):
    """أنواع المهام لتوجيهها إلى النموذج المناسب"""
    TRANSLATION = "translation"           # → Hunyuan (مجاني)
    ARABIC_CHAT = "arabic_chat"           # → Mistral Saba
    COMPLEX_ANALYSIS = "complex_analysis" # → Kimi K2.6
    FALLBACK = "fallback"                 # → Qwen


class AIRouter:
    """
    التوجيه الذكي للطلبات بين النماذج الأربعة
    يستخدم نسب التوزيع المحددة مع إمكانية التعديل الديناميكي
    """

    # النسب الافتراضية
    _routing_percentages = DEFAULT_ROUTING_PERCENTAGES.copy()
    
    # العداد الدوري لتوزيع الطلبات
    _counter = 0

    @classmethod
    def get_model_for_task(cls, task_type: TaskType, language: Optional[str] = None) -> AIModelId:
        """تحديد النموذج المناسب لنوع المهمة"""
        if task_type == TaskType.TRANSLATION:
            return AIModelId.HUNYUAN_MT
        
        elif task_type == TaskType.ARABIC_CHAT:
            # إذا كانت اللغة عربية أو مصرية، استخدم Mistral Saba
            if language and language in ("ar", "ar-EG"):
                return AIModelId.MISTRAL_SABA
            # وإلا استخدم التوزيع العادي
            return cls._select_by_percentage()
        
        elif task_type == TaskType.COMPLEX_ANALYSIS:
            # المهام المعقدة تذهب مباشرة إلى Kimi
            return AIModelId.KIMI_K2_6
        
        else:  # FALLBACK أو غير معروف
            return cls._select_by_percentage()

    @classmethod
    def _select_by_percentage(cls) -> AIModelId:
        """توزيع الطلبات حسب النسب المحددة (Round-Robin مع وزن)"""
        cls._counter += 1
        # استخدام عداد دوري مع الأوزان
        total = sum(cls._routing_percentages.values())
        rand = random.randint(1, total)
        
        cumulative = 0
        for model_id, percentage in cls._routing_percentages.items():
            cumulative += percentage
            if rand <= cumulative:
                return model_id
        
        return AIModelId.KIMI_K2_6  # القيمة الافتراضية

    @classmethod
    def update_routing_percentages(cls, new_percentages: Dict[AIModelId, int]) -> None:
        """تحديث نسب التوزيع (للاستخدام الديناميكي)"""
        # التأكد من أن المجموع 100
        total = sum(new_percentages.values())
        if total != 100:
            raise ValueError(f"مجموع النسب يجب أن يكون 100، لكنه {total}")
        cls._routing_percentages = new_percentages

    @classmethod
    async def route_request(
        cls,
        prompt: str,
        task_type: TaskType = TaskType.ARABIC_CHAT,
        language: Optional[str] = None,
        system_prompt: Optional[str] = None,
        context: Optional[Dict] = None,
        use_cache: bool = True,
        use_batch: bool = False,
        force_model: Optional[AIModelId] = None,
    ) -> Tuple[AIModelId, Dict[str, Any]]:
        """
        توجيه الطلب ومعالجته مع التخزين المؤقت والتكلفة
        
        Args:
            prompt: نص الاستعلام
            task_type: نوع المهمة
            language: لغة المستخدم (لتحديد النموذج)
            system_prompt: رسالة النظام
            context: سياق إضافي
            use_cache: استخدام التخزين المؤقت
            use_batch: استخدام التشغيل الدفعي
            force_model: فرض نموذج معين (تجاوز التوجيه)
        
        Returns:
            (النموذج المستخدم، النتيجة)
        """
        # تحديد النموذج
        if force_model:
            model_id = force_model
        else:
            model_id = cls.get_model_for_task(task_type, language)
        
        config = MODEL_CONFIGS.get(model_id)
        if not config or not config.is_active:
            # إذا كان النموذج غير نشط، استخدم البديل
            model_id = AIModelId.QWEN_3_7_MAX
        
        # 1. محاولة التخزين المؤقت الدلالي
        if use_cache:
            cached_result = await SemanticCache.get(prompt, model_id.value, context)
            if cached_result:
                # تحديث التكلفة (لا تكلفة لأنها من الكاش)
                return model_id, {
                    **cached_result,
                    "_from_cache": True,
                    "_cached": True,
                }
        
        # 2. محاولة التخزين المؤقت للمطالبات (خاص بـ Mistral و Kimi)
        if use_cache and system_prompt and config.supports_prompt_caching:
            cached_response = await PromptCache.get_cached_response(
                system_prompt, prompt, model_id.value
            )
            if cached_response:
                return model_id, {
                    "text": cached_response,
                    "_from_cache": True,
                    "_cached": True,
                    "_prompt_cached": True,
                }
        
        # 3. تشغيل دفعي (للمهام غير العاجلة)
        if use_batch:
            batch_id = await BatchProcessor.add_to_batch({
                "prompt": prompt,
                "model_id": model_id.value,
                "system_prompt": system_prompt,
                "context": context,
                "task_type": task_type,
            })
            return model_id, {
                "_batch": True,
                "_batch_id": batch_id,
                "message": "تم إضافة الطلب إلى قائمة التشغيل الدفعي"
            }
        
        # 4. معالجة عادية (ستنفذ في المحرك)
        return model_id, {
            "_pending": True,
            "_model_id": model_id.value,
            "_config": config.dict(),
        }