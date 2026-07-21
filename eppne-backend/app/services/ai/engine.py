# app/services/ai/engine.py
"""
المحرك الرئيسي الموحد للذكاء الاصطناعي
يدعم النماذج الأربعة مع التوجيه الذكي والتخزين المؤقت وتتبع التكلفة
"""

import json
from typing import Dict, Any, Optional, List, Tuple
import aiohttp
import asyncio

from app.services.ai.models import (
    AIModelId,
    ModelConfig,
    MODEL_CONFIGS,
    TaskType,
)
from app.services.ai.router import AIRouter
from app.services.ai.cache import SemanticCache, PromptCache
from app.services.ai.cost_tracker import CostTracker


class AIEngine:
    """
    المحرك الرئيسي الموحد للذكاء الاصطناعي
    """
    
    # محاكاة لمفاتيح API (سيتم استبدالها بالبيئة الفعلية)
    API_KEYS = {
        AIModelId.HUNYUAN_MT: "hunyuan-api-key",  # مجاني
        AIModelId.MISTRAL_SABA: "mistral-saba-key",
        AIModelId.KIMI_K2_6: "kimi-k2.6-key",
        AIModelId.QWEN_3_7_MAX: "qwen-3.7-max-key",
    }
    
    # محاكاة لعناوين API
    API_ENDPOINTS = {
        AIModelId.HUNYUAN_MT: "https://api.hunyuan.tencent.com/v1/chat/completions",
        AIModelId.MISTRAL_SABA: "https://api.mistral.ai/v1/chat/completions",
        AIModelId.KIMI_K2_6: "https://api.moonshot.cn/v1/chat/completions",
        AIModelId.QWEN_3_7_MAX: "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
    }
    
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """الحصول على جلسة HTTP (مع إعادة الاستخدام)"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """إغلاق الجلسة"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def generate(
        self,
        prompt: str,
        model_id: Optional[AIModelId] = None,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        language: Optional[str] = None,
        task_type: TaskType = TaskType.ARABIC_CHAT,
        use_cache: bool = True,
        use_batch: bool = False,
        force_model: Optional[AIModelId] = None,
    ) -> Dict[str, Any]:
        """
        الواجهة الرئيسية لتوليد النصوص باستخدام النموذج المناسب
        
        Args:
            prompt: نص الاستعلام
            model_id: معرف النموذج (اختياري)
            system_prompt: رسالة النظام
            max_tokens: الحد الأقصى للرد
            temperature: درجة العشوائية
            language: لغة المستخدم
            task_type: نوع المهمة
            use_cache: استخدام التخزين المؤقت
            use_batch: استخدام التشغيل الدفعي
            force_model: فرض نموذج معين
        
        Returns:
            النتيجة مع البيانات الوصفية
        """
        # 1. التوجيه الذكي
        selected_model, route_result = await AIRouter.route_request(
            prompt=prompt,
            task_type=task_type,
            language=language,
            system_prompt=system_prompt,
            use_cache=use_cache,
            use_batch=use_batch,
            force_model=force_model or model_id,
        )
        
        # 2. إذا كان الطلب في الكاش أو الدفعي، أعد النتيجة مباشرة
        if route_result.get("_from_cache") or route_result.get("_batch"):
            return {
                **route_result,
                "model": selected_model.value,
                "prompt": prompt,
            }
        
        # 3. معالجة عادية
        config = MODEL_CONFIGS.get(selected_model)
        
        # 3.1 إذا كان النموذج غير نشط، استخدم البديل
        if not config or not config.is_active:
            selected_model = AIModelId.QWEN_3_7_MAX
            config = MODEL_CONFIGS.get(selected_model)
        
        # 3.2 إرسال الطلب إلى النموذج الفعلي
        start_time = asyncio.get_event_loop().time()
        
        try:
            response = await self._call_model(
                model_id=selected_model,
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            # حساب الوقت المستغرق
            elapsed = asyncio.get_event_loop().time() - start_time
            
            # استخراج النص والتوكنات
            generated_text = response.get("text", "")
            input_tokens = response.get("usage", {}).get("input_tokens", len(prompt) // 4)
            output_tokens = response.get("usage", {}).get("output_tokens", len(generated_text) // 4)
            
            # 4. تتبع التكلفة
            cost_data = await CostTracker.record_usage(
                model_id=selected_model.value,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            
            # 5. تخزين النتيجة في الكاش (إذا لم تكن من الكاش)
            if use_cache and not route_result.get("_from_cache"):
                await SemanticCache.set(prompt, selected_model.value, {
                    "text": generated_text,
                    "model": selected_model.value,
                    "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
                })
                
                if system_prompt and config.supports_prompt_caching:
                    await PromptCache.set_cached_response(
                        system_prompt, prompt, selected_model.value, generated_text
                    )
            
            return {
                "text": generated_text,
                "model": selected_model.value,
                "model_config": {
                    "name": config.name,
                    "description": config.description,
                },
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                },
                "cost": cost_data,
                "performance": {
                    "elapsed_seconds": elapsed,
                },
                "task_type": task_type,
                "_from_cache": False,
                "_cached": False,
            }
            
        except Exception as e:
            # في حالة الفشل، حاول استخدام النموذج الاحتياطي
            if selected_model != AIModelId.QWEN_3_7_MAX:
                return await self.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    language=language,
                    task_type=task_type,
                    use_cache=use_cache,
                    use_batch=use_batch,
                    force_model=AIModelId.QWEN_3_7_MAX,
                )
            else:
                raise Exception(f"فشل جميع النماذج: {str(e)}")
    
    async def _call_model(
        self,
        model_id: AIModelId,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        استدعاء النموذج الفعلي عبر HTTP API
        """
        session = await self._get_session()
        endpoint = self.API_ENDPOINTS.get(model_id)
        api_key = self.API_KEYS.get(model_id)
        
        if not endpoint or not api_key:
            raise ValueError(f"⚠️ النموذج {model_id} غير مدعوم")
        
        # بناء الطلب حسب نوع النموذج
        if model_id == AIModelId.HUNYUAN_MT:
            # Hunyuan (مجاني للترجمة)
            payload = {
                "model": "hunyuan-translation",
                "messages": [
                    {"role": "user", "content": prompt}
                ] if not system_prompt else [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        elif model_id == AIModelId.MISTRAL_SABA:
            # Mistral Saba
            payload = {
                "model": "mistral-saba",
                "messages": [
                    {"role": "user", "content": prompt}
                ] if not system_prompt else [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        elif model_id == AIModelId.KIMI_K2_6:
            # Kimi K2.6
            payload = {
                "model": "moonshot-v1-8k",
                "messages": [
                    {"role": "user", "content": prompt}
                ] if not system_prompt else [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        else:  # Qwen
            payload = {
                "model": "qwen-max",
                "input": {
                    "messages": [
                        {"role": "user", "content": prompt}
                    ] if not system_prompt else [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ]
                },
                "parameters": {
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
            }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        # محاكاة الاستدعاء (للتطوير، استبدل بالاستدعاء الفعلي)
        # في بيئة الإنتاج، استخدم: async with session.post(endpoint, json=payload, headers=headers) as resp:
        
        # محاكاة مؤقتة:
        await asyncio.sleep(0.5)  # محاكاة زمن الاستجابة
        
        # محاكاة الرد:
        return {
            "text": f"رد من {model_id.value}: {prompt[:50]}... (محاكاة)",
            "usage": {
                "input_tokens": len(prompt) // 4,
                "output_tokens": 50,
            }
        }
        
        # الكود الفعلي (معلق):
        # try:
        #     async with session.post(endpoint, json=payload, headers=headers) as response:
        #         if response.status != 200:
        #             error_text = await response.text()
        #             raise Exception(f"API Error {response.status}: {error_text}")
        #         return await response.json()
        # except aiohttp.ClientError as e:
        #     raise Exception(f"Network error: {str(e)}")


# ==========================================
# إنشاء instance واحد (Singleton)
# ==========================================
ai_engine = AIEngine()