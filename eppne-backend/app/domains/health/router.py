# app/domains/health/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, cast

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, get_current_tenant
from app.domains.identity.models import User
from app.domains.academy.models import AcademyTenant
from app.domains.health.service import HealthService
from app.domains.health.schemas import *
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/health", tags=["Sovereign Health & Emergency"])


# ============================================================
# 1. الملف الطبي الشخصي (Medical Profile)
# ============================================================

@router.get("/profile/me", response_model=MedicalProfileResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_my_medical_profile(
    current_user: User = Depends(get_current_active_user),
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    profile = await service.get_or_create_profile(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id)
    )
    return profile


@router.put("/profile/me", response_model=MedicalProfileResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_my_medical_profile(
    data: MedicalProfileCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    profile = await service.update_profile(
        user_id=cast(int, current_user.id),
        data=data.model_dump()
    )
    return profile


# ============================================================
# 2. البيانات الحيوية والذكاء الاصطناعي
# ============================================================

@router.post("/biometric/log", response_model=dict)
@rate_limit(max_requests=20, window_seconds=60)
async def log_biometric_data(
    data: BiometricLogCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    result = await service.process_biometric_data(
        user_id=cast(int, current_user.id),
        data=data.model_dump()
    )
    return result


@router.get("/biometric/history", response_model=List[BiometricLogResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_biometric_history(
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    logs = await service.get_biometric_history(
        user_id=cast(int, current_user.id),
        limit=limit
    )
    return logs


@router.get("/ai/prognosis", response_model=List[AIHealthPrognosisResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def get_ai_prognosis(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    prognoses = await service.get_ai_prognosis(user_id=cast(int, current_user.id))
    return prognoses


# ============================================================
# 3. المواعيد الطبية (Appointments)
# ============================================================

@router.post("/appointments", response_model=MedicalAppointmentResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def book_appointment(
    data: MedicalAppointmentCreate,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    appointment = await service.book_appointment(
        patient_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return appointment


@router.get("/appointments", response_model=List[MedicalAppointmentResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_my_appointments(
    status_filter: Optional[str] = Query(None, description="حالة الموعد"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    appointments = await service.get_my_appointments(
        user_id=cast(int, current_user.id),
        status_filter=status_filter
    )
    return appointments


@router.patch("/appointments/{appointment_id}/cancel", response_model=MedicalAppointmentResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def cancel_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    appointment = await service.cancel_appointment(
        user_id=cast(int, current_user.id),
        appointment_id=appointment_id
    )
    return appointment


# ============================================================
# 4. الوصفات الطبية (Prescriptions)
# ============================================================

@router.post("/prescriptions", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_prescription(
    data: PrescriptionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    prescription = await service.create_prescription(data=data.model_dump())
    return prescription


# ============================================================
# 5. الطوارئ (Emergency)
# ============================================================

@router.post("/emergency", response_model=EmergencyDispatchResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, window_seconds=60)
async def call_emergency(
    data: EmergencyDispatchCreate,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    dispatch = await service.trigger_emergency(
        caller_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return dispatch


@router.get("/emergency/{dispatch_id}", response_model=EmergencyDispatchResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def get_emergency_status(
    dispatch_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    dispatch = await service.get_emergency_status(
        dispatch_id=dispatch_id,
        user_id=cast(int, current_user.id)
    )
    if not dispatch:
        raise HTTPException(status_code=404, detail="بلاغ الطوارئ غير موجود")
    return dispatch


# ============================================================
# 6. المنشآت الصحية (Facilities) – للإدارة
# ============================================================

@router.post("/facilities", response_model=HealthFacilityResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_facility(
    data: HealthFacilityCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    facility_data = data.model_dump()
    facility_data["tenant_id"] = tenant.id
    facility = await service.create_facility(
        user_id=cast(int, current_user.id),
        data=facility_data
    )
    return facility


@router.get("/facilities", response_model=List[HealthFacilityResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_facilities(
    category: Optional[str] = Query(None, description="تصنيف المنشأة"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    facilities = await service.list_facilities(
        tenant_id=cast(int, tenant.id),
        category=category,
        skip=skip,
        limit=limit
    )
    return facilities


@router.get("/facilities/{facility_id}", response_model=HealthFacilityResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_facility(
    facility_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    facility = await service.get_facility(
        facility_id=facility_id,
        tenant_id=cast(int, tenant.id)
    )
    if not facility:
        raise HTTPException(status_code=404, detail="المنشأة غير موجودة")
    return facility