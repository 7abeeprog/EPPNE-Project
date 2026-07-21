# app/domains/invitations/schemas.py
"""
نماذج (Schemas) Pydantic لقطاع الدعوات وخدمة العملاء – النسخة الذهبية
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.invitations.models import (
    InvitationType, InvitationTargetType, InvitationStatus, CampaignType,
    LeadStatus, LeadSource, CampaignStatus, InteractionType, TicketStatus
)


# ============================================================
# 1. الدعوات (Invitations)
# ============================================================

class InvitationCreate(BaseModel):
    invitation_type: InvitationType = Field(description="نوع الدعوة")
    target_type: InvitationTargetType = Field(description="نوع الهدف")
    target_user_id: Optional[int] = Field(default=None, description="معرف المستخدم المستهدف")
    target_entity_identifier: Optional[str] = Field(default=None, description="معرف الكيان المستهدف")
    custom_message: Optional[str] = Field(default=None, description="رسالة مخصصة")
    title: Optional[str] = Field(default=None, description="عنوان الدعوة")
    campaign_type: CampaignType = Field(description="نوع الحملة")
    campaign_id: int = Field(description="معرف الحملة")
    discount_percentage: Decimal = Field(default=Decimal("0.0"), ge=0, le=100, description="نسبة الخصم")
    gift_coins_amount: Decimal = Field(default=Decimal("0.0"), ge=0, description="مبلغ الهدية")
    gift_currency: str = Field(default="MR_USDT", description="عملة الهدية")
    max_uses: int = Field(default=1, ge=1, description="الحد الأقصى للاستخدام")
    expires_at: Optional[datetime] = Field(default=None, description="تاريخ الانتهاء")

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, v: Optional[datetime], info) -> Optional[datetime]:
        if v and "created_at" in info.data:
            created = info.data.get("created_at")
            if created and v <= created:
                raise ValueError("expires_at must be after created_at")
        return v


class InvitationUpdate(BaseModel):
    custom_message: Optional[str] = Field(default=None, description="رسالة مخصصة")
    title: Optional[str] = Field(default=None, description="عنوان الدعوة")
    discount_percentage: Optional[Decimal] = Field(default=None, ge=0, le=100, description="نسبة الخصم")
    gift_coins_amount: Optional[Decimal] = Field(default=None, ge=0, description="مبلغ الهدية")
    max_uses: Optional[int] = Field(default=None, ge=1, description="الحد الأقصى للاستخدام")
    expires_at: Optional[datetime] = Field(default=None, description="تاريخ الانتهاء")
    status: Optional[InvitationStatus] = Field(default=None, description="حالة الدعوة")


class InvitationResponse(InvitationCreate):
    id: int
    tenant_id: int
    sender_user_id: Optional[int]
    sender_entity_id: Optional[int]
    status: InvitationStatus
    assigned_ai_agent_id: Optional[int]
    click_count: int
    first_clicked_at: Optional[datetime]
    last_clicked_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    invitation_url: Optional[str] = Field(default=None, description="رابط الدعوة")
    model_config = ConfigDict(from_attributes=True)


class InvitationAccept(BaseModel):
    email: Optional[str] = Field(default=None, description="البريد الإلكتروني")
    password: Optional[str] = Field(default=None, description="كلمة المرور")
    name: Optional[str] = Field(default=None, description="الاسم")
    phone: Optional[str] = Field(default=None, description="رقم الهاتف")


class InvitationAcceptResponse(BaseModel):
    message: str
    user_id: int
    lead_id: int
    redirect_url: str


# ============================================================
# 2. العملاء المحتملون (Leads)
# ============================================================

class LeadCreate(BaseModel):
    first_name: Optional[str] = Field(default=None, description="الاسم الأول")
    last_name: Optional[str] = Field(default=None, description="الاسم الأخير")
    email: Optional[str] = Field(default=None, description="البريد الإلكتروني")
    phone: Optional[str] = Field(default=None, description="رقم الهاتف")
    company: Optional[str] = Field(default=None, description="الشركة")
    position: Optional[str] = Field(default=None, description="المنصب")
    source: LeadSource = Field(description="مصدر العميل المحتمل")
    source_reference: Optional[str] = Field(default=None, description="مرجع المصدر")
    status: LeadStatus = Field(default=LeadStatus.NEW, description="حالة العميل المحتمل")
    notes: Optional[str] = Field(default=None, description="ملاحظات")
    assigned_to: Optional[int] = Field(default=None, description="معرف المسؤول المعين")
    social_profiles: Dict[str, str] = Field(default_factory=dict, description="الملفات الاجتماعية")


class LeadUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, description="الاسم الأول")
    last_name: Optional[str] = Field(default=None, description="الاسم الأخير")
    email: Optional[str] = Field(default=None, description="البريد الإلكتروني")
    phone: Optional[str] = Field(default=None, description="رقم الهاتف")
    company: Optional[str] = Field(default=None, description="الشركة")
    position: Optional[str] = Field(default=None, description="المنصب")
    status: Optional[LeadStatus] = Field(default=None, description="حالة العميل المحتمل")
    notes: Optional[str] = Field(default=None, description="ملاحظات")
    assigned_to: Optional[int] = Field(default=None, description="معرف المسؤول المعين")
    social_profiles: Optional[Dict[str, str]] = Field(default=None, description="الملفات الاجتماعية")


class LeadResponse(LeadCreate):
    id: int
    tenant_id: int
    score: int
    converted_user_id: Optional[int]
    converted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    assigned_to_name: Optional[str] = Field(default=None, description="اسم المسؤول المعين")
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# 3. تفاعلات العملاء (Interactions)
# ============================================================

class InteractionCreate(BaseModel):
    interaction_type: InteractionType = Field(description="نوع التفاعل")
    title: Optional[str] = Field(default=None, description="عنوان التفاعل")
    content: str = Field(description="محتوى التفاعل")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="بيانات إضافية")


class InteractionUpdate(BaseModel):
    title: Optional[str] = Field(default=None, description="عنوان التفاعل")
    content: Optional[str] = Field(default=None, description="محتوى التفاعل")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="بيانات إضافية")


class InteractionResponse(InteractionCreate):
    id: int
    tenant_id: int
    lead_id: int
    user_id: Optional[int]
    user_name: Optional[str] = Field(default=None, description="اسم المستخدم")
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# 4. الحملات التسويقية (Campaigns)
# ============================================================

class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255, description="اسم الحملة")
    description: Optional[str] = Field(default=None, description="وصف الحملة")
    campaign_type: CampaignType = Field(description="نوع الحملة")
    target_audience: Dict[str, Any] = Field(default_factory=dict, description="الجمهور المستهدف")
    budget_mrusdt: Decimal = Field(default=Decimal("0.0"), ge=0, description="الميزانية")
    start_date: datetime = Field(description="تاريخ البدء")
    end_date: Optional[datetime] = Field(default=None, description="تاريخ الانتهاء")
    channels: List[str] = Field(default_factory=list, description="القنوات")

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: Optional[datetime], info) -> Optional[datetime]:
        if v and "start_date" in info.data:
            start = info.data.get("start_date")
            if start and v <= start:
                raise ValueError("end_date must be after start_date")
        return v


class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(default=None, description="اسم الحملة")
    description: Optional[str] = Field(default=None, description="وصف الحملة")
    target_audience: Optional[Dict[str, Any]] = Field(default=None, description="الجمهور المستهدف")
    budget_mrusdt: Optional[Decimal] = Field(default=None, ge=0, description="الميزانية")
    end_date: Optional[datetime] = Field(default=None, description="تاريخ الانتهاء")
    channels: Optional[List[str]] = Field(default=None, description="القنوات")
    status: Optional[CampaignStatus] = Field(default=None, description="حالة الحملة")


class CampaignResponse(CampaignCreate):
    id: int
    tenant_id: int
    spent_mrusdt: Decimal
    total_leads: int
    converted_leads: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# 5. تذاكر الدعم (Support Tickets)
# ============================================================

class TicketCreate(BaseModel):
    lead_id: Optional[int] = Field(default=None, description="معرف العميل المحتمل")
    subject: str = Field(..., min_length=3, max_length=255, description="موضوع التذكرة")
    description: str = Field(description="وصف التذكرة")
    priority: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|URGENT)$", description="الأولوية")


class TicketUpdate(BaseModel):
    subject: Optional[str] = Field(default=None, description="موضوع التذكرة")
    description: Optional[str] = Field(default=None, description="وصف التذكرة")
    priority: Optional[str] = Field(default=None, pattern="^(LOW|MEDIUM|HIGH|URGENT)$", description="الأولوية")
    status: Optional[TicketStatus] = Field(default=None, description="حالة التذكرة")
    assigned_to: Optional[int] = Field(default=None, description="معرف المسؤول المعين")


class TicketResponse(TicketCreate):
    id: int
    tenant_id: int
    user_id: Optional[int]
    user_name: Optional[str] = Field(default=None, description="اسم المستخدم")
    assigned_to: Optional[int]
    assigned_to_name: Optional[str] = Field(default=None, description="اسم المسؤول المعين")
    status: TicketStatus
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    comments: Optional[List['TicketCommentResponse']] = None
    model_config = ConfigDict(from_attributes=True)


class TicketCommentCreate(BaseModel):
    comment: str = Field(description="التعليق")
    is_internal: bool = Field(default=False, description="هل التعليق داخلي؟")


class TicketCommentResponse(TicketCommentCreate):
    id: int
    tenant_id: int
    ticket_id: int
    user_id: int
    user_name: Optional[str] = Field(default=None, description="اسم المستخدم")
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# 6. التتبع والتحليلات (Tracking & Analytics)
# ============================================================

class InvitationTrackingCreate(BaseModel):
    invitation_id: int = Field(description="معرف الدعوة")
    page_visited: Optional[str] = Field(default=None, description="الصفحة التي تمت زيارتها")
    actions: List[str] = Field(default_factory=list, description="الإجراءات")


class InvitationTrackingResponse(BaseModel):
    id: int
    invitation_id: int
    ip_address: Optional[str]
    user_agent: Optional[str]
    device_type: Optional[str]
    location_city: Optional[str]
    location_country: Optional[str]
    page_visited: Optional[str]
    time_spent_seconds: int
    actions: List[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ConversationMessage(BaseModel):
    message: str = Field(description="الرسالة")


class ConversationResponse(BaseModel):
    id: int
    invitation_id: int
    visitor_session_id: Optional[str]
    visitor_user_id: Optional[int]
    message: str
    is_from_ai: bool
    ai_agent_id: Optional[int]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ClientInsightResponse(BaseModel):
    invitation_id: int
    ai_analysis: Dict[str, Any]
    recommended_discount: Optional[float]
    recommended_message_template: Optional[str]
    readiness_score: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# 7. الإحصائيات (Stats)
# ============================================================

class InvitationStatsResponse(BaseModel):
    total_invitations: int
    sent_invitations: int
    accepted_invitations: int
    conversion_rate: float
    total_clicks: int
    total_leads: int
    converted_leads: int
    active_campaigns: int
    open_tickets: int
    model_config = ConfigDict(from_attributes=True)