# app/domains/insurance/models.py
"""
نماذج (Models) قطاع التأمينات السيادية
"""
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, Enum as SQLEnum, Index, CheckConstraint, text
)
from sqlalchemy.dialects.postgresql import JSONB  # ✅ تم إضافة الاستيراد الصحيح
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class PolicyType(str, enum.Enum):
    MEDICAL = "MEDICAL"
    ACCIDENT = "ACCIDENT"
    LIFE = "LIFE"
    FLEET = "FLEET"
    CARGO = "CARGO"
    PROJECT = "PROJECT"
    EMPLOYEE_BENEFITS = "EMPLOYEE_BENEFITS"


class PremiumCycle(str, enum.Enum):
    ONE_TIME = "ONE_TIME"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUALLY = "ANNUALLY"


class ClaimStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAID = "PAID"


class PensionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


# ========== 1. بوالص التأمين ==========
class InsurancePolicy(Base):
    __tablename__ = "insurance_policies"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    issuer_entity_id = Column(Integer, ForeignKey("sovereign_entities_v2.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    policy_type = Column(SQLEnum(PolicyType), nullable=False, index=True)
    description = Column(Text, nullable=True)

    base_premium_mrusdt = Column(Numeric(30, 8), nullable=False)
    premium_cycle = Column(SQLEnum(PremiumCycle), default=PremiumCycle.MONTHLY)
    max_coverage_limit_mrusdt = Column(Numeric(30, 8), nullable=False)

    terms_and_conditions = Column(JSONB, default=dict)

    is_active = Column(Boolean, default=True)

    smart_contract_address = Column(String(42), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_policy_type_active", "policy_type", "is_active"),
        Index("ix_policy_created_at", "created_at"),
    )


# ========== 2. الاشتراكات التأمينية ==========
class InsuranceSubscription(Base):
    __tablename__ = "insurance_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    policy_id = Column(Integer, ForeignKey("insurance_policies.id"), nullable=False, index=True)

    subscriber_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    fleet_id = Column(Integer, nullable=True, index=True)
    land_asset_id = Column(Integer, nullable=True, index=True)
    project_id = Column(Integer, nullable=True, index=True)
    bio_asset_id = Column(Integer, nullable=True, index=True)
    shipment_id = Column(Integer, nullable=True, index=True)
    employment_contract_id = Column(Integer, nullable=True, index=True)

    beneficiaries_json = Column(JSONB, nullable=True)

    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="ACTIVE", index=True)

    policy_nft_id = Column(String(100), unique=True, nullable=True)
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
        Index("ix_subscription_created_at", "created_at"),
        Index("ix_subscription_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


# ========== 3. مطالبات التعويض ==========
class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    subscription_id = Column(Integer, ForeignKey("insurance_subscriptions.id"), nullable=False, index=True)
    claimant_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    incident_date = Column(DateTime(timezone=True), nullable=False)
    incident_description = Column(Text, nullable=False)
    evidence_urls = Column(JSONB, default=list)

    claimed_amount_mrusdt = Column(Numeric(30, 8), nullable=False)
    approved_amount_mrusdt = Column(Numeric(30, 8), default=0)

    status = Column(SQLEnum(ClaimStatus), default=ClaimStatus.SUBMITTED, index=True)
    investigation_notes = Column(Text, nullable=True)
    oracle_verification_hash = Column(String(100), nullable=True)

    payout_tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_claim_tenant", "tenant_id"),
        Index("ix_claim_created_at", "created_at"),
        Index("ix_claim_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


# ========== 4. سجلات المعاشات ==========
class PensionRecord(Base):
    __tablename__ = "pension_records"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    beneficiary_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_entity_id = Column(Integer, ForeignKey("sovereign_entities_v2.id", ondelete="SET NULL"), nullable=True)
    pension_type = Column(String(50), index=True)
    monthly_amount_mrusdt = Column(Numeric(30, 8), nullable=False)

    total_disbursed_mrusdt = Column(Numeric(30, 8), default=0)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)

    status = Column(SQLEnum(PensionStatus), default=PensionStatus.ACTIVE, index=True)

    streaming_contract_address = Column(String(42), nullable=True)
    last_payout_tx = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_pension_tenant", "tenant_id"),
        Index("ix_pension_created_at", "created_at"),
        Index("ix_pension_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


# ========== 5. ملفات التأمين للموظفين ==========
class EmployeeInsuranceProfile(Base):
    __tablename__ = "employee_insurance_profiles"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    government_insurance_number = Column(String(50), unique=True, nullable=False)

    employee_share_percentage = Column(Numeric(5, 2), nullable=False)
    employer_share_percentage = Column(Numeric(5, 2), nullable=False)

    total_contributed_mrusdt = Column(Numeric(30, 8), default=0)
    last_contribution_date = Column(DateTime(timezone=True), nullable=True)

    status = Column(String(50), default="ACTIVE", index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_employee_profile_tenant", "tenant_id"),
        Index("ix_employee_profile_created_at", "created_at"),
    )