# app/domains/translation/schemas.py (الإصدار النهائي المتكامل)
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime


class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "auto"
    target_lang: str
    context: Optional[str] = None  # سياق للمساعدة في الترجمة (مثال: "technical", "medical", "legal")
    idempotency_key: Optional[str] = Field(None, description="مفتاح تفادي التكرار (اختياري)")


class TranslateResponse(BaseModel):
    translated_text: str
    source_lang: str
    target_lang: str
    from_cache: bool
    cost_mrusdt: str  # تم تغيير النوع إلى string للحفاظ على الدقة المالية


class BatchTranslateRequest(BaseModel):
    texts: list[str]
    source_lang: str = "auto"
    target_lang: str


class ChatTranslateRequest(BaseModel):
    message: str
    conversation_id: str
    target_lang: str


class ChatTranslateResponse(BaseModel):
    original: str
    translated: str
    target_lang: str


class SupportedLanguageResponse(BaseModel):
    code: str
    name: str
    native_name: Optional[str]
    model_config = ConfigDict(from_attributes=True)