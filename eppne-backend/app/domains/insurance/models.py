# app/domains/insurance/models.py (الإصدار النهائي المتكامل)
"""
نماذج (Models) قطاع التأمينات السيادية
يدعم: بوالص التأمين (Policies)، الاشتراكات (Subscriptions)، المطالبات (Claims)،
المعاشات (Pensions)، وملفات التأمين للموظفين
"""
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, JSON, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class PolicyType(str, enum.Enum):
    MEDICAL = "MEDICAL"               # تأمين صحي
    ACCIDENT = "ACCIDENT"             # تأمين حوادث
    LIFE = "LIFE"                     # تأمين على الحياة
    FLEET = "FLEET"                   # تأمين أساطيل
    CARGO = "CARGO"                   # تأمين شحنات
    PROJECT = "PROJECT"               # تأمين مشاريع
    EMPLOYEE_BENEFITS = "EMPLOYEE_BENEFITS"  # تأمينات الموظفين


class PremiumCycle(str, enum.Enum):
    ONE_TIME = "ONE_TIME"             # دفعة واحدة
    MONTHLY = "MONTHLY"               # شهري
    QUARTERLY = "QUARTERLY"           # ربع سنوي
    ANNUALLY = "ANNUALLY"             # سنوي


class ClaimStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"           # تم التقديم
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAID = "PAID"


class PensionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


# ========== 1. بوالص التأمين (Policies) ==========
class InsurancePolicy(Base):
    __tablename__ = "insurance_policies"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    issuer_entity_id = Column(Integer, nullable=False, index=True) # TODO: add ForeignKey to sovereign_entities
    name = Column(String(255), nullable=False)
    policy_type = Column(SQLEnum(PolicyType), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # الشروط المالية
    base_premium_mrusdt = Column(Numeric(30, 8), nullable=False)      # القسط الأساسي
    premium_cycle = Column(SQLEnum(PremiumCycle), default=PremiumCycle.MONTHLY)
    max_coverage_limit_mrusdt = Column(Numeric(30, 8), nullable=False)  # الحد الأقصى للتغطية

    # شروط إضافية (JSON مرن)
    terms_and_conditions = Column(JSON, default=dict)

    is_active = Column(Boolean, default=True)

    # العقود الذكية
    smart_contract_address = Column(String(42), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_policy_type_active", "policy_type", "is_active"),
    )


# ========== 2. الاشتراكات التأمينية (مع Multi-Tenancy + Idempotency) ==========
class InsuranceSubscription(Base):
    __tablename__ = "insurance_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    policy_id = Column(Integer, ForeignKey("insurance_policies.id"), nullable=False, index=True)

    # الكيان المؤمَّن (واحد فقط من التالي)
    subscriber_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    fleet_id = Column(Integer, nullable=True, index=True)          # من قطاع النقل
    land_asset_id = Column(Integer, nullable=True, index=True)    # من قطاع العقارات
    project_id = Column(Integer, nullable=True, index=True)       # من قطاع المشاريع
    bio_asset_id = Column(Integer, nullable=True, index=True)     # من قطاع الزراعة
    shipment_id = Column(Integer, nullable=True, index=True)      # من قطاع اللوجستيات
    employment_contract_id = Column(Integer, nullable=True, index=True)  # من قطاع التوظيف

    # المستفيدون (JSON)
    beneficiaries_json = Column(JSON, nullable=True)

    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="ACTIVE", index=True)

    # التوثيق
    policy_nft_id = Column(String(100), unique=True, nullable=True)   # وثيقة التأمين كـ NFT
    subscription_tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "((subscriber_user_id IS NOT NULL)::int + (fleet_id IS NOT NULL)::int + "
            "(land_asset_id IS NOT NULL)::int + (project_id IS NOT NULL)::int + "
            "(bio_asset_id IS NOT NULL)::int + (shipment_id IS NOT NULL)::int + "
            "(employment_contract_id IS NOT NULL)::int) = 1",
            name="chk_exclusive_insurance_target"
        ),
        Index("ix_subscription_tenant", "tenant_id"),
        Index("ix_subscription_status_dates", "status", "start_date", "end_date"),
    )


# ========== 3. مطالبات التعويض (مع Multi-Tenancy + Idempotency) ==========
class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    subscription_id = Column(Integer, ForeignKey("insurance_subscriptions.id"), nullable=False, index=True)
    claimant_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    incident_date = Column(DateTime(timezone=True), nullable=False)
    incident_description = Column(Text, nullable=False)
    evidence_urls = Column(JSON, default=list)          # روابط للأدلة (صور، فيديوهات، مستندات)

    claimed_amount_mrusdt = Column(Numeric(30, 8), nullable=False)
    approved_amount_mrusdt = Column(Numeric(30, 8), default=0)

    status = Column(SQLEnum(ClaimStatus), default=ClaimStatus.SUBMITTED, index=True)
    investigation_notes = Column(Text, nullable=True)
    oracle_verification_hash = Column(String(100), nullable=True)  # تحقق Oracle (للحوادث)

    payout_tx_hash = Column(String(100), nullable=True)            # هاش صرف التعويض

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_claim_tenant", "tenant_id"),
    )


# ========== 4. سجلات المعاشات (مع Multi-Tenancy) ==========
class PensionRecord(Base):
    __tablename__ = "pension_records"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    beneficiary_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_entity_id = Column(Integer, nullable=True) # TODO: add ForeignKey to sovereign_entities
    pension_type = Column(String(50), index=True)  # RETIREMENT, DISABILITY, SURVIVOR
    monthly_amount_mrusdt = Column(Numeric(30, 8), nullable=False)

    total_disbursed_mrusdt = Column(Numeric(30, 8), default=0)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)

    status = Column(SQLEnum(PensionStatus), default=PensionStatus.ACTIVE, index=True)

    streaming_contract_address = Column(String(42), nullable=True)  # عقد ذكي للدفع الشهري
    last_payout_tx = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_pension_tenant", "tenant_id"),
    )


# ========== 5. ملفات التأمين للموظفين (مع Multi-Tenancy) ==========
class EmployeeInsuranceProfile(Base):
    __tablename__ = "employee_insurance_profiles"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    government_insurance_number = Column(String(50), unique=True, nullable=False)

    employee_share_percentage = Column(Numeric(5, 2), nullable=False)   # نسبة استقطاع الموظف
    employer_share_percentage = Column(Numeric(5, 2), nullable=False)   # نسبة صاحب العمل

    total_contributed_mrusdt = Column(Numeric(30, 8), default=0)
    last_contribution_date = Column(DateTime(timezone=True), nullable=True)

    status = Column(String(50), default="ACTIVE", index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_employee_profile_tenant", "tenant_id"),
    )