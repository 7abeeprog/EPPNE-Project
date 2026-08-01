# app/domains/zamakana/models.py (الإصدار النهائي المتكامل - مع ترقية JSONB)
"""
نماذج (Models) قطاع الزمكان – محرك المعرفة والتأثير عبر الزمن
يدير: عقد المعرفة (الحقب، الابتكارات، الأحداث، الشخصيات)،
تأثير الفراشة (العلاقات السببية)، الحملات الكوكبية (تجميع ساعات تطوعية)،
وتحليل السيناريوهات المستقبلية.
"""
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text, Boolean,
    Numeric, Enum as SQLEnum, Index, CheckConstraint, text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ZamakanaNodeType(str, enum.Enum):
    ERA = "ERA"
    INNOVATION = "INNOVATION"
    PERSON = "PERSON"
    EVENT = "EVENT"


class ScenarioStatus(str, enum.Enum):
    DRAFTING = "DRAFTING"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    CONFIRMED = "CONFIRMED"


class ClaimStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    FIELD_VERIFIED = "FIELD_VERIFIED"
    ADMIN_APPROVED = "ADMIN_APPROVED"
    REJECTED = "REJECTED"


class PledgeStatus(str, enum.Enum):
    PENDING = "PENDING"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"


# ========== 1. عقد المعرفة (Knowledge Graph) ==========
class ZamakanaNode(Base):
    __tablename__ = "zamakana_nodes"
    __table_args__ = (
        Index("ix_zamakana_node_type_year", "node_type", "timeline_year"),
        Index("ix_zamakana_node_title", "title"),
        Index("ix_zamakana_node_created_at", "created_at"),
        {"extend_existing": True}  # ✅ إضافة هذا السطر لحل التعارض
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    node_type = Column(SQLEnum(ZamakanaNodeType), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    timeline_year = Column(Integer, nullable=True)
    geo_location = Column(String(255), nullable=True)

    verified_sources = Column(JSONB, default=list)
    extra_data = Column(JSONB, default=dict)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)


# ========== 2. حواف المعرفة (مع Multi-Tenancy + Idempotency) ==========
class ZamakanaEdge(Base):
    __tablename__ = "zamakana_edges"
    __table_args__ = (
        Index("ix_zamakana_edge_tenant", "tenant_id"),
        Index("ix_zamakana_edge_pair", "source_node_id", "target_node_id", unique=True),
        Index("ix_zamakana_edge_created_at", "created_at"),
        Index("ix_zamakana_edge_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
        {"extend_existing": True}  # ✅ إضافة هذا السطر
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    source_node_id = Column(Integer, ForeignKey("zamakana_nodes.id"), nullable=False, index=True)
    target_node_id = Column(Integer, ForeignKey("zamakana_nodes.id"), nullable=False, index=True)

    impact_description = Column(Text, nullable=False)
    impact_weight = Column(Numeric(4, 2), default=1.0)
    is_alternative_timeline = Column(Boolean, default=False)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ========== 3. الحملات الكوكبية والتعهدات الزمنية (Planetary Campaigns) ==========
class PlanetaryCampaign(Base):
    __tablename__ = "planetary_campaigns"
    __table_args__ = (
        Index("ix_planetary_campaign_tenant", "tenant_id"),
        Index("ix_planetary_campaign_created_at", "created_at"),
        Index("ix_planetary_campaign_status", "status"),
        {"extend_existing": True}  # ✅ إضافة هذا السطر
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    target_time_hours = Column(Numeric(15, 2), nullable=False)
    collected_time_hours = Column(Numeric(15, 2), default=0)

    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=False)

    status = Column(String(50), default="ACTIVE")
    campaign_contract_address = Column(String(42), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)


# ========== 4. التعهدات الزمنية (مع Multi-Tenancy + Idempotency) ==========
class TimePledge(Base):
    __tablename__ = "time_pledges"
    __table_args__ = (
        Index("ix_time_pledge_tenant", "tenant_id"),
        Index("ix_time_pledge_campaign", "campaign_id"),
        Index("ix_time_pledge_user", "user_id"),
        Index("ix_time_pledge_created_at", "created_at"),
        Index("ix_time_pledge_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
        {"extend_existing": True}  # ✅ إضافة هذا السطر
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    campaign_id = Column(Integer, ForeignKey("planetary_campaigns.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    pledged_hours = Column(Numeric(10, 2), nullable=False)
    skill_category = Column(String(100), nullable=True)

    status = Column(SQLEnum(PledgeStatus), default=PledgeStatus.PENDING)
    proof_hash = Column(String(100), nullable=True)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ========== 5. المحاكاة المستقبلية (Future Scenarios) ==========
class FutureScenario(Base):
    __tablename__ = "future_scenarios"
    __table_args__ = (
        Index("ix_future_scenario_tenant", "tenant_id"),
        Index("ix_future_scenario_created_at", "created_at"),
        Index("ix_future_scenario_status", "status"),
        {"extend_existing": True}  # ✅ إضافة هذا السطر
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    scenario_title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    target_year = Column(Integer, nullable=False)

    assumptions = Column(JSONB, default=dict)
    ai_analysis_report = Column(JSONB, nullable=True)
    ai_agent_id = Column(Integer, nullable=True)

    status = Column(SQLEnum(ScenarioStatus), default=ScenarioStatus.DRAFTING)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)


# ========== 6. المراجعات البشرية (مع Multi-Tenancy + Idempotency) ==========
class HumanFeedback(Base):
    __tablename__ = "human_feedbacks"
    __table_args__ = (
        Index("ix_human_feedback_tenant", "tenant_id"),
        Index("ix_human_feedback_scenario", "scenario_id"),
        Index("ix_human_feedback_created_at", "created_at"),
        Index("ix_human_feedback_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
        {"extend_existing": True}  # ✅ إضافة هذا السطر
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    scenario_id = Column(Integer, ForeignKey("future_scenarios.id"), nullable=False, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    feedback_text = Column(Text, nullable=False)
    agreement_score = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())