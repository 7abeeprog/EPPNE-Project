# app/domains/iot/router.py (الإصدار النهائي المتكامل)
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser
from app.domains.identity.models import User
from app.domains.iot.service import IoTService
from app.domains.iot.schemas import *

router = APIRouter(prefix="/iot", tags=["IoT & Carbon Sovereignty"])

# ========== Smart Assets ==========
@router.post("/assets", response_model=SmartAssetResponse, status_code=201)
async def create_asset(
    request: Request,
    data: SmartAssetCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    asset = await service.create_asset(current_user.id, data.model_dump())
    return asset

@router.get("/assets", response_model=list[SmartAssetResponse])
async def list_my_assets(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    assets = await service.list_assets(current_user.id, skip=skip, limit=limit)
    return assets

@router.get("/assets/{asset_id}", response_model=SmartAssetResponse)
async def get_asset(
    request: Request,
    asset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    asset = await service.get_asset(asset_id, current_user.id)
    return asset

@router.patch("/assets/{asset_id}", response_model=SmartAssetResponse)
async def update_asset(
    request: Request,
    asset_id: int,
    data: SmartAssetUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    updated = await service.update_asset(asset_id, current_user.id, data.model_dump(exclude_unset=True))
    return updated

# ========== Utility Grids (Superuser only) ==========
@router.post("/grids", response_model=UtilityGridResponse, status_code=201)
async def create_grid(
    request: Request,
    data: UtilityGridCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    grid = await service.create_grid(data.model_dump())
    return grid

@router.get("/grids", response_model=list[UtilityGridResponse])
async def list_grids(
    request: Request,
    grid_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    grids = await service.list_grids(grid_type, skip, limit)
    return grids

# ========== Readings ==========
@router.post("/readings", response_model=dict, status_code=201)
async def ingest_reading(
    request: Request,
    data: UtilityReadingCreate,
    idempotency_key: Optional[str] = None,  # يمكن تمريره في الـ Header أو الـ Body
    current_user: User = Depends(get_current_active_user),  # مؤقتاً، يمكن أن يكون جهازاً
    db: AsyncSession = Depends(get_db)
):
    """
    استقبال قراءة من جهاز IoT.
    يُفضل تمرير `Idempotency-Key` في الـ Header لمنع تكرار الإرسال.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    # يمكننا استلام idempotency_key من الـ Header
    idem_key = request.headers.get("Idempotency-Key") or idempotency_key
    service = IoTService(db)
    result = await service.record_reading(
        data.model_dump(),
        idempotency_key=idem_key,
        ip=client_ip,
        ua=user_agent
    )
    return result

@router.get("/readings", response_model=list[UtilityReadingResponse])
async def get_readings(
    request: Request,
    asset_id: Optional[int] = None,
    grid_id: Optional[int] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    readings = await service.get_readings(current_user.id, asset_id, grid_id, limit)
    return readings

# ========== Carbon Settlement ==========
@router.post("/carbon/settle")
async def settle_carbon(
    request: Request,
    payload: CarbonSettlementRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    idem_key = request.headers.get("Idempotency-Key")
    service = IoTService(db)
    result = await service.settle_carbon_credits(
        current_user.id,
        payload.asset_ids,
        idempotency_key=idem_key,
        ip=client_ip,
        ua=user_agent
    )
    return result

# ========== Maintenance ==========
@router.post("/maintenance", response_model=MaintenanceLogResponse, status_code=201)
async def report_maintenance(
    request: Request,
    data: MaintenanceLogCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    log = await service.create_maintenance(data.model_dump())
    return log

@router.post("/maintenance/{log_id}/resolve", response_model=MaintenanceLogResponse)
async def resolve_maintenance(
    request: Request,
    log_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = IoTService(db)
    log = await service.resolve_maintenance(log_id, current_user.id)
    return log