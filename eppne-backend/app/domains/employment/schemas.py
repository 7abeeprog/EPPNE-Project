# app/domains/employment/schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.employment.models import EmploymentStatus, LeaveType, PayrollStatus, AttendanceStatus


# ============================================================
# الوظائف (Job Listings)
# ============================================================

class JobListingCreate(BaseModel):
    title: str = Field(description="عنوان الوظيفة")
    description: Optional[str] = Field(default=None, description="وصف الوظيفة")
    required_skills: List[str] = Field(default_factory=list, description="المهارات المطلوبة")
    required_certificate_ids: List[int] = Field(default_factory=list, description="معرفات الشهادات المطلوبة")
    required_rank: Optional[str] = Field(default=None, description="الرتبة السيادية المطلوبة")
    salary_min: Optional[Decimal] = Field(default=None, description="الحد الأدنى للراتب")
    salary_max: Optional[Decimal] = Field(default=None, description="الحد الأقصى للراتب")
    currency: str = Field(default="MR_USDT", description="العملة")
    location: Optional[str] = Field(default=None, description="الموقع")
    employment_type: str = Field(default="FULL_TIME", description="نوع التوظيف")


class JobListingResponse(JobListingCreate):
    id: int
    employer_id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# طلبات التوظيف (Job Applications)
# ============================================================

class JobApplicationCreate(BaseModel):
    job_id: int = Field(description="معرف الوظيفة")
    cover_letter: Optional[str] = Field(default=None, description="رسالة التعريف")
    resume_url: Optional[str] = Field(default=None, description="رابط السيرة الذاتية")


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


# ============================================================
# عقود العمل (Employment Contracts)
# ============================================================

class EmploymentContractCreate(BaseModel):
    application_id: int = Field(description="معرف طلب التوظيف")
    job_title: str = Field(description="المسمى الوظيفي")
    base_salary: Decimal = Field(description="الراتب الأساسي")
    allowances: Optional[Dict[str, Any]] = Field(default_factory=dict, description="البدلات الإضافية")
    currency: str = Field(default="MR_USDT", description="العملة")
    start_date: datetime = Field(description="تاريخ البدء")
    end_date: Optional[datetime] = Field(default=None, description="تاريخ الانتهاء (إن وجد)")
    probation_days: int = Field(default=90, description="مدة التجربة بالأيام")
    annual_leave_days: int = Field(default=21, description="أيام الإجازة السنوية")
    idempotency_key: Optional[str] = Field(default=None, description="مفتاح عدم التكرار")


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
    signature_tx_hash: str = Field(description="هاش التوقيع")


# ============================================================
# الحضور والانصراف (Attendance)
# ============================================================

class AttendanceCheckIn(BaseModel):
    latitude: float = Field(description="خط العرض")
    longitude: float = Field(description="خط الطول")
    device_fingerprint: Optional[str] = Field(default=None, description="بصمة الجهاز")


class AttendanceRecordResponse(BaseModel):
    id: int
    contract_id: int
    date: datetime
    check_in: Optional[datetime]
    check_out: Optional[datetime]
    hours_worked: float
    overtime_hours: float
    status: AttendanceStatus
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# الإجازات (Leave Requests)
# ============================================================

class LeaveRequestCreate(BaseModel):
    leave_type: LeaveType = Field(description="نوع الإجازة")
    start_date: datetime = Field(description="تاريخ البدء")
    end_date: datetime = Field(description="تاريخ الانتهاء")
    reason: Optional[str] = Field(default=None, description="سبب الإجازة")


class LeaveRequestResponse(LeaveRequestCreate):
    id: int
    contract_id: int
    status: str
    approved_by_id: Optional[int]
    approved_at: Optional[datetime]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# الرواتب (Payroll)
# ============================================================

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