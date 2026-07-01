# app/domains/manufacturing/router.py (الإصدار النهائي المتكامل)
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser
from app.domains.identity.models import User
from app.domains.manufacturing.service import ManufacturingService
from app.domains.manufacturing.repository import ManufacturingRepository
from app.domains.manufacturing.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/manufacturing", tags=["Sovereign Manufacturing"])

# ========== المنشآت (مع Rate Limiting واستخدام الخدمة) ==========
@router.post("/facilities", response_model=ManufacturingFacilityResponse, status_code=201)
@rate_limit(max_requests=10, window=60)
async def create_facility(
    data: ManufacturingFacilityCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    facility = await service.create_facility(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump()
    )
    return facility

# ========== خطوط الإنتاج ==========
@router.post("/facilities/{facility_id}/lines", response_model=ProductionLineResponse, status_code=201)
async def add_production_line(
    facility_id: int,
    data: ProductionLineCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = ManufacturingRepository(db)
    line = await repo.create_production_line(facility_id=facility_id, **data.model_dump())
    return line

# ========== النماذج (Blueprints) ==========
@router.post("/blueprints", response_model=ProductBlueprintResponse, status_code=201)
async def create_blueprint(
    data: ProductBlueprintCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = ManufacturingRepository(db)
    bp = await repo.create_blueprint(tenant_id=tenant.id, facility_id=1, **data.model_dump())
    return bp

# ========== دفعات الإنتاج ==========
@router.post("/batches", response_model=ProductionBatchResponse, status_code=201)
async def create_batch(
    data: ProductionBatchCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = ManufacturingRepository(db)
    batch = await repo.create_batch(tenant_id=tenant.id, **data.model_dump())
    return batch

@router.post("/batches/{batch_id}/start", response_model=StartProductionResponse)
@rate_limit(max_requests=5, window=60)
async def start_production(
    batch_id: int,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    result = await service.start_production(
        user_id=current_user.id,
        tenant_id=tenant.id,
        batch_id=batch_id,
        idempotency_key=idempotency_key
    )
    return result

# ========== المواد الخام ==========
@router.post("/raw-materials", response_model=RawMaterialBatchResponse, status_code=201)
async def register_raw_material(
    data: RawMaterialBatchCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    batch = await service.register_raw_material_batch(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump()
    )
    return batch

@router.get("/raw-materials", response_model=List[RawMaterialBatchResponse])
async def list_raw_materials(
    skip: int = 0,
    limit: int = 100,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = ManufacturingRepository(db)
    materials = await repo.list_raw_materials(tenant.id, skip, limit)
    return materials

@router.post("/batches/{batch_id}/consume-material")
@rate_limit(max_requests=20, window=60)
async def consume_raw_material(
    batch_id: int,
    data: MaterialConsumptionCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    log = await service.consume_raw_material(
        user_id=current_user.id,
        tenant_id=tenant.id,
        batch_id=batch_id,
        raw_material_batch_id=data.raw_material_batch_id,
        quantity=data.quantity_used_kg,
        idempotency_key=idempotency_key
    )
    return {"message": "Material consumed", "log_id": log.id}

# ========== التوأم الرقمي ==========
@router.post("/product-items/{product_item_id}/digital-twin", response_model=ProductDigitalTwinResponse, status_code=201)
async def create_digital_twin(
    product_item_id: int,
    batch_id: int,
    production_line_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    twin = await service.create_product_digital_twin(product_item_id, batch_id, production_line_id)
    return twin

@router.get("/product-items/{product_item_id}/digital-twin", response_model=ProductDigitalTwinResponse)
async def get_digital_twin(
    product_item_id: int,
    db: AsyncSession = Depends(get_db)
):
    repo = ManufacturingRepository(db)
    twin = await repo.get_digital_twin(product_item_id)
    if not twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    return twin

# ========== شهادات الجودة ==========
@router.post("/quality-certificates", response_model=QualityCertificateResponse, status_code=201)
async def issue_quality_certificate(
    data: QualityCertificateCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    cert = await service.issue_quality_certificate(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump()
    )
    return cert

@router.get("/quality-certificates/{entity_type}/{entity_id}", response_model=List[QualityCertificateResponse])
async def get_entity_certificates(
    entity_type: str,
    entity_id: int,
    db: AsyncSession = Depends(get_db)
):
    repo = ManufacturingRepository(db)
    certs = await repo.get_certificates_for_entity(entity_type, entity_id)
    return certs

# ========== الصيانة التنبؤية (مع Rate Limiting واستخدام الخدمة) ==========
@router.post("/predictive-maintenance", response_model=PredictiveMaintenanceLogResponse, status_code=201)
@rate_limit(max_requests=30, window=60)
async def analyze_maintenance(
    data: PredictiveMaintenanceLogCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    log = await service.analyze_and_schedule_maintenance(
        user_id=current_user.id,
        tenant_id=tenant.id,
        production_line_id=data.production_line_id,
        sensor_data=data.sensor_data
    )
    return log

@router.get("/production-lines/{line_id}/pending-maintenance", response_model=List[PredictiveMaintenanceLogResponse])
async def get_pending_maintenance(
    line_id: int,
    db: AsyncSession = Depends(get_db)
):
    repo = ManufacturingRepository(db)
    logs = await repo.get_pending_maintenance(line_id)
    return logs

@router.post("/maintenance/{log_id}/schedule")
async def schedule_maintenance(
    log_id: int,
    scheduled_at: datetime,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = ManufacturingRepository(db)
    log = await repo.schedule_maintenance(log_id, scheduled_at)
    return {"message": "Maintenance scheduled", "scheduled_at": log.maintenance_scheduled_at}

# ========== قطع الغيار ==========
@router.post("/spare-parts", response_model=SparePartResponse, status_code=201)
async def create_spare_part(
    data: SparePartCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    repo = ManufacturingRepository(db)
    part = await repo.create_spare_part(tenant_id=tenant.id, **data.model_dump())
    return part

@router.post("/spare-parts/{part_id}/restock", response_model=SparePartResponse)
async def restock_spare_part(
    part_id: int,
    data: SparePartRestock,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    part = await service.restock_spare_part(part_id, data.quantity_added, current_user.id)
    return part

@router.get("/spare-parts", response_model=List[SparePartResponse])
async def list_spare_parts(
    skip: int = 0,
    limit: int = 100,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = ManufacturingRepository(db)
    parts = await repo.list_spare_parts(tenant.id, skip, limit)
    return parts