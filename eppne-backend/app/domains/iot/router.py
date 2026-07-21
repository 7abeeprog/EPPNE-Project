# app/domains/iot/router.py (الإصدار النهائي المتكامل)
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, cast
import uuid

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser
from app.domains.identity.models import User
from app.domains.iot.service import IoTService
from app.domains.iot.schemas import *
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/iot", tags=["IoT & Carbon Sovereignty"])


# ============================================================
# 1. الأصول الذكية (Smart Assets)
# ============================================================

@router.post("/assets", response_model=SmartAssetResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_asset(
    data: SmartAssetCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    asset = await service.create_asset(
        owner_id=cast(int, current_user.id),
        data=data.model_dump()
    )
    return asset


@router.get("/assets", response_model=List[SmartAssetResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_my_assets(
    current_user: User = Depends(get_current_active_user),
    asset_class: Optional[AssetClass] = Query(None, description="فئة الأصل"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    assets = await service.list_assets(
        user_id=cast(int, current_user.id),
        asset_class=asset_class,
        skip=skip,
        limit=limit
    )
    return assets


@router.get("/assets/{asset_id}", response_model=SmartAssetResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_asset(
    asset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    asset = await service.get_asset(
        asset_id=asset_id,
        user_id=cast(int, current_user.id)
    )
    return asset


@router.patch("/assets/{asset_id}", response_model=SmartAssetResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_asset(
    asset_id: int,
    data: SmartAssetUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    updated = await service.update_asset(
        asset_id=asset_id,
        user_id=cast(int, current_user.id),
        data=data.model_dump(exclude_unset=True)
    )
    return updated


# ============================================================
# 2. المحطات المركزية (Utility Grids) – للمشرف فقط
# ============================================================

@router.post("/grids", response_model=UtilityGridResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, window_seconds=60)
async def create_grid(
    data: UtilityGridCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    grid = await service.create_grid(data=data.model_dump())
    return grid


@router.get("/grids", response_model=List[UtilityGridResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_grids(
    grid_type: Optional[GridStationType] = Query(None, description="نوع المحطة"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    grids = await service.list_grids(
        grid_type=grid_type,
        skip=skip,
        limit=limit
    )
    return grids


# ============================================================
# 3. القراءات (Readings)
# ============================================================

@router.post("/readings", response_model=dict, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=50, window_seconds=60)
async def ingest_reading(
    request: Request,
    data: UtilityReadingCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    idem_key = idempotency_key or f"READ-{uuid.uuid4().hex[:12]}"
    result = await service.record_reading(
        data=data.model_dump(),
        idempotency_key=idem_key,
        ip=client_ip,
        ua=user_agent
    )
    return result


@router.get("/readings", response_model=List[UtilityReadingResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_readings(
    asset_id: Optional[int] = Query(None, description="معرف الأصل"),
    grid_id: Optional[int] = Query(None, description="معرف المحطة"),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    readings = await service.get_readings(
        user_id=cast(int, current_user.id),
        asset_id=asset_id,
        grid_id=grid_id,
        limit=limit
    )
    return readings


# ============================================================
# 4. تسييل الكربون (Carbon Settlement)
# ============================================================

@router.post("/carbon/settle")
@rate_limit(max_requests=5, window_seconds=300)
async def settle_carbon(
    request: Request,
    payload: CarbonSettlementRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    idem_key = idempotency_key or f"SETTLE-{uuid.uuid4().hex[:12]}"
    result = await service.settle_carbon_credits(
        owner_id=cast(int, current_user.id),
        asset_ids=payload.asset_ids,
        idempotency_key=idem_key,
        ip=client_ip,
        ua=user_agent
    )
    return result


# ============================================================
# 5. الصيانة (Maintenance)
# ============================================================

@router.post("/maintenance", response_model=MaintenanceLogResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def report_maintenance(
    data: MaintenanceLogCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    log = await service.create_maintenance(data=data.model_dump())
    return log


@router.post("/maintenance/{log_id}/resolve", response_model=MaintenanceLogResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def resolve_maintenance(
    log_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    log = await service.resolve_maintenance(
        log_id=log_id,
        technician_id=cast(int, current_user.id)
    )
    return log