# app/domains/employment/schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.employment.models import EmploymentStatus, LeaveType, PayrollStatus
from app.domains.employment.models import (
    JobListing, JobApplication, EmploymentContract, AttendanceRecord,
    LeaveRequest, PayrollRecord, EmploymentStatus, AttendanceStatus,
    LeaveType, PayrollStatus
)

# ========== Job Listings ==========
class JobListingCreate(BaseModel):
    title: str
    description: Optional[str] = None
    required_skills: List[str] = []
    required_certificate_ids: List[int] = []
    required_rank: Optional[str] = None
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    currency: str = "MR_USDT"
    location: Optional[str] = None
    employment_type: str = "FULL_TIME"

class JobListingResponse(JobListingCreate):
    id: int
    employer_id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Job Applications ==========
class JobApplicationCreate(BaseModel):
    job_id: int
    cover_letter: Optional[str] = None
    resume_url: Optional[str] = None

class JobApplicationResponse(BaseModel):
    id: int
    job_id: int
    applicant_id: int
    cover_letter: Optional[str]
    resume_url: Optional[str]
    ai_match_score: Optional[float]
    status: str
    reviewed_by_id: Optional[int]
    reviewed_at: Optional[datetime]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Employment Contracts ==========
class EmploymentContractCreate(BaseModel):
    application_id: int
    job_title: str
    base_salary: Decimal
    allowances: Dict[str, Decimal] = {}
    currency: str = "MR_USDT"
    start_date: datetime
    end_date: Optional[datetime] = None
    probation_days: int = 90
    annual_leave_days: int = 21
    idempotency_key: Optional[str] = None  # 🔥 دعم Idempotency

class EmploymentContractResponse(EmploymentContractCreate):
    id: int
    employee_id: int
    employer_id: int
    status: EmploymentStatus
    smart_contract_address: Optional[str]
    signature_tx_hash: Optional[str]
    employer_signature_tx: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ContractSignRequest(BaseModel):
    contract_id: int
    signature_tx_hash: str

# ========== Attendance ==========
class AttendanceCheckIn(BaseModel):
    latitude: float
    longitude: float
    device_fingerprint: Optional[str] = None

class AttendanceRecordResponse(BaseModel):
    id: int
    contract_id: int
    date: datetime
    check_in: Optional[datetime]
    check_out: Optional[datetime]
    hours_worked: float
    overtime_hours: float
    status: str
    model_config = ConfigDict(from_attributes=True)

# ========== Leave Requests ==========
class LeaveRequestCreate(BaseModel):
    leave_type: LeaveType
    start_date: datetime
    end_date: datetime
    reason: Optional[str] = None

class LeaveRequestResponse(LeaveRequestCreate):
    id: int
    contract_id: int
    status: str
    approved_by_id: Optional[int]
    approved_at: Optional[datetime]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Payroll ==========
class PayrollRecordResponse(BaseModel):
    id: int
    contract_id: int
    month: str
    base_salary: Decimal
    bonuses: Decimal
    overtime_pay: Decimal
    deductions: Dict[str, Decimal]
    net_salary: Decimal
    status: PayrollStatus
    payment_tx_hash: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)