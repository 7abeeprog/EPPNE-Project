# app/domains/digital_twin/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, get_current_tenant
from app.domains.identity.models import User
from app.domains.academy.models import AcademyTenant
from app.domains.digital_twin.service import DigitalTwinService
from app.domains.digital_twin.repository import DigitalTwinRepository
from app.domains.digital_twin.schemas import *
from app.core.rate_limiter import rate_limit

import uuid

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
    twin = await service.get_or_create_twin(current_user.id, tenant.id)
    return twin


@router.put("/config", response_model=TwinConfigResponse)
@rate_limit(max_requests=10, window=60)
async def update_twin_config(
    data: TwinConfigCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    twin = await service.repo.update_twin_config(current_user.id, tenant.id, **data.model_dump())
    return twin


@router.post("/interact/{owner_id}", response_model=TwinInteractionResponse)
@rate_limit(max_requests=20, window=60)
async def interact_with_twin(
    owner_id: int,
    data: TwinInteractionCreate,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    تفاعل المستخدم مع التوأم الرقمي مع دعم Idempotency.
    """
    service = DigitalTwinService(db)
    log = await service.interact_with_twin(
        visitor_id=current_user.id,
        twin_owner_id=owner_id,
        tenant_id=tenant.id,
        interaction_data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return log


# ============================================================
# 2. خزائن الزمن والوصايا (Time Capsule & Legacy)
# ============================================================

@router.post("/time-capsule", response_model=TimeCapsuleResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, window=60)
async def create_time_capsule(
    data: TimeCapsuleCreate,
    beneficiaries: list[BeneficiaryCreate],
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    capsule = await service.setup_time_capsule(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump(),
        beneficiaries=[b.model_dump() for b in beneficiaries]
    )
    return capsule


@router.post("/time-capsule/heartbeat")
@rate_limit(max_requests=10, window=60)
async def send_heartbeat(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    capsule = await service.send_heartbeat(current_user.id, tenant.id)
    return {"message": "Heartbeat sent", "last_heartbeat": capsule.last_heartbeat_at}


@router.get("/time-capsule", response_model=TimeCapsuleResponse)
async def get_my_time_capsule(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = DigitalTwinRepository(db)
    capsule = await repo.get_time_capsule(current_user.id, tenant.id)
    if not capsule:
        raise HTTPException(status_code=404, detail="Time capsule not found")
    return capsule


# ============================================================
# 3. الوصية الرقمية (Digital Will)
# ============================================================

@router.post("/will", response_model=DigitalWillResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=3, window=60)
async def create_digital_will(
    data: DigitalWillCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = DigitalTwinRepository(db)
    existing = await repo.get_digital_will(current_user.id, tenant.id)
    if existing:
        raise HTTPException(status_code=400, detail="Digital will already exists")
    nft_id = f"WILL-{current_user.id}-{uuid.uuid4().hex[:8].upper()}"
    will = await repo.create_digital_will(
        user_id=current_user.id,
        tenant_id=tenant.id,
        will_nft_id=nft_id,
        **data.model_dump()
    )
    return will


# ============================================================
# 4. أوراكل الموت (Death Oracle)
# ============================================================

@router.post("/death-oracle/report-death")
@rate_limit(max_requests=5, window=60)
async def report_death(
    data: DeathReport,
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    oracle = await service.report_death(
        reporter_id=current_user.id,
        deceased_id=data.reporter_user_id,
        tenant_id=tenant.id,
        evidence_ipfs=data.evidence_ipfs_hash,
        request_ip=request.client.host,
        request_user_agent=request.headers.get("user-agent")
    )
    return {"status": oracle.status, "message": "Death reported, pending confirmation"}


@router.post("/death-oracle/confirm-death/{deceased_id}")
@rate_limit(max_requests=5, window=60)
async def confirm_death(
    deceased_id: int,
    confirmers: list[int],
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = DigitalTwinService(db)
    oracle = await service.confirm_death(
        deceased_id=deceased_id,
        tenant_id=tenant.id,
        confirmers=confirmers,
        request_ip=request.client.host,
        request_user_agent=request.headers.get("user-agent")
    )
    return {"status": oracle.status, "release_tx": oracle.release_tx_hash}


# ============================================================
# 5. محطات الحياة (Life Milestones)
# ============================================================

@router.post("/milestones", response_model=LifeMilestoneResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window=60)
async def add_life_milestone(
    data: LifeMilestoneCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = DigitalTwinRepository(db)
    nft_id = f"MLS-{current_user.id}-{data.milestone_type.value}-{uuid.uuid4().hex[:8].upper()}"
    milestone = await repo.create_life_milestone(
        user_id=current_user.id,
        tenant_id=tenant.id,
        milestone_nft_id=nft_id,
        **data.model_dump()
    )
    return milestone


@router.get("/milestones", response_model=list[LifeMilestoneResponse])
async def get_my_milestones(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = DigitalTwinRepository(db)
    milestones = await repo.list_life_milestones(current_user.id, tenant.id)
    return milestones


# ============================================================
# 6. الحجز قبل الولادة (Pre-Birth Identity)
# ============================================================

@router.post("/pre-birth", response_model=PreBirthRecordResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=3, window=60)
async def reserve_pre_birth_identity(
    data: PreBirthRecordCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = DigitalTwinRepository(db)
    existing = await repo.get_pre_birth_record(data.reserved_sovereign_id, tenant.id)
    if existing:
        raise HTTPException(status_code=400, detail="Sovereign ID already reserved")
    record = await repo.create_pre_birth_record(
        tenant_id=tenant.id,
        parent_1_id=current_user.id,
        **data.model_dump()
    )
    return record