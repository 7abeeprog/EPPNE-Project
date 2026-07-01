from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.sovereign_entities.models import (
    SovereignEntityType, KYBStatus, EntityRole
)


# ========== Sovereign Entity ==========
class SovereignEntityCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    legal_name: Optional[str] = None
    entity_type: SovereignEntityType
    registration_number: Optional[str] = None
    tax_id: Optional[str] = None
    country_of_origin: str = Field(..., min_length=2, max_length=100)
    city: Optional[str] = None
    address: Optional[str] = None
    official_email: str
    official_phone: Optional[str] = None
    website: Optional[str] = None
    wallet_address: Optional[str] = Field(None, pattern="^0x[a-fA-F0-9]{40}$")
    logo_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    primary_color: str = "#8CC63F"
    secondary_color: str = "#06b6d4"
    parent_id: Optional[int] = None

    @field_validator("official_email")
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v


class SovereignEntityUpdate(BaseModel):
    name: Optional[str] = None
    legal_name: Optional[str] = None
    registration_number: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    official_email: Optional[str] = None
    official_phone: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    is_active: Optional[bool] = None


class SovereignEntityResponse(SovereignEntityCreate):
    id: int
    tenant_id: int
    treasury_balance_mrusdt: Decimal
    kyb_status: KYBStatus
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========== Entity Representatives ==========
class EntityRepresentativeCreate(BaseModel):
    user_id: int
    role: EntityRole
    can_sign_contracts: bool = False
    signature_pub_key: Optional[str] = None


class EntityRepresentativeResponse(EntityRepresentativeCreate):
    id: int
    entity_id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========== KYB Verification ==========
class KYBDocumentUpload(BaseModel):
    document_type: str  # commercial_register, tax_card, authorization_letter
    document_url: str


class KYBUpdateStatus(BaseModel):
    status: KYBStatus
    rejection_reason: Optional[str] = None


# ========== Entity Page (Brand Builder) ==========
class PageComponentSchema(BaseModel):
    component_type: str
    props: Dict[str, Any] = {}
    id: str  # unique id for drag-drop


class PageSection(BaseModel):
    id: str
    layout: str  # grid, flex, single-column
    components: List[PageComponentSchema] = []


class EntityPageCreate(BaseModel):
    template_id: Optional[int] = None
    custom_structure: Optional[Dict[str, Any]] = None  # {sections: [...]}
    slug: str = Field(..., pattern="^[a-z0-9-]+$")
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    custom_domain: Optional[str] = None


class EntityPageUpdate(BaseModel):
    custom_structure: Optional[Dict[str, Any]] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    

class EntityPageResponse(EntityPageCreate):
    id: int
    entity_id: int
    visits_count: int
    last_visit_at: Optional[datetime]
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EntityCustomPageCreate(BaseModel):
    slug: str
    title: str
    content: Dict[str, Any]  # sections structure


# ========== Templates & Components ==========
class PageTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    page_structure: Dict[str, Any]
    is_public: bool = True


class PageTemplateResponse(PageTemplateCreate):
    id: int
    tenant_id: int
    is_default: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PageComponentResponse(BaseModel):
    id: int
    name: str
    component_type: str
    default_props: Dict[str, Any]
    preview_image: Optional[str]
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# 🆕 الإضافات الجديدة للعمليات المالية والشجرة
# ============================================================

class EntityDepositRequest(BaseModel):
    """طلب الإيداع في محفظة الكيان"""
    amount: Decimal = Field(..., gt=0, description="المبلغ المراد إيداعه")
    currency: str = Field("MR_USDT", description="عملة الإيداع")
    notes: Optional[str] = Field(None, description="ملاحظات اختيارية")


class EntityTransferRequest(BaseModel):
    """طلب التحويل من محفظة الكيان إلى عنوان خارجي"""
    to_address: str = Field(..., description="العنوان المستهدف (بريد إلكتروني أو محفظة)")
    amount: Decimal = Field(..., gt=0, description="المبلغ المراد تحويله")
    currency: str = Field("MR_USDT", description="عملة التحويل")
    notes: Optional[str] = Field(None, description="ملاحظات اختيارية")


class EntityTreeResponse(BaseModel):
    """استجابة الشجرة الهرمية للكيان (للـ JSON المتداخل)"""
    id: int
    name: str
    entity_type: str
    logo_url: Optional[str]
    children: List['EntityTreeResponse'] = []

    model_config = ConfigDict(from_attributes=True)