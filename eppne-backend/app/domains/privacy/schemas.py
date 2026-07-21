# app/domains/privacy/schemas.py
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List
from datetime import datetime

from app.domains.privacy.models import ConsentType, ErasureStatus


# ==========================================
# 1. إعدادات الخصوصية (Privacy Settings)
# ==========================================

class PrivacySettingUpdate(BaseModel):
    """
    مخطط تحديث إعدادات الخصوصية.
    جميع الحقول اختيارية لتحديث جزئي.
    """
    profile_visibility: Optional[str] = Field(
        default=None,
        description="رؤية الملف الشخصي: PUBLIC, FRIENDS_ONLY, PRIVATE"
    )
    search_engine_indexing: Optional[bool] = Field(
        default=None,
        description="السماح بفهرسة الملف الشخصي في محركات البحث"
    )
    allow_ai_training: Optional[bool] = Field(
        default=None,
        description="السماح باستخدام البيانات لتدريب نماذج الذكاء الاصطناعي"
    )
    allow_targeted_ads: Optional[bool] = Field(
        default=None,
        description="السماح بعرض إعلانات مخصصة بناءً على النشاط"
    )
    share_live_location: Optional[bool] = Field(
        default=None,
        description="مشاركة الموقع الحي مع التطبيقات المرتبطة"
    )

    @field_validator("profile_visibility")
    @classmethod
    def validate_profile_visibility(cls, v: Optional[str]) -> Optional[str]:
        """التحقق من صحة قيمة profile_visibility."""
        if v is not None and v not in ["PUBLIC", "FRIENDS_ONLY", "PRIVATE"]:
            raise ValueError("profile_visibility must be one of: PUBLIC, FRIENDS_ONLY, PRIVATE")
        return v


class PrivacySettingResponse(PrivacySettingUpdate):
    """
    مخطط الاستجابة لإعدادات الخصوصية.
    يحتوي على جميع الحقول بما فيها المعرف وتواريخ الإنشاء والتحديث.
    """
    id: int = Field(description="المعرف الفريد للإعدادات")
    user_id: int = Field(description="معرف المستخدم المرتبط")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    updated_at: datetime = Field(description="تاريخ آخر تحديث")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "user_id": 123,
                "profile_visibility": "PUBLIC",
                "search_engine_indexing": True,
                "allow_ai_training": False,
                "allow_targeted_ads": True,
                "share_live_location": False,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z"
            }
        }
    )


# ==========================================
# 2. طلبات محو البيانات (Erasure Requests)
# ==========================================

class DataErasureRequestCreate(BaseModel):
    """
    مخطط إنشاء طلب محو بيانات جديد.
    """
    target_module: str = Field(
        description="القطاع المستهدف: identity, academy, finance, commerce, health, iot, realestate, all"
    )
    reason: Optional[str] = Field(
        default=None,
        description="سبب طلب محو البيانات (اختياري)",
        max_length=500
    )

    @field_validator("target_module")
    @classmethod
    def validate_target_module(cls, v: str) -> str:
        """التحقق من صحة القطاع المستهدف."""
        valid_modules = ["identity", "academy", "finance", "commerce", "health", "iot", "realestate", "all"]
        if v.lower() not in valid_modules:
            raise ValueError(f"target_module must be one of: {', '.join(valid_modules)}")
        return v.lower()


class DataErasureRequestResponse(BaseModel):
    """
    مخطط الاستجابة لطلب محو البيانات.
    """
    id: int = Field(description="المعرف الفريد للطلب")
    user_id: int = Field(description="معرف المستخدم صاحب الطلب")
    target_module: str = Field(description="القطاع المستهدف")
    reason: Optional[str] = Field(description="سبب الطلب")
    status: str = Field(description="حالة الطلب: PENDING, PROCESSING, COMPLETED, PARTIAL_ON_CHAIN, REJECTED")
    processed_at: Optional[datetime] = Field(description="تاريخ المعالجة")
    erasure_receipt_tx: Optional[str] = Field(description="رقم معاملة الإثبات على السلسلة")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "user_id": 123,
                "target_module": "academy",
                "reason": "رغبة في حذف بياناتي الأكاديمية",
                "status": "PENDING",
                "processed_at": None,
                "erasure_receipt_tx": None,
                "created_at": "2026-01-01T00:00:00Z"
            }
        }
    )


class PaginatedErasureRequestResponse(BaseModel):
    """
    مخطط الاستجابة لقائمة طلبات محو البيانات مع Pagination.
    """
    data: List[DataErasureRequestResponse] = Field(description="قائمة الطلبات")
    total: int = Field(description="إجمالي عدد الطلبات")
    skip: int = Field(default=0, description="عدد العناصر التي تم تخطيها")
    limit: int = Field(default=20, description="عدد العناصر في الصفحة")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data": [
                    {
                        "id": 1,
                        "user_id": 123,
                        "target_module": "academy",
                        "reason": "رغبة في حذف بياناتي الأكاديمية",
                        "status": "PENDING",
                        "processed_at": None,
                        "erasure_receipt_tx": None,
                        "created_at": "2026-01-01T00:00:00Z"
                    }
                ],
                "total": 1,
                "skip": 0,
                "limit": 20
            }
        }
    )


# ==========================================
# 3. سجلات الموافقات (Consent Logs) - للاستخدام الداخلي
# ==========================================

class ConsentLogResponse(BaseModel):
    """
    مخطط الاستجابة لسجل الموافقة (للإدارة والتدقيق).
    """
    id: int = Field(description="المعرف الفريد للسجل")
    user_id: int = Field(description="معرف المستخدم")
    consent_type: str = Field(description="نوع الموافقة: DATA_PROCESSING, AI_TRAINING, MARKETING, THIRD_PARTY")
    is_granted: bool = Field(description="هل تمت الموافقة (true/false)")
    ip_address: Optional[str] = Field(description="عنوان IP المشفر")
    user_agent: Optional[str] = Field(description="متصفح المستخدم")
    consent_tx_hash: Optional[str] = Field(description="رقم معاملة الموافقة على السلسلة")
    created_at: datetime = Field(description="تاريخ التسجيل")
    
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 4. سجلات الشواهد (Tombstone Records) - للاستخدام الداخلي
# ==========================================

class TombstoneRecordResponse(BaseModel):
    """
    مخطط الاستجابة لسجل الشاهدة (للإدارة والتدقيق).
    """
    id: int = Field(description="المعرف الفريد للسجل")
    table_name: str = Field(description="اسم الجدول المحذوف منه")
    record_id: int = Field(description="معرف السجل المحذوف")
    erasure_request_id: Optional[int] = Field(description="معرف طلب المحو المرتبط")
    deleted_by_id: int = Field(description="معرف المستخدم الذي حذف السجل")
    original_tx_hash: Optional[str] = Field(description="هاش المعاملة الأصلية")
    ipfs_unpin_status: bool = Field(description="هل تم إلغاء الربط من IPFS")
    blockchain_burn_status: str = Field(description="حالة حرق التوكن: PENDING, COMPLETED, FAILED")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 5. مخططات الأخطاء الموحدة (Error Schemas)
# ==========================================

class ErrorResponse(BaseModel):
    """
    مخطط الاستجابة للأخطاء الموحدة.
    """
    detail: str = Field(description="رسالة الخطأ الواضحة للمستخدم")
    code: Optional[str] = Field(default=None, description="رمز الخطأ الداخلي للتصنيف")
    status: int = Field(description="رمز حالة HTTP")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "تعذر إنشاء طلب محو البيانات. قد يكون هناك طلب معلق بالفعل لهذا القطاع.",
                "code": "DUPLICATE_REQUEST",
                "status": 400
            }
        }
    )