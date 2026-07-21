# app/domains/translation/schemas.py (الإصدار النهائي المتكامل)
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class TranslateRequest(BaseModel):
    text: str = Field(description="النص المراد ترجمته")
    source_lang: str = Field(default="auto", description="لغة المصدر (auto للكشف التلقائي)")
    target_lang: str = Field(description="اللغة المستهدفة")
    context: Optional[str] = Field(default=None, description="سياق الترجمة (مثل technical, medical, legal)")
    idempotency_key: Optional[str] = Field(default=None, description="مفتاح تفادي التكرار (اختياري)")


class TranslateResponse(BaseModel):
    translated_text: str = Field(description="النص المترجم")
    source_lang: str = Field(description="لغة المصدر الفعلية")
    target_lang: str = Field(description="اللغة المستهدفة")
    from_cache: bool = Field(description="هل تمت الترجمة من الكاش؟")
    cost_mrusdt: str = Field(description="تكلفة الترجمة بوحدة MRUSDT (كـ نص للحفاظ على الدقة)")


class BatchTranslateRequest(BaseModel):
    texts: List[str] = Field(description="قائمة النصوص للترجمة الجماعية")
    source_lang: str = Field(default="auto", description="لغة المصدر")
    target_lang: str = Field(description="اللغة المستهدفة")


class ChatTranslateRequest(BaseModel):
    message: str = Field(description="رسالة المحادثة")
    conversation_id: str = Field(description="معرف المحادثة")
    target_lang: str = Field(description="اللغة المستهدفة")


class ChatTranslateResponse(BaseModel):
    original: str = Field(description="النص الأصلي")
    translated: str = Field(description="النص المترجم")
    target_lang: str = Field(description="اللغة المستهدفة")


class SupportedLanguageResponse(BaseModel):
    code: str = Field(description="رمز اللغة (مثل en, ar)")
    name: str = Field(description="اسم اللغة بالإنجليزية")
    native_name: Optional[str] = Field(default=None, description="الاسم باللغة الأصلية")

    model_config = ConfigDict(from_attributes=True)