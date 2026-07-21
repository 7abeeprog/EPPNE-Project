# app/services/ai/models.py
"""
تعريف النماذج الأربعة للذكاء الاصطناعي (المزيج الرباعي)
"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class TaskType(str, Enum):
    ANALYSIS = "ANALYSIS"
    GENERATION = "GENERATION"
    TRANSLATION = "TRANSLATION"
    MAINTENANCE = "MAINTENANCE"
    AUTOMATION = "AUTOMATION"
    ARABIC_CHAT = "ARABIC_CHAT"  # أضفنا هذا السطر تحديداً لحل الخطأ
    SUPPORT_ASSISTANT = "SUPPORT_ASSISTANT" # احتياطاً لأي مهام دعم
    # أضف أي نوع مهمة إضافي تحتاجه هنا
class AIModelId(str, Enum):
    """معرفات النماذج الأربعة"""
    HUNYUAN_MT = "hunyuan-mt-7b"       # الطبقة الأولى: الترجمة (مجاني)
    MISTRAL_SABA = "mistral-saba"       # الطبقة الثانية: العربية واللهجة المصرية
    KIMI_K2_6 = "kimi-k2.6"             # الطبقة الثالثة: المهام المعقدة
    QWEN_3_7_MAX = "qwen-3.7-max"       # الطبقة الرابعة: النموذج الاحتياطي


class ModelConfig(BaseModel):
    """إعدادات النموذج الواحد"""
    id: AIModelId
    name: str
    description: str
    input_cost_per_1m: float = 0.0      # التكلفة لكل مليون رمز إدخال
    output_cost_per_1m: float = 0.0     # التكلفة لكل مليون رمز إخراج
    max_tokens: int = 4096
    supports_streaming: bool = False
    supports_prompt_caching: bool = False
    languages: list[str] = []
    is_active: bool = True


# ==========================================
# إعدادات النماذج الأربعة
# ==========================================

MODEL_CONFIGS: Dict[AIModelId, ModelConfig] = {
    AIModelId.HUNYUAN_MT: ModelConfig(
        id=AIModelId.HUNYUAN_MT,
        name="Tencent Hunyuan-MT-7B",
        description="الترجمة الفورية بين 33 لغة (مجاني)",
        input_cost_per_1m=0.0,
        output_cost_per_1m=0.0,
        max_tokens=2048,
        supports_streaming=False,
        supports_prompt_caching=False,
        languages=["ar", "en", "fr", "es", "de", "it", "pt", "ru", "ja", "ko", "zh", "hi", "tr", "fa", "ur", "he", "nl", "pl", "sv", "da", "no", "fi", "el", "cs", "hu", "ro", "bg", "sr", "hr", "sk", "sl", "lt", "lv"],
        is_active=True
    ),
    AIModelId.MISTRAL_SABA: ModelConfig(
        id=AIModelId.MISTRAL_SABA,
        name="Mistral Saba",
        description="الخبير الإقليمي للغة العربية واللهجة المصرية",
        input_cost_per_1m=0.20,
        output_cost_per_1m=0.60,
        max_tokens=8192,
        supports_streaming=True,
        supports_prompt_caching=True,
        languages=["ar", "ar-EG"],
        is_active=True
    ),
    AIModelId.KIMI_K2_6: ModelConfig(
        id=AIModelId.KIMI_K2_6,
        name="Kimi K2.6",
        description="الدماغ المركزي للمهام المعقدة (برمجة، أتمتة، تنسيق الوكلاء)",
        input_cost_per_1m=0.75,
        output_cost_per_1m=3.50,
        max_tokens=16384,
        supports_streaming=True,
        supports_prompt_caching=True,
        languages=["ar", "en", "fr", "zh", "ja", "ko"],
        is_active=True
    ),
    AIModelId.QWEN_3_7_MAX: ModelConfig(
        id=AIModelId.QWEN_3_7_MAX,
        name="Qwen 3.7 Max",
        description="النموذج الاحتياطي للمناطق التي لا تغطيها النماذج السابقة",
        input_cost_per_1m=1.25,
        output_cost_per_1m=3.75,
        max_tokens=8192,
        supports_streaming=True,
        supports_prompt_caching=False,
        languages=["ar", "en", "fr", "es", "de", "it", "pt", "ru", "ja", "ko", "zh", "hi"],
        is_active=True
    ),
}


# ==========================================
# تعريف الطبقات (للتوجيه الذكي)
# ==========================================

class ModelTier(str, Enum):
    """طبقات النماذج حسب التكلفة والوظيفة"""
    FREE = "free"           # مجاني (Hunyuan)
    REGIONAL = "regional"   # إقليمي (Mistral Saba)
    CORE = "core"           # أساسي (Kimi K2.6)
    FALLBACK = "fallback"   # احتياطي (Qwen)


TIER_MODELS = {
    ModelTier.FREE: [AIModelId.HUNYUAN_MT],
    ModelTier.REGIONAL: [AIModelId.MISTRAL_SABA],
    ModelTier.CORE: [AIModelId.KIMI_K2_6],
    ModelTier.FALLBACK: [AIModelId.QWEN_3_7_MAX],
}

# نسب التوزيع الافتراضية (حسب التقرير)
DEFAULT_ROUTING_PERCENTAGES = {
    AIModelId.HUNYUAN_MT: 35,   # 35%
    AIModelId.MISTRAL_SABA: 35, # 35%
    AIModelId.KIMI_K2_6: 20,    # 20%
    AIModelId.QWEN_3_7_MAX: 10, # 10%
}