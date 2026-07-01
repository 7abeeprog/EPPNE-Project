# app/domains/digital_twin/models.py
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, JSON, Enum as SQLEnum, Index, CheckConstraint
)
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
    LEGACY_MODE = "LEGACY_MODE"   # بعد الوفاة، يعمل كـ avatar إرثي

class MilestoneType(str, enum.Enum):
    IDENTITY_RESERVATION = "IDENTITY_RESERVATION"  # حجز هوية الجنين
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
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    agent_id = Column(Integer, nullable=True)  # من قطاع AI Agents (التوأم كـ Agent)

    # إعدادات الخصوصية والاقتصاد
    global_access_level = Column(SQLEnum(TwinAccessLevel), default=TwinAccessLevel.PRIVATE)
    interaction_fee_mrusdt = Column(Numeric(15, 8), default=0)
    subscription_monthly_mrusdt = Column(Numeric(15, 8), default=0)

    capabilities = Column(JSON, default=list)       # قائمة بـ TwinCapability
    knowledge_boundaries = Column(JSON, default=dict)  # حدود معرفة التوأم (ما يمكنه فعله)

    max_spending_limit = Column(Numeric(15, 8), default=0)  # حد الإنفاق نيابة عن المالك

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
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    twin_config_id = Column(Integer, ForeignKey("digital_twin_configs.id"), nullable=False, index=True)
    grantee_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    grantee_rank = Column(String(50), nullable=True)        # أو منح الصلاحية بناءً على الرتبة السيادية
    access_granted = Column(Boolean, default=True)
    override_fee = Column(Boolean, default=False)          # هل يُعفى من رسوم التفاعل؟

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TwinInteractionLog(Base):
    __tablename__ = "twin_interaction_logs"
    __table_args__ = (
        Index("ix_twin_interaction_tenant_twin", "tenant_id", "twin_config_id"),
        Index("ix_twin_interaction_visitor", "visitor_id"),
        Index("ix_twin_interaction_idempotency", "idempotency_key", unique=True, postgresql_where="idempotency_key IS NOT NULL"),
        Index("ix_twin_interaction_created", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    twin_config_id = Column(Integer, ForeignKey("digital_twin_configs.id"), nullable=False, index=True)
    visitor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 🔥 Idempotency Key (لمنع تسجيل التفاعلات المكررة)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    interaction_type = Column(String(50), nullable=False)  # TEXT, VOICE, METAVERSE_AVATAR
    duration_minutes = Column(Integer, default=0)

    fee_paid_mrusdt = Column(Numeric(15, 8), default=0)
    payout_tx_hash = Column(String(100), nullable=True)

    is_affiliate_enabled = Column(Boolean, default=False)  # هل حصل الداعي على عمولة؟
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ========== 2. خزائن الزمن والوصايا (Legacy & Time Capsules) ==========
class TimeCapsule(Base):
    __tablename__ = "time_capsules"
    __table_args__ = (
        Index("ix_time_capsule_tenant_user", "tenant_id", "user_id"),
        Index("ix_time_capsule_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    # الرسائل والفيديوهات المشفرة
    encrypted_payload_hash = Column(Text, nullable=False)  # هاش المحتوى المشفر
    video_will_ipfs = Column(String(100), nullable=True)   # فيديو وصية على IPFS

    # نبضات الحياة
    heartbeat_interval_days = Column(Integer, default=90)
    last_heartbeat_at = Column(DateTime(timezone=True), server_default=func.now())

    # من يملك حق فتح الخزنة بعد الوفاة (AI Avatar)
    ai_avatar_access_id = Column(Integer, nullable=True)   # مؤشر لـ AIAgent

    status = Column(String(50), default="ALIVE")  # ALIVE, DECEASED, UNLOCKED

    encrypted_credentials = Column(JSON, nullable=True)   # مفاتيح المحافظ المشفرة

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LegacyBeneficiary(Base):
    __tablename__ = "legacy_beneficiaries"
    __table_args__ = (
        Index("ix_legacy_beneficiary_tenant_capsule", "tenant_id", "capsule_id"),
        Index("ix_legacy_beneficiary_user", "beneficiary_user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    capsule_id = Column(Integer, ForeignKey("time_capsules.id"), nullable=False, index=True)
    beneficiary_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    relationship_type = Column(String(50), nullable=True)   # SON, DAUGHTER, SPOUSE, CHARITY
    access_share_percentage = Column(Integer, default=100)  # نسبة ما سيحصل عليه من الأصول
    heir_wallet_address = Column(String(42), nullable=False)  # محفظة الوريث

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DigitalWill(Base):
    __tablename__ = "digital_wills"
    __table_args__ = (
        Index("ix_digital_will_tenant_user", "tenant_id", "user_id"),
        Index("ix_digital_will_nft", "will_nft_id", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    will_content_ipfs = Column(String(100), nullable=False)  # نص الوصية على IPFS
    will_nft_id = Column(String(100), unique=True, nullable=False)  # NFT لتوثيق الوصية
    legal_witness_tx = Column(String(100), nullable=True)    # توقيع الشهود

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
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    check_interval_days = Column(Integer, default=30)   # كم مرة يتم فحص النبض
    last_confirmed_alive_at = Column(DateTime(timezone=True), server_default=func.now())
    grace_period_days = Column(Integer, default=7)      # مهلة بعد انقطاع النبض

    status = Column(String(50), default="MONITORING")   # MONITORING, ALIVE_AND_WELL, DEATH_PENDING, DEATH_CONFIRMED

    official_death_certificate_ipfs = Column(String(100), nullable=True)
    release_tx_hash = Column(String(100), nullable=True)  # هاش تفعيل توزيع الإرث

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
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    milestone_type = Column(SQLEnum(MilestoneType), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String(1024), nullable=True)

    milestone_nft_id = Column(String(100), unique=True, nullable=True)  # NFT كشهادة إنجاز
    evidence_ipfs_hash = Column(String(100), nullable=True)             # دليل (شهادة ميلاد، عقد زواج، براءة اختراع)

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
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    parent_1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_2_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    reserved_sovereign_id = Column(String(100), unique=True, nullable=False)  # الاسم السيادي المحجوز للطفل
    trust_fund_wallet = Column(String(42), nullable=True)                     # محفظة للاستثمار للطفل

    expected_arrival_date = Column(DateTime(timezone=True), nullable=True)
    genetic_profile_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())