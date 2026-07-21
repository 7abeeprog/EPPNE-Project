# app/domains/sovereign_entities/schemas.py
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.sovereign_entities.models import (
    SovereignEntityType, KYBStatus, EntityRole
)


# ========== Sovereign Entity ==========
class SovereignEntityCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="اسم الكيان")
    legal_name: Optional[str] = Field(default=None, description="الاسم القانوني المسجل")
    entity_type: SovereignEntityType = Field(description="نوع الكيان")
    registration_number: Optional[str] = Field(default=None, description="رقم التسجيل التجاري")
    tax_id: Optional[str] = Field(default=None, description="الرقم الضريبي")
    country_of_origin: str = Field(..., min_length=2, max_length=100, description="الدولة")
    city: Optional[str] = Field(default=None, description="المدينة")
    address: Optional[str] = Field(default=None, description="العنوان")
    official_email: str = Field(description="البريد الإلكتروني الرسمي")
    official_phone: Optional[str] = Field(default=None, description="الهاتف الرسمي")
    website: Optional[str] = Field(default=None, description="الموقع الإلكتروني")
    wallet_address: Optional[str] = Field(default=None, pattern="^0x[a-fA-F0-9]{40}$", description="عنوان المحفظة")
    logo_url: Optional[str] = Field(default=None, description="رابط الشعار")
    cover_image_url: Optional[str] = Field(default=None, description="رابط صورة الغلاف")
    primary_color: str = Field(default="#8CC63F", description="اللون الأساسي")
    secondary_color: str = Field(default="#06b6d4", description="اللون الثانوي")
    parent_id: Optional[int] = Field(default=None, description="معرف الكيان الأب")

    @field_validator("official_email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v


class SovereignEntityUpdate(BaseModel):
    name: Optional[str] = Field(default=None, description="الاسم")
    legal_name: Optional[str] = Field(default=None, description="الاسم القانوني")
    registration_number: Optional[str] = Field(default=None, description="رقم التسجيل")
    tax_id: Optional[str] = Field(default=None, description="الرقم الضريبي")
    address: Optional[str] = Field(default=None, description="العنوان")
    official_email: Optional[str] = Field(default=None, description="البريد الرسمي")
    official_phone: Optional[str] = Field(default=None, description="الهاتف الرسمي")
    website: Optional[str] = Field(default=None, description="الموقع الإلكتروني")
    logo_url: Optional[str] = Field(default=None, description="رابط الشعار")
    cover_image_url: Optional[str] = Field(default=None, description="رابط صورة الغلاف")
    primary_color: Optional[str] = Field(default=None, description="اللون الأساسي")
    secondary_color: Optional[str] = Field(default=None, description="اللون الثانوي")
    is_active: Optional[bool] = Field(default=None, description="نشط")


class SovereignEntityResponse(SovereignEntityCreate):
    id: int = Field(description="معرف الكيان")
    tenant_id: int = Field(description="معرف المستأجر")
    treasury_balance_mrusdt: Decimal = Field(description="رصيد الخزينة")
    kyb_status: KYBStatus = Field(description="حالة التحقق")
    is_active: bool = Field(description="نشط")
    created_by: int = Field(description="معرف المنشئ")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    updated_at: datetime = Field(description="تاريخ التحديث")
    model_config = ConfigDict(from_attributes=True)


# ========== Entity Representatives ==========
class EntityRepresentativeCreate(BaseModel):
    user_id: int = Field(description="معرف المستخدم")
    role: EntityRole = Field(description="الدور")
    can_sign_contracts: bool = Field(default=False, description="يمكنه التوقيع على العقود")
    signature_pub_key: Optional[str] = Field(default=None, description="مفتاح التوقيع العام")


class EntityRepresentativeResponse(EntityRepresentativeCreate):
    id: int = Field(description="معرف التمثيل")
    entity_id: int = Field(description="معرف الكيان")
    is_active: bool = Field(description="نشط")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)


# ========== KYB Verification ==========
class KYBDocumentUpload(BaseModel):
    document_type: str = Field(description="نوع المستند (commercial_register, tax_card, authorization_letter)")
    document_url: str = Field(description="رابط المستند")


class KYBUpdateStatus(BaseModel):
    status: KYBStatus = Field(description="الحالة الجديدة")
    rejection_reason: Optional[str] = Field(default=None, description="سبب الرفض")


# ========== Entity Page (Brand Builder) ==========
class PageComponentSchema(BaseModel):
    component_type: str = Field(description="نوع المكون")
    props: Dict[str, Any] = Field(default={}, description="خصائص المكون")
    id: str = Field(description="معرف فريد للمكون")


class PageSection(BaseModel):
    id: str = Field(description="معرف القسم")
    layout: str = Field(description="نوع التخطيط (grid, flex, single-column)")
    components: List[PageComponentSchema] = Field(default=[], description="مكونات القسم")


class EntityPageCreate(BaseModel):
    template_id: Optional[int] = Field(default=None, description="معرف القالب المستخدم")
    custom_structure: Optional[Dict[str, Any]] = Field(default=None, description="الهيكل المخصص")
    slug: str = Field(..., pattern="^[a-z0-9-]+$", description="المسار المختصر")
    meta_title: Optional[str] = Field(default=None, description="عنوان SEO")
    meta_description: Optional[str] = Field(default=None, description="وصف SEO")
    custom_domain: Optional[str] = Field(default=None, description="النطاق المخصص")


class EntityPageUpdate(BaseModel):
    custom_structure: Optional[Dict[str, Any]] = Field(default=None, description="الهيكل المخصص")
    meta_title: Optional[str] = Field(default=None, description="عنوان SEO")
    meta_description: Optional[str] = Field(default=None, description="وصف SEO")


class EntityPageResponse(EntityPageCreate):
    id: int = Field(description="معرف الصفحة")
    entity_id: int = Field(description="معرف الكيان")
    visits_count: int = Field(description="عدد الزيارات")
    last_visit_at: Optional[datetime] = Field(default=None, description="آخر زيارة")
    published_at: Optional[datetime] = Field(default=None, description="تاريخ النشر")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    updated_at: datetime = Field(description="تاريخ التحديث")
    model_config = ConfigDict(from_attributes=True)


class EntityCustomPageCreate(BaseModel):
    slug: str = Field(description="المسار المختصر")
    title: str = Field(description="العنوان")
    content: Dict[str, Any] = Field(description="محتوى الصفحة (هيكل الأقسام)")


# ========== Templates & Components ==========
class PageTemplateCreate(BaseModel):
    name: str = Field(description="اسم القالب")
    description: Optional[str] = Field(default=None, description="الوصف")
    thumbnail_url: Optional[str] = Field(default=None, description="رابط الصورة المصغرة")
    page_structure: Dict[str, Any] = Field(description="هيكل الصفحة")
    is_public: bool = Field(default=True, description="عام")


class PageTemplateResponse(PageTemplateCreate):
    id: int = Field(description="معرف القالب")
    tenant_id: int = Field(description="معرف المستأجر")
    is_default: bool = Field(description="افتراضي")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)


class PageComponentResponse(BaseModel):
    id: int = Field(description="معرف المكون")
    name: str = Field(description="الاسم")
    component_type: str = Field(description="النوع")
    default_props: Dict[str, Any] = Field(description="الخصائص الافتراضية")
    preview_image: Optional[str] = Field(default=None, description="صورة معاينة")
    model_config = ConfigDict(from_attributes=True)


# ========== الإضافات الجديدة للعمليات المالية والشجرة ==========
class EntityDepositRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="المبلغ المراد إيداعه")
    currency: str = Field(default="MR_USDT", description="عملة الإيداع")
    notes: Optional[str] = Field(default=None, description="ملاحظات اختيارية")


class EntityTransferRequest(BaseModel):
    to_address: str = Field(..., description="العنوان المستهدف (بريد إلكتروني أو محفظة)")
    amount: Decimal = Field(..., gt=0, description="المبلغ المراد تحويله")
    currency: str = Field(default="MR_USDT", description="عملة التحويل")
    notes: Optional[str] = Field(default=None, description="ملاحظات اختيارية")


class EntityTreeResponse(BaseModel):
    id: int = Field(description="معرف الكيان")
    name: str = Field(description="الاسم")
    entity_type: str = Field(description="نوع الكيان")
    logo_url: Optional[str] = Field(default=None, description="رابط الشعار")
    children: List['EntityTreeResponse'] = Field(default=[], description="الأبناء")

    model_config = ConfigDict(from_attributes=True)


# حل المشكلة المرجعية الذاتية
EntityTreeResponse.model_rebuild()