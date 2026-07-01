# app/domains/arbitration_syndicates/models.py (الإصدار النهائي المتكامل)
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, JSON, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum

# ========== الأنواع المساعدة ==========
class DisputeStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"
    APPEALED = "APPEALED"

class JudgingMode(str, enum.Enum):
    AI_ONLY = "AI_ONLY"
    HUMAN_ONLY = "HUMAN_ONLY"
    AI_HYBRID = "AI_HYBRID"

class SyndicateType(str, enum.Enum):
    PROFESSIONAL = "PROFESSIONAL"      # نقابة مهنية (أطباء، مهندسون)
    TRADE = "TRADE"                    # غرفة تجارية
    LABOR = "LABOR"                    # نقابة عمالية
    COMMUNITY = "COMMUNITY"            # نقابة مجتمعية

class ElectionStatus(str, enum.Enum):
    UPCOMING = "UPCOMING"
    NOMINATION = "NOMINATION"
    VOTING = "VOTING"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

# ========== 1. التحكيم (مع Multi-Tenancy + Idempotency) ==========
class ArbitrationCase(Base):
    __tablename__ = "arbitration_cases"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    contract_id = Column(String(100), index=True, nullable=True)  # العقد محل النزاع
    claimant_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    respondent_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    dispute_reason = Column(Text, nullable=False)
    evidence_hashes = Column(JSON, default=list)  # روابط IPFS للأدلة
    judging_mode = Column(SQLEnum(JudgingMode), default=JudgingMode.AI_HYBRID)

    ai_judge_id = Column(Integer, nullable=True)  # من قطاع AI Agents
    status = Column(SQLEnum(DisputeStatus), default=DisputeStatus.OPEN, index=True)

    final_verdict = Column(Text, nullable=True)
    enforcement_tx_hash = Column(String(100), nullable=True)  # هاش تنفيذ الحكم

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)


class CrowdJury(Base):
    __tablename__ = "crowd_juries"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    case_id = Column(Integer, ForeignKey("arbitration_cases.id"), nullable=False, index=True)
    juror_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    vote = Column(Boolean, nullable=True)  # True = لصالح المدعي, False = لصالح المدعى عليه
    justification = Column(Text, nullable=True)
    reward_mr7 = Column(Numeric(15, 8), default=0)  # مكافأة المحلف

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_crowd_jury_tenant", "tenant_id"),
        Index("ix_crowd_jury_case_unique", "case_id", "juror_id", unique=True),
    )


# ========== 2. النقابات (مع Multi-Tenancy + Idempotency) ==========
class SovereignSyndicate(Base):
    __tablename__ = "sovereign_syndicates"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    syndicate_type = Column(SQLEnum(SyndicateType), nullable=False)
    description = Column(Text, nullable=True)

    annual_fee_mrusdt = Column(Numeric(30, 8), default=0)
    is_active = Column(Boolean, default=True)

    # العقود الذكية للنقابة (DAO)
    dao_contract_address = Column(String(42), nullable=True)
    treasury_wallet_address = Column(String(42), nullable=True)
    governance_token = Column(String(42), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)


class SyndicateMembership(Base):
    __tablename__ = "syndicate_memberships"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    syndicate_id = Column(Integer, ForeignKey("sovereign_syndicates.id"), nullable=False, index=True)
    member_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    membership_number = Column(String(100), unique=True, nullable=False)
    join_date = Column(DateTime(timezone=True), nullable=False)
    expiry_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="ACTIVE", index=True)

    # الكارنيه كـ Soulbound Token (SBT)
    membership_sbt_id = Column(String(100), unique=True, nullable=True)
    minting_tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("expiry_date > join_date", name="check_membership_dates"),
        Index("ix_syndicate_membership_tenant", "tenant_id"),
        Index("ix_syndicate_membership_active", "syndicate_id", "status"),
    )


class ProfessionalLicense(Base):
    __tablename__ = "professional_licenses"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    syndicate_id = Column(Integer, ForeignKey("sovereign_syndicates.id"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    license_name = Column(String(255), nullable=False)
    license_number = Column(String(100), unique=True, nullable=False)

    # الشهادات المطلوبة من الأكاديمية
    required_certificate_id = Column(Integer, nullable=True)  # من academy_courses
    qualifies_for_job_id = Column(Integer, nullable=True)     # من sovereign_jobs

    issue_date = Column(DateTime(timezone=True), nullable=False)
    expiry_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="VALID")

    # الرخصة كـ SBT
    license_sbt_id = Column(String(100), unique=True, nullable=True)
    minting_tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        CheckConstraint("expiry_date > issue_date", name="check_license_dates"),
        Index("ix_license_tenant", "tenant_id"),
    )


# ========== 3. الانتخابات النقابية (مع Multi-Tenancy + Idempotency) ==========
class SyndicateElection(Base):
    __tablename__ = "syndicate_elections"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    syndicate_id = Column(Integer, ForeignKey("sovereign_syndicates.id"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    election_type = Column(String(50), nullable=False)  # BOARD, PRESIDENT, COMMITTEE
    election_year = Column(Integer, nullable=False)

    nomination_start = Column(DateTime(timezone=True), nullable=False)
    nomination_end = Column(DateTime(timezone=True), nullable=False)
    voting_start = Column(DateTime(timezone=True), nullable=False)
    voting_end = Column(DateTime(timezone=True), nullable=False)

    status = Column(SQLEnum(ElectionStatus), default=ElectionStatus.UPCOMING, index=True)

    # العقد الذكي للانتخابات
    smart_contract_address = Column(String(42), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        CheckConstraint("nomination_end > nomination_start", name="check_nomination_dates"),
        CheckConstraint("voting_start > nomination_end", name="check_voting_start"),
        CheckConstraint("voting_end > voting_start", name="check_voting_end"),
    )


class ElectionCandidate(Base):
    __tablename__ = "election_candidates"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    election_id = Column(Integer, ForeignKey("syndicate_elections.id"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    manifesto = Column(Text, nullable=False)
    campaign_budget_allocation_id = Column(Integer, nullable=True)  # من قطاع المالية
    status = Column(String(50), default="APPROVED")  # PENDING, APPROVED, REJECTED

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_candidate_tenant", "tenant_id"),
    )


class ElectionVote(Base):
    __tablename__ = "election_votes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    election_id = Column(Integer, ForeignKey("syndicate_elections.id"), nullable=False, index=True)
    voter_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("election_candidates.id"), nullable=False)

    vote_hash = Column(String(255), unique=True, nullable=False)          # هاش التصويت (لإخفاء الهوية)
    blockchain_tx_hash = Column(String(100), unique=True, nullable=True)  # تسجيل الصوت على السلسلة

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_election_vote_tenant", "tenant_id"),
        Index("ix_election_vote_unique_voter", "election_id", "voter_user_id", unique=True),
    )