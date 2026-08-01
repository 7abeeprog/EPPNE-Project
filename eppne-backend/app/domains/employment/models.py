# app/domains/employment/models.py
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, Enum as SQLEnum, Index, CheckConstraint, text
)
from sqlalchemy.dialects.postgresql import JSONB  # ✅ تم إضافة الاستيراد الصحيح
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class EmploymentStatus(str, enum.Enum):
    WAITING_SIGNATURE = "WAITING_SIGNATURE"
    PROBATION = "PROBATION"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


class LeaveType(str, enum.Enum):
    ANNUAL = "ANNUAL"
    SICK = "SICK"
    UNPAID = "UNPAID"
    MATERNITY = "MATERNITY"
    BEREAVEMENT = "BEREAVEMENT"


class PayrollStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    PAID = "PAID"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    HALF_DAY = "HALF_DAY"


# ============================================================
# 1. الوظائف والتقديم (Job Listings & Applications)
# ============================================================

class JobListing(Base):
    __tablename__ = "job_listings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text)
    required_skills = Column(JSONB, default=list)
    required_certificate_ids = Column(JSONB, default=list)
    required_rank = Column(String(50), nullable=True)

    salary_min = Column(Numeric(30, 8), nullable=True)
    salary_max = Column(Numeric(30, 8), nullable=True)
    currency = Column(String(20), default="MR_USDT")

    location = Column(String(255), nullable=True)
    employment_type = Column(String(50), default="FULL_TIME")
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_job_listings_active", "is_active", "created_at"),
        Index("ix_job_listings_tenant_active", "tenant_id", "is_active"),
    )


class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_listings.id"), nullable=False, index=True)
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    cover_letter = Column(Text, nullable=True)
    resume_url = Column(String(1024), nullable=True)

    ai_match_score = Column(Numeric(5, 2), nullable=True)
    status = Column(String(50), default="PENDING")

    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_job_applications_status", "status"),
        Index("ix_job_applications_job_status", "job_id", "status"),
        CheckConstraint("ai_match_score >= 0 AND ai_match_score <= 100", name="check_match_score"),
    )


# ============================================================
# 2. عقود العمل الذكية (Employment Contracts) – مع Idempotency
# ============================================================

class EmploymentContract(Base):
    __tablename__ = "employment_contracts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("job_applications.id"), nullable=False, unique=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    job_title = Column(String(255), nullable=False)
    base_salary = Column(Numeric(30, 8), nullable=False)
    allowances = Column(JSONB, default=dict)
    currency = Column(String(20), default="MR_USDT")

    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    probation_days = Column(Integer, default=90)
    annual_leave_days = Column(Integer, default=21)

    status = Column(SQLEnum(EmploymentStatus), default=EmploymentStatus.WAITING_SIGNATURE)

    smart_contract_address = Column(String(42), nullable=True)
    signature_tx_hash = Column(String(100), nullable=True)
    employer_signature_tx = Column(String(100), nullable=True)

    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_contract_tenant_status", "tenant_id", "status"),
        Index("ix_contract_employee_status", "employee_id", "status"),
        Index("ix_contract_tenant_employee", "tenant_id", "employee_id"),
        Index("ix_contract_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


# ============================================================
# 3. الحضور والإجازات (Attendance & Leave) – مع Idempotency
# ============================================================

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("employment_contracts.id"), nullable=False, index=True)

    date = Column(DateTime(timezone=True), nullable=False)
    check_in = Column(DateTime(timezone=True), nullable=True)
    check_out = Column(DateTime(timezone=True), nullable=True)
    check_in_location = Column(JSONB, nullable=True)
    check_out_location = Column(JSONB, nullable=True)

    hours_worked = Column(Numeric(5, 2), default=0)
    overtime_hours = Column(Numeric(5, 2), default=0)
    status = Column(SQLEnum(AttendanceStatus), default=AttendanceStatus.ABSENT)

    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_attendance_contract_date", "contract_id", "date", unique=True),
        Index("ix_attendance_tenant_contract", "tenant_id", "contract_id"),
        Index("ix_attendance_tenant_date", "tenant_id", "date"),
        Index("ix_attendance_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("employment_contracts.id"), nullable=False, index=True)

    leave_type = Column(SQLEnum(LeaveType), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    reason = Column(Text, nullable=True)

    status = Column(String(50), default="PENDING")
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="check_leave_dates"),
        Index("ix_leave_tenant_contract", "tenant_id", "contract_id"),
        Index("ix_leave_tenant_status", "tenant_id", "status"),
        Index("ix_leave_created_at", "created_at"),
    )


# ============================================================
# 4. كشوف المرتبات والتسويات (Payroll) – مع Idempotency
# ============================================================

class PayrollRecord(Base):
    __tablename__ = "payroll_records"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("employment_contracts.id"), nullable=False, index=True)

    month = Column(String(20), nullable=False)
    base_salary = Column(Numeric(30, 8), nullable=False)
    bonuses = Column(Numeric(30, 8), default=0)
    overtime_pay = Column(Numeric(30, 8), default=0)
    deductions = Column(JSONB, default=dict)
    net_salary = Column(Numeric(30, 8), nullable=False)

    status = Column(SQLEnum(PayrollStatus), default=PayrollStatus.DRAFT)
    payment_tx_hash = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_payroll_contract_month", "contract_id", "month", unique=True),
        Index("ix_payroll_tenant_contract", "tenant_id", "contract_id"),
        Index("ix_payroll_tenant_status", "tenant_id", "status"),
        Index("ix_payroll_month", "month"),
        Index("ix_payroll_created_at", "created_at"),
        Index("ix_payroll_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


class PayrollAdjustment(Base):
    __tablename__ = "payroll_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("employment_contracts.id"), nullable=False, index=True)
    payroll_id = Column(Integer, ForeignKey("payroll_records.id"), nullable=True)

    adjustment_type = Column(String(50), nullable=False)
    amount = Column(Numeric(30, 8), nullable=False)
    reason = Column(Text, nullable=False)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_payroll_adjustment_tenant_contract", "tenant_id", "contract_id"),
        Index("ix_payroll_adjustment_payroll", "payroll_id"),
        Index("ix_payroll_adjustment_created_at", "created_at"),
    )