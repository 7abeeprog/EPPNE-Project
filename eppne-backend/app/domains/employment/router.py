# app/domains/employment/router.py (الإصدار النهائي المتكامل)
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, cast
from datetime import datetime

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, get_current_tenant
from app.domains.identity.models import User
from app.domains.employment.service import EmploymentService
from app.domains.employment.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/employment", tags=["Sovereign Employment & Talent"])


# ============================================================
# 1. الوظائف (Job Listings)
# ============================================================

@router.post("/jobs", response_model=JobListingResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_job(
    data: JobListingCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmploymentService(db)
    job = await service.create_job(
        employer_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return job


@router.get("/jobs/open", response_model=list[JobListingResponse])
async def get_open_jobs(
    employment_type: Optional[str] = Query(None, description="FULL_TIME, PART_TIME, CONTRACT"),
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmploymentService(db)
    jobs = await service.list_open_jobs(
        tenant_id=cast(int, tenant.id),
        employment_type=employment_type,
        skip=skip,
        limit=limit
    )
    return jobs


@router.get("/jobs/my", response_model=list[JobListingResponse])
async def get_my_jobs(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmploymentService(db)
    jobs = await service.get_my_jobs(
        employer_id=cast(int, current_user.id),
        skip=skip,
        limit=limit
    )
    return jobs


@router.put("/jobs/{job_id}", response_model=JobListingResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_job(
    job_id: int,
    data: JobListingCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmploymentService(db)
    job = await service.update_job(
        employer_id=cast(int, current_user.id),
        job_id=job_id,
        data=data.model_dump(exclude_unset=True)
    )
    return job


@router.delete("/jobs/{job_id}")
@rate_limit(max_requests=5, window_seconds=60)
async def close_job(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmploymentService(db)
    await service.close_job(
        employer_id=cast(int, current_user.id),
        job_id=job_id
    )
    return {"message": "تم إغلاق الوظيفة"}


# ============================================================
# 2. طلبات التوظيف (Applications)
# ============================================================

@router.post("/applications", response_model=JobApplicationResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, window_seconds=60)
async def apply_to_job(
    data: JobApplicationCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmploymentService(db)
    application = await service.apply_for_job(
        applicant_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
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
    service = EmploymentService(db)
    apps = await service.get_my_applications(
        applicant_id=cast(int, current_user.id),
        skip=skip,
        limit=limit
    )
    return apps


@router.get("/applications/job/{job_id}", response_model=list[JobApplicationResponse])
async def get_job_applications(
    job_id: int,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmploymentService(db)
    apps = await service.get_job_applications(
        employer_id=cast(int, current_user.id),
        job_id=job_id,
        skip=skip,
        limit=limit
    )
    return apps


@router.post("/applications/{application_id}/review", response_model=JobApplicationResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def review_application(
    application_id: int,
    approve: bool = Query(..., description="true للموافقة، false للرفض"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmploymentService(db)
    status_val = "APPROVED" if approve else "REJECTED"
    application = await service.review_application(
        employer_id=cast(int, current_user.id),
        application_id=application_id,
        status=status_val
    )
    return application


# ============================================================
# 3. عقود العمل (Contracts)
# ============================================================

@router.post("/contracts", response_model=EmploymentContractResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_contract(
    data: EmploymentContractCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmploymentService(db)
    contract = await service.create_contract(
        employer_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(),
        idempotency_key=idempotency_key or data.idempotency_key
    )
    return contract


@router.get("/contracts/me", response_model=EmploymentContractResponse)
async def get_my_active_contract(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmploymentService(db)
    contract = await service.get_my_active_contract(user_id=cast(int, current_user.id))
    if not contract:
        raise HTTPException(status_code=404, detail="لا يوجد عقد نشط")
    return contract


@router.post("/contracts/{contract_id}/sign")
@rate_limit(max_requests=5, window_seconds=60)
async def sign_contract(
    contract_id: int,
    signature: ContractSignRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmploymentService(db)
    contract = await service.repo.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="العقد غير موجود")
    is_employee = (cast(int, contract.employee_id) == current_user.id)
    if not is_employee and contract.employer_id != current_user.id:  # type: ignore
        raise HTTPException(status_code=403, detail="لا تملك صلاحية توقيع هذا العقد")
    updated = await service.sign_contract(
        user_id=cast(int, current_user.id),
        contract_id=contract_id,
        signature_tx_hash=signature.signature_tx_hash,
        is_employee=is_employee
    )
    return {"message": "تم توقيع العقد", "status": updated.status}


# ============================================================
# 4. الحضور والانصراف (Attendance)
# ============================================================

@router.post("/attendance/check-in")
@rate_limit(max_requests=2, window_seconds=60)
async def check_in(
    contract_id: int,
    location: AttendanceCheckIn,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmploymentService(db)
    record = await service.check_in(
        user_id=cast(int, current_user.id),
        contract_id=contract_id,
        latitude=location.latitude,
        longitude=location.longitude,
        device_fingerprint=location.device_fingerprint
    )
    return {"message": "تم تسجيل الحضور", "check_in": record.check_in}


@router.post("/attendance/check-out")
@rate_limit(max_requests=2, window_seconds=60)
async def check_out(
    contract_id: int,
    location: Optional[AttendanceCheckIn] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmploymentService(db)
    lat = location.latitude if location else None
    lng = location.longitude if location else None
    record = await service.check_out(
        user_id=cast(int, current_user.id),
        contract_id=contract_id,
        latitude=lat,
        longitude=lng
    )
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
    service = EmploymentService(db)
    records = await service.get_my_attendance(
        user_id=cast(int, current_user.id),
        contract_id=contract_id,
        skip=skip,
        limit=limit
    )
    return records


# ============================================================
# 5. الإجازات (Leave Requests)
# ============================================================

@router.post("/leaves/request", response_model=LeaveRequestResponse)
@rate_limit(max_requests=3, window_seconds=60)
async def request_leave(
    data: LeaveRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmploymentService(db)
    contract = await service.get_my_active_contract(user_id=cast(int, current_user.id))
    if not contract:
        raise HTTPException(status_code=404, detail="لا يوجد عقد نشط")
    leave = await service.request_leave(
        user_id=cast(int, current_user.id),
        contract_id=cast(int, contract.id),
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
    service = EmploymentService(db)
    leaves = await service.get_pending_leaves_for_employer(
        employer_id=cast(int, current_user.id)
    )
    return leaves


@router.post("/leaves/{leave_id}/approve")
@rate_limit(max_requests=10, window_seconds=60)
async def approve_leave(
    leave_id: int,
    approve: bool = Query(..., description="true للموافقة، false للرفض"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmploymentService(db)
    await service.approve_leave(
        employer_id=cast(int, current_user.id),
        leave_id=leave_id,
        approve=approve
    )
    return {"message": "تم تحديث طلب الإجازة"}


# ============================================================
# 6. الرواتب (Payroll)
# ============================================================

@router.post("/payroll/generate", response_model=PayrollRecordResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def generate_payroll(
    contract_id: int,
    month: str = Query(..., regex=r"^\d{4}-\d{2}$", description="شهر بصيغة YYYY-MM"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmploymentService(db)
    payroll = await service.generate_payroll(
        contract_id=contract_id,
        month=month,
        employer_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        idempotency_key=idempotency_key
    )
    return payroll


@router.post("/payroll/{payroll_id}/approve", response_model=PayrollRecordResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def approve_payroll(
    payroll_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmploymentService(db)
    payroll = await service.approve_payroll(
        payroll_id=payroll_id,
        employer_id=cast(int, current_user.id)
    )
    return payroll


@router.post("/payroll/{payroll_id}/pay", response_model=PayrollRecordResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def pay_payroll(
    payroll_id: int,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmploymentService(db)
    payroll = await service.pay_payroll(
        payroll_id=payroll_id,
        employer_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
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
    service = EmploymentService(db)
    payrolls = await service.get_my_payrolls(
        user_id=cast(int, current_user.id),
        skip=skip,
        limit=limit
    )
    return payrolls