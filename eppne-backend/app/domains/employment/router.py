# app/domains/employment/router.py (الإصدار النهائي المتكامل)
"""
مسارات (Endpoints) قطاع التوظيف والموارد البشرية
تدعم: الوظائف، طلبات التوظيف، العقود، الحضور، الإجازات، الرواتب
مع إضافة: Idempotency-Key، Rate Limiting، SaaS Tenant
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, get_current_tenant
from app.domains.identity.models import User
from app.domains.employment.service import EmploymentService
from app.domains.employment.repository import EmploymentRepository
from app.domains.employment.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/employment", tags=["Sovereign Employment & Talent"])


# ========== 1. الوظائف (Job Listings) ==========

@router.post("/jobs", response_model=JobListingResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window=60)
async def create_job(
    data: JobListingCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    إنشاء وظيفة جديدة (لأصحاب العمل فقط).
    """
    service = EmploymentService(db)
    job = await service.create_job(
        employer_id=current_user.id,
        tenant_id=tenant.id,
        data={**data.model_dump(), "tenant_id": tenant.id}
    )
    return job


@router.get("/jobs/open", response_model=list[JobListingResponse])
async def get_open_jobs(
    employment_type: Optional[str] = Query(None, description="FULL_TIME, PART_TIME, CONTRACT"),
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب الوظائف النشطة المتاحة للتقديم.
    """
    repo = EmploymentRepository(db)
    jobs = await repo.list_active_jobs(tenant.id, skip, limit, employment_type)
    return jobs


@router.get("/jobs/my", response_model=list[JobListingResponse])
async def get_my_jobs(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب الوظائف التي نشرها المستخدم (لأصحاب العمل).
    """
    repo = EmploymentRepository(db)
    jobs = await repo.list_employer_jobs(current_user.id, skip, limit)
    return jobs


@router.put("/jobs/{job_id}", response_model=JobListingResponse)
@rate_limit(max_requests=10, window=60)
async def update_job(
    job_id: int,
    data: JobListingCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    تحديث وظيفة موجودة (لصاحب العمل فقط).
    """
    service = EmploymentService(db)
    job = await service.update_job(current_user.id, job_id, data.model_dump(exclude_unset=True))
    return job


@router.delete("/jobs/{job_id}")
@rate_limit(max_requests=5, window=60)
async def close_job(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    إغلاق وظيفة (وقف استقبال الطلبات).
    """
    service = EmploymentService(db)
    await service.close_job(current_user.id, job_id)
    return {"message": "تم إغلاق الوظيفة"}


# ========== 2. طلبات التوظيف (Applications) ==========

@router.post("/applications", response_model=JobApplicationResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, window=60)
async def apply_to_job(
    data: JobApplicationCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    تقديم طلب وظيفة (للمستخدمين العاديين).
    """
    service = EmploymentService(db)
    application = await service.apply_for_job(
        applicant_id=current_user.id,
        tenant_id=tenant.id,
        job_id=data.job_id,
        cover_letter=data.cover_letter,
        resume_url=data.resume_url
    )
    return application


@router.get("/applications/my", response_model=list[JobApplicationResponse])
async def get_my_applications(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب طلبات التوظيف الخاصة بي.
    """
    repo = EmploymentRepository(db)
    apps = await repo.list_applications_for_applicant(current_user.id, skip, limit)
    return apps


@router.get("/applications/job/{job_id}", response_model=list[JobApplicationResponse])
async def get_job_applications(
    job_id: int,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب طلبات التوظيف لوظيفة معينة (لصاحب العمل فقط).
    """
    repo = EmploymentRepository(db)
    job = await repo.get_job_listing_by_employer(job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=403, detail="ليس لديك صلاحية لعرض هذه الطلبات")
    apps = await repo.list_applications_for_job(job_id, skip, limit)
    return apps


@router.post("/applications/{application_id}/review", response_model=JobApplicationResponse)
@rate_limit(max_requests=10, window=60)
async def review_application(
    application_id: int,
    approve: bool = Query(..., description="true للموافقة، false للرفض"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    قبول أو رفض طلب وظيفة (لصاحب العمل).
    """
    service = EmploymentService(db)
    status_val = "APPROVED" if approve else "REJECTED"
    application = await service.review_application(current_user.id, application_id, status_val)
    return application


# ========== 3. عقود العمل (Contracts) ==========

@router.post("/contracts", response_model=EmploymentContractResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window=60)
async def create_contract(
    data: EmploymentContractCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    إنشاء عقد عمل بعد قبول طلب التوظيف (لصاحب العمل) مع دعم Idempotency.
    """
    service = EmploymentService(db)
    contract = await service.create_contract(
        employer_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return contract


@router.get("/contracts/me", response_model=EmploymentContractResponse)
async def get_my_active_contract(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب العقد النشط للموظف الحالي.
    """
    service = EmploymentService(db)
    contract = await service.get_my_active_contract(current_user.id)
    if not contract:
        raise HTTPException(status_code=404, detail="لا يوجد عقد نشط")
    return contract


@router.post("/contracts/{contract_id}/sign")
@rate_limit(max_requests=5, window=60)
async def sign_contract(
    contract_id: int,
    signature: ContractSignRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    توقيع العقد (للموظف أو صاحب العمل).
    """
    service = EmploymentService(db)
    # تحديد ما إذا كان المستخدم هو الموظف أم صاحب العمل
    contract = await service.repo.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="العقد غير موجود")
    is_employee = (contract.employee_id == current_user.id)
    if not is_employee and contract.employer_id != current_user.id:
        raise HTTPException(status_code=403, detail="لا تملك صلاحية توقيع هذا العقد")
    updated = await service.sign_contract(current_user.id, contract_id, signature.signature_tx_hash, is_employee)
    return {"message": "تم توقيع العقد", "status": updated.status}


# ========== 4. الحضور والانصراف ==========

@router.post("/attendance/check-in")
@rate_limit(max_requests=2, window=60)
async def check_in(
    contract_id: int,
    location: AttendanceCheckIn,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    تسجيل حضور الموظف (مع التحقق من الموقع الجغرافي).
    """
    service = EmploymentService(db)
    record = await service.check_in(
        user_id=current_user.id,
        contract_id=contract_id,
        latitude=location.latitude,
        longitude=location.longitude,
        device_fingerprint=location.device_fingerprint
    )
    return {"message": "تم تسجيل الحضور", "check_in": record.check_in}


@router.post("/attendance/check-out")
@rate_limit(max_requests=2, window=60)
async def check_out(
    contract_id: int,
    location: Optional[AttendanceCheckIn] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    تسجيل انصراف الموظف وحساب ساعات العمل.
    """
    service = EmploymentService(db)
    lat = location.latitude if location else None
    lng = location.longitude if location else None
    record = await service.check_out(current_user.id, contract_id, lat, lng)
    return {
        "message": "تم تسجيل الانصراف",
        "check_out": record.check_out,
        "hours_worked": record.hours_worked,
        "overtime_hours": record.overtime_hours
    }


@router.get("/attendance/my", response_model=list[AttendanceRecordResponse])
async def get_my_attendance(
    contract_id: int,
    skip: int = 0,
    limit: int = 30,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب سجل الحضور الخاص بي لعقد معين.
    """
    repo = EmploymentRepository(db)
    # التحقق من أن العقد يخص المستخدم
    contract = await repo.get_contract(contract_id)
    if not contract or contract.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="لا تملك صلاحية الاطلاع على هذا السجل")
    year = datetime.utcnow().year
    month = datetime.utcnow().month
    records = await repo.get_attendance_for_month(contract_id, year, month)
    # التبسيط: نعيد آخر 30 سجلاً (يمكن تحسينه لاحقاً)
    return records[-limit:]


# ========== 5. الإجازات ==========

@router.post("/leaves/request", response_model=LeaveRequestResponse)
@rate_limit(max_requests=3, window=60)
async def request_leave(
    data: LeaveRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    تقديم طلب إجازة.
    """
    service = EmploymentService(db)
    contract = await service.get_my_active_contract(current_user.id)
    if not contract:
        raise HTTPException(status_code=404, detail="لا يوجد عقد نشط")
    leave = await service.request_leave(
        user_id=current_user.id,
        contract_id=contract.id,
        leave_type=data.leave_type,
        start_date=data.start_date,
        end_date=data.end_date,
        reason=data.reason
    )
    return leave


@router.get("/leaves/pending", response_model=list[LeaveRequestResponse])
async def get_pending_leaves_for_employer(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب طلبات الإجازات المعلقة لجميع عقود صاحب العمل.
    """
    repo = EmploymentRepository(db)
    leaves = await repo.list_pending_leave_requests_for_employer(current_user.id)
    return leaves


@router.post("/leaves/{leave_id}/approve")
@rate_limit(max_requests=10, window=60)
async def approve_leave(
    leave_id: int,
    approve: bool = Query(..., description="true للموافقة، false للرفض"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    الموافقة أو رفض طلب إجازة (لصاحب العمل).
    """
    service = EmploymentService(db)
    await service.approve_leave(current_user.id, leave_id, approve)
    return {"message": "تم تحديث طلب الإجازة"}


# ========== 6. الرواتب ==========

@router.post("/payroll/generate", response_model=PayrollRecordResponse)
@rate_limit(max_requests=5, window=60)
async def generate_payroll(
    contract_id: int,
    month: str = Query(..., regex=r"^\d{4}-\d{2}$", description="شهر بصيغة YYYY-MM"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    إنشاء كشف راتب لشهر محدد (لصاحب العمل) مع دعم Idempotency.
    """
    service = EmploymentService(db)
    payroll = await service.generate_payroll(
        contract_id=contract_id,
        month=month,
        employer_id=current_user.id,
        tenant_id=tenant.id,
        idempotency_key=idempotency_key
    )
    return payroll


@router.post("/payroll/{payroll_id}/approve", response_model=PayrollRecordResponse)
@rate_limit(max_requests=5, window=60)
async def approve_payroll(
    payroll_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    اعتماد كشف الراتب قبل الدفع.
    """
    service = EmploymentService(db)
    payroll = await service.approve_payroll(payroll_id, current_user.id)
    return payroll


@router.post("/payroll/{payroll_id}/pay", response_model=PayrollRecordResponse)
@rate_limit(max_requests=5, window=60)
async def pay_payroll(
    payroll_id: int,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    دفع الراتب (تحويل من محفظة صاحب العمل إلى محفظة الموظف) مع دعم Idempotency.
    """
    service = EmploymentService(db)
    payroll = await service.pay_payroll(
        payroll_id=payroll_id,
        employer_id=current_user.id,
        tenant_id=tenant.id,
        idempotency_key=idempotency_key
    )
    return payroll


@router.get("/payroll/my", response_model=list[PayrollRecordResponse])
async def get_my_payrolls(
    skip: int = 0,
    limit: int = 12,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب كشوف رواتب الموظف الحالي.
    """
    repo = EmploymentRepository(db)
    contract = await repo.get_contract_by_employee(current_user.id, active_only=False)
    if not contract:
        raise HTTPException(status_code=404, detail="لا يوجد عقد عمل مسجل")
    payrolls = await repo.list_payrolls_for_contract(contract.id, skip, limit)
    return payrolls