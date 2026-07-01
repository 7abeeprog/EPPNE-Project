# app/domains/invitations/models.py (الإصدار النهائي المتكامل)
"""
نماذج قطاع الدعوات والهدايا السيادية – مدعوم بالذكاء الاصطناعي
"""
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, JSON, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class InvitationType(str, enum.Enum):
    GENERAL = "GENERAL"           # رابط عام مفتوح للجميع
    PRIVATE = "PRIVATE"           # مرسلة لشخص/جهة محددة


class InvitationTargetType(str, enum.Enum):
    PERSON = "PERSON"
    CIVIL_ORGANIZATION = "CIVIL_ORGANIZATION"
    GOVERNMENT_BODY = "GOVERNMENT_BODY"
    INTERNATIONAL_ORGANIZATION = "INTERNATIONAL_ORGANIZATION"
    UNIVERSITY = "UNIVERSITY"
    COMPANY = "COMPANY"


class InvitationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"


class CampaignType(str, enum.Enum):
    BOOTCAMP = "BOOTCAMP"
    COURSE = "COURSE"
    SERVICE = "SERVICE"
    PRODUCT = "PRODUCT"
    EVENT = "EVENT"


class LeadStatus(str, enum.Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    QUALIFIED = "QUALIFIED"
    CONVERTED = "CONVERTED"
    LOST = "LOST"


class LeadSource(str, enum.Enum):
    INVITATION = "INVITATION"
    SOCIAL_FACEBOOK = "SOCIAL_FACEBOOK"
    SOCIAL_INSTAGRAM = "SOCIAL_INSTAGRAM"
    SOCIAL_LINKEDIN = "SOCIAL_LINKEDIN"
    SOCIAL_TWITTER = "SOCIAL_TWITTER"
    EMAIL = "EMAIL"
    REFERRAL = "REFERRAL"
    WEBSITE = "WEBSITE"


class CampaignStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class InteractionType(str, enum.Enum):
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    CHAT = "CHAT"
    MEETING = "MEETING"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"


class TicketStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


# ========== 1. الدعوات الأساسية (مع Idempotency + Multi-Tenancy) ==========
class SovereignInvitation(Base):
    __tablename__ = "sovereign_invitations_v2"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد

    sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    sender_entity_id = Column(Integer, nullable=True)

    invitation_type = Column(SQLEnum(InvitationType), nullable=False)
    target_type = Column(SQLEnum(InvitationTargetType), nullable=False)

    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    target_entity_identifier = Column(String(255), nullable=True)

    custom_message = Column(Text, nullable=True)
    title = Column(String(255), nullable=True)

    campaign_type = Column(SQLEnum(CampaignType), nullable=False)
    campaign_id = Column(Integer, nullable=False)

    discount_percentage = Column(Numeric(5, 2), default=0)
    gift_coins_amount = Column(Numeric(30, 8), default=0)
    gift_currency = Column(String(20), default="MR_USDT")

    max_uses = Column(Integer, default=1)
    current_uses = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(SQLEnum(InvitationStatus), default=InvitationStatus.DRAFT)

    assigned_ai_agent_id = Column(Integer, ForeignKey("ai_agents.id"), nullable=True)

    first_clicked_at = Column(DateTime(timezone=True), nullable=True)
    last_clicked_at = Column(DateTime(timezone=True), nullable=True)
    click_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_invitation_tenant", "tenant_id"),
        Index("ix_invitation_sender", "sender_user_id", "sender_entity_id"),
        Index("ix_invitation_target", "target_type", "target_user_id"),
        Index("ix_invitation_status_expiry", "status", "expires_at"),
    )


# ========== 2. تتبع سلوك المدعو ==========
class InvitationTracking(Base):
    __tablename__ = "invitation_tracking"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    invitation_id = Column(Integer, ForeignKey("sovereign_invitations_v2.id"), nullable=False, index=True)

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    device_type = Column(String(50), nullable=True)
    location_city = Column(String(100), nullable=True)
    location_country = Column(String(100), nullable=True)

    page_visited = Column(String(255), nullable=True)
    time_spent_seconds = Column(Integer, default=0)
    actions = Column(JSON, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_tracking_tenant_invitation", "tenant_id", "invitation_id"),
    )


# ========== 3. محادثات الذكاء الاصطناعي ==========
class InvitationConversation(Base):
    __tablename__ = "invitation_conversations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    invitation_id = Column(Integer, ForeignKey("sovereign_invitations_v2.id"), nullable=False, index=True)

    visitor_session_id = Column(String(255), nullable=True)
    visitor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    message = Column(Text, nullable=False)
    is_from_ai = Column(Boolean, default=True)
    ai_agent_id = Column(Integer, ForeignKey("ai_agents.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_conversation_tenant", "tenant_id"),
    )


# ========== 4. تحليلات الذكاء الاصطناعي للعميل ==========
class ClientInsight(Base):
    __tablename__ = "client_insights"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    invitation_id = Column(Integer, ForeignKey("sovereign_invitations_v2.id"), nullable=False, unique=True)

    ai_analysis = Column(JSON, nullable=False)
    recommended_discount = Column(Numeric(5, 2), nullable=True)
    recommended_message_template = Column(Text, nullable=True)

    readiness_score = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_insight_tenant", "tenant_id"),
    )


# ========== 5. العملاء المحتملون (Leads) – CRM Core ==========
class Lead(Base):
    __tablename__ = "crm_leads"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد

    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    company = Column(String(255), nullable=True)
    position = Column(String(255), nullable=True)

    source = Column(SQLEnum(LeadSource), nullable=False)
    source_reference = Column(String(255), nullable=True)

    status = Column(SQLEnum(LeadStatus), default=LeadStatus.NEW, index=True)
    score = Column(Integer, default=0)

    social_profiles = Column(JSON, default=dict)
    notes = Column(Text, nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)

    converted_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_lead_tenant_email", "tenant_id", "email"),
        Index("ix_lead_tenant_status", "tenant_id", "status"),
    )


# ========== 6. تفاعلات العملاء ==========
class CustomerInteraction(Base):
    __tablename__ = "crm_interactions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد

    lead_id = Column(Integer, ForeignKey("crm_leads.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    interaction_type = Column(SQLEnum(InteractionType), nullable=False)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    metadata = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_interaction_tenant_lead", "tenant_id", "lead_id"),
    )


# ========== 7. الحملات التسويقية ==========
class MarketingCampaign(Base):
    __tablename__ = "crm_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    campaign_type = Column(SQLEnum(CampaignType), nullable=False)
    target_audience = Column(JSON, default=dict)

    budget_mrusdt = Column(Numeric(30, 8), default=0)
    spent_mrusdt = Column(Numeric(30, 8), default=0)

    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)

    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.DRAFT, index=True)

    channels = Column(JSON, default=list)

    total_leads = Column(Integer, default=0)
    converted_leads = Column(Integer, default=0)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_campaign_tenant", "tenant_id"),
        Index("ix_campaign_tenant_status", "tenant_id", "status"),
        CheckConstraint("end_date > start_date", name="check_campaign_dates"),
    )


# ========== 8. تذاكر الدعم الفني ==========
class SupportTicket(Base):
    __tablename__ = "crm_tickets"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد

    lead_id = Column(Integer, ForeignKey("crm_leads.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)

    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(50), default="MEDIUM")
    status = Column(SQLEnum(TicketStatus), default=TicketStatus.OPEN, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_ticket_tenant", "tenant_id"),
    )


class TicketComment(Base):
    __tablename__ = "crm_ticket_comments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    ticket_id = Column(Integer, ForeignKey("crm_tickets.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    comment = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_comment_tenant_ticket", "tenant_id", "ticket_id"),
    )