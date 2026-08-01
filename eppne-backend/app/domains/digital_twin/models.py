# app/domains/digital_twin/models.py
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB  # ✅ تم إضافة الاستيراد الصحيح
from sqlalchemy.sql import func
from app.core.database import Base
import enum

# ========== الأنواع المساعدة ==========
class TwinAccessLevel(str, enum.Enum):
    PRIVATE = "PRIVATE"          # فقط المالك
    FAMILY = "FAMILY"            # العائلة فقط
    PAID_ONLY = "PAID_ONLY"      # من يدفع رسوم التفاعل
    PUBLIC = "PUBLIC"            # عام

class TwinCapability(str, enum.Enum):
    CHAT = "CHAT"
    MEETING_ATTENDANCE = "MEETING"
    FINANCIAL_ADVICE = "FINANCE"
    SIGNATURE_AUTHORITY = "SIGN"
    LEGACY_TELLER = "LEGACY"

class LifeStatus(str, enum.Enum):
    ALIVE = "ALIVE"
    DECEASED = "DECEASED"
    PRESUMED_DEAD = "PRESUMED_DEAD"
    LEGACY_MODE = "LEGACY_MODE"

class MilestoneType(str, enum.Enum):
    IDENTITY_RESERVATION = "IDENTITY_RESERVATION"
    BIRTH = "BIRTH"
    GRADUATION = "GRADUATION"
    MARRIAGE = "MARRIAGE"
    PATENT = "PATENT"
    DECEASE_CONFIRMATION = "DECEASE_CONFIRMATION"


# ========== 1. التوأم الرقمي (Digital Twin) ==========
class DigitalTwinConfig(Base):
    __tablename__ = "digital_twin_configs"
    __table_args__ = (
        Index("ix_digital_twin_tenant_user", "tenant_id", "user_id"),
        Index("ix_digital_twin_agent", "agent_id"),
        Index("ix_digital_twin_active", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    agent_id = Column(Integer, nullable=True)

    global_access_level = Column(SQLEnum(TwinAccessLevel), default=TwinAccessLevel.PRIVATE)
    interaction_fee_mrusdt = Column(Numeric(15, 8), default=0)
    subscription_monthly_mrusdt = Column(Numeric(15, 8), default=0)

    capabilities = Column(JSONB, default=list)
    knowledge_boundaries = Column(JSONB, default=dict)

    max_spending_limit = Column(Numeric(15, 8), default=0)

    is_active = Column(Boolean, default=True)
    settlement_type = Column(String(50), default="WEB2_FIAT")
    physical_embodiment_status = Column(String(50), default="DIGITAL_ONLY")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TwinPermission(Base):
    __tablename__ = "twin_permissions"
    __table_args__ = (
        Index("ix_twin_permission_tenant_twin", "tenant_id", "twin_config_id"),
        Index("ix_twin_permission_grantee", "grantee_user_id"),
        Index("ix_twin_permission_unique", "twin_config_id", "grantee_user_id", unique=True, postgresql_where="grantee_user_id IS NOT NULL"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    twin_config_id = Column(Integer, ForeignKey("digital_twin_configs.id"), nullable=False, index=True)
    grantee_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    grantee_rank = Column(String(50), nullable=True)
    access_granted = Column(Boolean, default=True)
    override_fee = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TwinInteractionLog(Base):
    __tablename__ = "twin_interaction_logs"
    __table_args__ = (
        Index("ix_twin_interaction_tenant_twin", "tenant_id", "twin_config_id"),
        Index("ix_twin_interaction_visitor", "visitor_id"),
        Index("ix_twin_interaction_idempotency", "idempotency_key", unique=True, postgresql_where="idempotency_key IS NOT NULL"),
        Index("ix_twin_interaction_created", "created_at"),
        Index("ix_twin_interaction_visitor_created", "visitor_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    twin_config_id = Column(Integer, ForeignKey("digital_twin_configs.id"), nullable=False, index=True)
    visitor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    interaction_type = Column(String(50), nullable=False)
    duration_minutes = Column(Integer, default=0)

    fee_paid_mrusdt = Column(Numeric(15, 8), default=0)
    payout_tx_hash = Column(String(100), nullable=True)

    is_affiliate_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ========== 2. خزائن الزمن والوصايا (Legacy & Time Capsules) ==========
class TimeCapsule(Base):
    __tablename__ = "time_capsules"
    __table_args__ = (
        Index("ix_time_capsule_tenant_user", "tenant_id", "user_id"),
        Index("ix_time_capsule_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    encrypted_payload_hash = Column(Text, nullable=False)
    video_will_ipfs = Column(String(100), nullable=True)

    heartbeat_interval_days = Column(Integer, default=90)
    last_heartbeat_at = Column(DateTime(timezone=True), server_default=func.now())

    ai_avatar_access_id = Column(Integer, nullable=True)

    status = Column(String(50), default="ALIVE")

    encrypted_credentials = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyBeneficiary(Base):
    __tablename__ = "legacy_beneficiaries"
    __table_args__ = (
        Index("ix_legacy_beneficiary_tenant_capsule", "tenant_id", "capsule_id"),
        Index("ix_legacy_beneficiary_user", "beneficiary_user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    capsule_id = Column(Integer, ForeignKey("time_capsules.id"), nullable=False, index=True)
    beneficiary_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    relationship_type = Column(String(50), nullable=True)
    access_share_percentage = Column(Integer, default=100)
    heir_wallet_address = Column(String(42), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DigitalWill(Base):
    __tablename__ = "digital_wills"
    __table_args__ = (
        Index("ix_digital_will_tenant_user", "tenant_id", "user_id"),
        Index("ix_digital_will_nft", "will_nft_id", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    will_content_ipfs = Column(String(100), nullable=False)
    will_nft_id = Column(String(100), unique=True, nullable=False)
    legal_witness_tx = Column(String(100), nullable=True)

    is_executed = Column(Boolean, default=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ========== 3. أوراكل الموت (Death Oracle) ==========
class DeathOracleCheck(Base):
    __tablename__ = "death_oracle_checks"
    __table_args__ = (
        Index("ix_death_oracle_tenant_user", "tenant_id", "user_id"),
        Index("ix_death_oracle_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    check_interval_days = Column(Integer, default=30)
    last_confirmed_alive_at = Column(DateTime(timezone=True), server_default=func.now())
    grace_period_days = Column(Integer, default=7)

    status = Column(String(50), default="MONITORING")

    official_death_certificate_ipfs = Column(String(100), nullable=True)
    release_tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ========== 4. محطات الحياة (Life Milestones) ==========
class LifeMilestone(Base):
    __tablename__ = "life_milestones"
    __table_args__ = (
        Index("ix_life_milestone_tenant_user", "tenant_id", "user_id"),
        Index("ix_life_milestone_type", "milestone_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    milestone_type = Column(SQLEnum(MilestoneType), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String(1024), nullable=True)

    milestone_nft_id = Column(String(100), unique=True, nullable=True)
    evidence_ipfs_hash = Column(String(100), nullable=True)

    occurrence_date = Column(DateTime(timezone=True), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ========== 5. الحجز قبل الولادة (Pre-Birth Identity) ==========
class PreBirthRecord(Base):
    __tablename__ = "pre_birth_records"
    __table_args__ = (
        Index("ix_pre_birth_tenant_parent", "tenant_id", "parent_1_id"),
        Index("ix_pre_birth_sovereign_id", "reserved_sovereign_id", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    parent_1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_2_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    reserved_sovereign_id = Column(String(100), unique=True, nullable=False)
    trust_fund_wallet = Column(String(42), nullable=True)

    expected_arrival_date = Column(DateTime(timezone=True), nullable=True)
    genetic_profile_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())