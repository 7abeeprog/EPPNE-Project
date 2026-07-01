# app/domains/health/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, get_current_tenant
from app.domains.identity.models import User
from app.domains.academy.models import AcademyTenant
from app.domains.health.service import HealthService
from app.domains.health.repository import HealthRepository
from app.domains.health.schemas import *
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/health", tags=["Sovereign Health & Emergency"])

# ============================================================
# 1. الملف الطبي الشخصي (Medical Profile)
# ============================================================

@router.get("/profile/me", response_model=MedicalProfileResponse)
async def get_my_medical_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    profile = await service.get_or_create_profile(current_user.id)
    return profile


@router.put("/profile/me", response_model=MedicalProfileResponse)
async def update_my_medical_profile(
    data: MedicalProfileCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    profile = await service.repo.update_medical_profile(current_user.id, **data.model_dump())
    return profile


# ============================================================
# 2. البيانات الحيوية والذكاء الاصطناعي (Biometric & AI)
# ============================================================

@router.post("/biometric/log", response_model=dict)
async def log_biometric_data(
    data: BiometricLogCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    result = await service.process_biometric_data(current_user.id, data.model_dump())
    return result


@router.get("/biometric/history", response_model=list[BiometricLogResponse])
async def get_biometric_history(
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    profile = await service.get_or_create_profile(current_user.id)
    logs = await service.repo.list_biometric_logs(profile.id, limit)
    return logs


@router.get("/ai/prognosis", response_model=list[AIHealthPrognosisResponse])
async def get_ai_prognosis(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    profile = await service.get_or_create_profile(current_user.id)
    prognoses = await service.repo.list_prognoses(profile.id)
    return prognoses


# ============================================================
# 3. المواعيد الطبية (Appointments) – مع Rate Limiting و Idempotency
# ============================================================

@router.post("/appointments", response_model=MedicalAppointmentResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window=60)
async def book_appointment(
    data: MedicalAppointmentCreate,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    حجز موعد طبي مع دعم Idempotency ومنع التكرار.
    """
    service = HealthService(db)
    appointment = await service.book_appointment(
        patient_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return appointment


@router.get("/appointments", response_model=list[MedicalAppointmentResponse])
async def get_my_appointments(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    appointments = await service.repo.list_appointments(current_user.id, status_filter)
    return appointments


@router.patch("/appointments/{appointment_id}/cancel", response_model=MedicalAppointmentResponse)
async def cancel_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    appointment = await service.repo.get_appointment(appointment_id)
    if not appointment or appointment.patient_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Appointment not found")
    updated = await service.repo.update_appointment_status(appointment_id, AppointmentStatus.CANCELLED.value)
    return updated


# ============================================================
# 4. الوصفات الطبية (Prescriptions)
# ============================================================

@router.post("/prescriptions", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_prescription(
    data: PrescriptionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # فقط الأطباء (سنضيف صلاحية لاحقاً)
    service = HealthService(db)
    prescription = await service.repo.create_prescription(**data.model_dump())
    return prescription


# ============================================================
# 5. الطوارئ (Emergency) – مع Rate Limiting و Idempotency
# ============================================================

@router.post("/emergency", response_model=EmergencyDispatchResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, window=60)
async def call_emergency(
    data: EmergencyDispatchCreate,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    استدعاء الطوارئ مع دعم Idempotency ومنع التكرار.
    """
    service = HealthService(db)
    dispatch = await service.trigger_emergency(
        caller_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return dispatch


@router.get("/emergency/{dispatch_id}", response_model=EmergencyDispatchResponse)
async def get_emergency_status(
    dispatch_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = HealthService(db)
    dispatch = await service.repo.get_dispatch(dispatch_id)
    if not dispatch or (dispatch.patient_id and dispatch.patient_id != current_user.id):
        raise HTTPException(status_code=404, detail="Emergency not found")
    return dispatch


# ============================================================
# 6. المنشآت الصحية (Facilities) – للإدارة
# ============================================================

@router.post("/facilities", response_model=HealthFacilityResponse, status_code=status.HTTP_201_CREATED)
async def create_facility(
    data: HealthFacilityCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    repo = HealthRepository(db)
    facility = await repo.create_facility(**data.model_dump())
    return facility


@router.get("/facilities", response_model=list[HealthFacilityResponse])
async def list_facilities(
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    repo = HealthRepository(db)
    facilities = await repo.list_facilities(category, skip, limit)
    return facilities