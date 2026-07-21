# app/domains/digital_twin/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, cast
import uuid

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, get_current_tenant
from app.domains.identity.models import User
from app.domains.academy.models import AcademyTenant
from app.domains.digital_twin.service import DigitalTwinService
from app.domains.digital_twin.schemas import *
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/digital-twin", tags=["Digital Twin & Legacy"])


# ============================================================
# 1. التوأم الرقمي (Digital Twin)
# ============================================================

@router.get("/config", response_model=TwinConfigResponse)
async def get_my_twin_config(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    twin = await service.get_or_create_twin(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id)
    )
    return twin


@router.put("/config", response_model=TwinConfigResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_twin_config(
    data: TwinConfigCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    twin = await service.update_twin_config(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return twin


@router.post("/interact/{owner_id}", response_model=TwinInteractionResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def interact_with_twin(
    owner_id: int,
    data: TwinInteractionCreate,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    log = await service.interact_with_twin(
        visitor_id=cast(int, current_user.id),
        twin_owner_id=owner_id,
        tenant_id=cast(int, tenant.id),
        interaction_data=data.model_dump(),
        idempotency_key=idempotency_key or f"twin-{uuid.uuid4().hex[:12]}"
    )
    return log


# ============================================================
# 2. خزائن الزمن والوصايا (Time Capsule & Legacy)
# ============================================================

@router.post("/time-capsule", response_model=TimeCapsuleResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, window_seconds=60)
async def create_time_capsule(
    data: TimeCapsuleCreate,
    beneficiaries: List[BeneficiaryCreate] = Query(..., description="قائمة المستفيدين"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    capsule = await service.setup_time_capsule(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(),
        beneficiaries=[b.model_dump() for b in beneficiaries]
    )
    return capsule


@router.post("/time-capsule/heartbeat")
@rate_limit(max_requests=10, window_seconds=60)
async def send_heartbeat(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    capsule = await service.send_heartbeat(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id)
    )
    return {"message": "Heartbeat sent", "last_heartbeat": capsule.last_heartbeat_at}  # type: ignore


@router.get("/time-capsule", response_model=TimeCapsuleResponse)
async def get_my_time_capsule(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    capsule = await service.get_time_capsule(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id)
    )
    if not capsule:
        raise HTTPException(status_code=404, detail="Time capsule not found")
    return capsule


# ============================================================
# 3. الوصية الرقمية (Digital Will)
# ============================================================

@router.post("/will", response_model=DigitalWillResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=3, window_seconds=60)
async def create_digital_will(
    data: DigitalWillCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    will = await service.create_digital_will(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return will


@router.get("/will", response_model=DigitalWillResponse)
async def get_my_digital_will(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    will = await service.get_digital_will(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id)
    )
    if not will:
        raise HTTPException(status_code=404, detail="Digital will not found")
    return will


# ============================================================
# 4. أوراكل الموت (Death Oracle)
# ============================================================

@router.post("/death-oracle/report-death")
@rate_limit(max_requests=5, window_seconds=60)
async def report_death(
    data: DeathReport,
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    oracle = await service.report_death(
        reporter_id=cast(int, current_user.id),
        deceased_id=data.reporter_user_id,
        tenant_id=cast(int, tenant.id),
        evidence_ipfs=data.evidence_ipfs_hash,
        request_ip=request.client.host if request.client else None,
        request_user_agent=request.headers.get("user-agent")
    )
    return {"status": oracle.status, "message": "Death reported, pending confirmation"}  # type: ignore


@router.post("/death-oracle/confirm-death/{deceased_id}")
@rate_limit(max_requests=5, window_seconds=60)
async def confirm_death(
    deceased_id: int,
    request: Request,
    confirmers: List[int] = Query(..., description="معرفات الشهود (3 على الأقل)"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    oracle = await service.confirm_death(
        deceased_id=deceased_id,
        tenant_id=cast(int, tenant.id),
        confirmers=confirmers,
        request_ip=request.client.host if request.client else None,
        request_user_agent=request.headers.get("user-agent")
    )
    return {"status": oracle.status, "release_tx": oracle.release_tx_hash}  # type: ignore


@router.get("/death-oracle/me", response_model=DeathOracleResponse)
async def get_my_death_oracle(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    oracle = await service.get_death_oracle(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id)
    )
    if not oracle:
        raise HTTPException(status_code=404, detail="Death oracle not found")
    return oracle


# ============================================================
# 5. محطات الحياة (Life Milestones)
# ============================================================

@router.post("/milestones", response_model=LifeMilestoneResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def add_life_milestone(
    data: LifeMilestoneCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    milestone = await service.add_life_milestone(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return milestone


@router.get("/milestones", response_model=List[LifeMilestoneResponse])
async def get_my_milestones(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    milestones = await service.list_life_milestones(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id)
    )
    return milestones


# ============================================================
# 6. الحجز قبل الولادة (Pre-Birth Identity)
# ============================================================

@router.post("/pre-birth", response_model=PreBirthRecordResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=3, window_seconds=60)
async def reserve_pre_birth_identity(
    data: PreBirthRecordCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    record = await service.reserve_pre_birth_identity(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return record