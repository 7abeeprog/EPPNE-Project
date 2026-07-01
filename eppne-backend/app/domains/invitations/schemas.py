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


# ============================================================================
# 1. الدعوات (Invitations)
# ============================================================================

class InvitationCreate(BaseModel):
    invitation_type: InvitationType
    target_type: InvitationTargetType
    target_user_id: Optional[int] = None
    target_entity_identifier: Optional[str] = None
    custom_message: Optional[str] = None
    title: Optional[str] = None
    campaign_type: CampaignType
    campaign_id: int
    discount_percentage: Decimal = Field(default=0, ge=0, le=100)
    gift_coins_amount: Decimal = Field(default=0, ge=0)
    gift_currency: str = "MR_USDT"
    max_uses: int = Field(default=1, ge=1)
    expires_at: Optional[datetime] = None

    @field_validator("expires_at")
    def validate_expires_at(cls, v, info):
        if v and "created_at" in info.data:
            created = info.data.get("created_at")
            if created and v <= created:
                raise ValueError("expires_at must be after created_at")
        return v


class InvitationUpdate(BaseModel):
    custom_message: Optional[str] = None
    title: Optional[str] = None
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    gift_coins_amount: Optional[Decimal] = Field(None, ge=0)
    max_uses: Optional[int] = Field(None, ge=1)
    expires_at: Optional[datetime] = None
    status: Optional[InvitationStatus] = None


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
    invitation_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class InvitationAccept(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None


class InvitationAcceptResponse(BaseModel):
    message: str
    user_id: int
    lead_id: int
    redirect_url: str


# ============================================================================
# 2. العملاء المحتملون (Leads)
# ============================================================================

class LeadCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    source: LeadSource
    source_reference: Optional[str] = None
    status: LeadStatus = LeadStatus.NEW
    notes: Optional[str] = None
    assigned_to: Optional[int] = None
    social_profiles: Dict[str, str] = {}


class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    status: Optional[LeadStatus] = None
    notes: Optional[str] = None
    assigned_to: Optional[int] = None
    social_profiles: Optional[Dict[str, str]] = None


class LeadResponse(LeadCreate):
    id: int
    tenant_id: int
    score: int
    converted_user_id: Optional[int]
    converted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    assigned_to_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# 3. تفاعلات العملاء (Interactions)
# ============================================================================

class InteractionCreate(BaseModel):
    interaction_type: InteractionType
    title: Optional[str] = None
    content: str
    metadata: Dict[str, Any] = {}


class InteractionUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class InteractionResponse(InteractionCreate):
    id: int
    tenant_id: int
    lead_id: int
    user_id: Optional[int]
    user_name: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# 4. الحملات التسويقية (Campaigns)
# ============================================================================

class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    campaign_type: CampaignType
    target_audience: Dict[str, Any] = {}
    budget_mrusdt: Decimal = Field(default=0, ge=0)
    start_date: datetime
    end_date: Optional[datetime] = None
    channels: List[str] = []

    @field_validator("end_date")
    def validate_end_date(cls, v, info):
        if v and "start_date" in info.data:
            start = info.data.get("start_date")
            if start and v <= start:
                raise ValueError("end_date must be after start_date")
        return v


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_audience: Optional[Dict[str, Any]] = None
    budget_mrusdt: Optional[Decimal] = Field(None, ge=0)
    end_date: Optional[datetime] = None
    channels: Optional[List[str]] = None
    status: Optional[CampaignStatus] = None


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


# ============================================================================
# 5. تذاكر الدعم (Support Tickets)
# ============================================================================

class TicketCreate(BaseModel):
    lead_id: Optional[int] = None
    subject: str = Field(..., min_length=3, max_length=255)
    description: str
    priority: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|URGENT)$")


class TicketUpdate(BaseModel):
    subject: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(LOW|MEDIUM|HIGH|URGENT)$")
    status: Optional[TicketStatus] = None
    assigned_to: Optional[int] = None


class TicketResponse(TicketCreate):
    id: int
    tenant_id: int
    user_id: Optional[int]
    user_name: Optional[str] = None
    assigned_to: Optional[int]
    assigned_to_name: Optional[str] = None
    status: TicketStatus
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    comments: Optional[List['TicketCommentResponse']] = None
    model_config = ConfigDict(from_attributes=True)


class TicketCommentCreate(BaseModel):
    comment: str
    is_internal: bool = False


class TicketCommentResponse(TicketCommentCreate):
    id: int
    tenant_id: int
    ticket_id: int
    user_id: int
    user_name: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# 6. التتبع والتحليلات (Tracking & Analytics)
# ============================================================================

class InvitationTrackingCreate(BaseModel):
    invitation_id: int
    page_visited: Optional[str] = None
    actions: List[str] = []


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
    message: str


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


# ============================================================================
# 7. الإحصائيات (Stats)
# ============================================================================

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