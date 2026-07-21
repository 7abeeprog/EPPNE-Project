# app/domains/manufacturing/router.py (الإصدار النهائي المتكامل)
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, cast
from datetime import datetime

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser
from app.domains.identity.models import User
from app.domains.manufacturing.service import ManufacturingService
from app.domains.manufacturing.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/manufacturing", tags=["Sovereign Manufacturing"])


# ============================================================
# 1. المنشآت (Facilities)
# ============================================================

@router.post("/facilities", response_model=ManufacturingFacilityResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_facility(
    data: ManufacturingFacilityCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    facility = await service.create_facility(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return facility


@router.get("/facilities", response_model=List[ManufacturingFacilityResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_facilities(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    facilities = await service.list_facilities(
        tenant_id=cast(int, tenant.id),
        skip=skip,
        limit=limit
    )
    return facilities


@router.get("/facilities/{facility_id}", response_model=ManufacturingFacilityResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_facility(
    facility_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    facility = await service.get_facility(
        facility_id=facility_id,
        tenant_id=cast(int, tenant.id)
    )
    return facility


# ============================================================
# 2. خطوط الإنتاج (Production Lines)
# ============================================================

@router.post("/facilities/{facility_id}/lines", response_model=ProductionLineResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=15, window_seconds=60)
async def add_production_line(
    facility_id: int,
    data: ProductionLineCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    line = await service.add_production_line(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        facility_id=facility_id,
        data=data.model_dump()
    )
    return line


# ============================================================
# 3. النماذج (Blueprints)
# ============================================================

@router.post("/blueprints", response_model=ProductBlueprintResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=15, window_seconds=60)
async def create_blueprint(
    data: ProductBlueprintCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    bp = await service.create_blueprint(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return bp


# ============================================================
# 4. دفعات الإنتاج (Production Batches)
# ============================================================

@router.post("/batches", response_model=ProductionBatchResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=15, window_seconds=60)
async def create_batch(
    data: ProductionBatchCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    batch = await service.create_batch(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return batch


@router.post("/batches/{batch_id}/start", response_model=StartProductionResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def start_production(
    batch_id: int,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    result = await service.start_production(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        batch_id=batch_id,
        idempotency_key=idempotency_key
    )
    return result


# ============================================================
# 5. المواد الخام (Raw Materials)
# ============================================================

@router.post("/raw-materials", response_model=RawMaterialBatchResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=15, window_seconds=60)
async def register_raw_material(
    data: RawMaterialBatchCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    batch = await service.register_raw_material_batch(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return batch


@router.get("/raw-materials", response_model=List[RawMaterialBatchResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_raw_materials(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    materials = await service.list_raw_materials(
        tenant_id=cast(int, tenant.id),
        skip=skip,
        limit=limit
    )
    return materials


@router.post("/batches/{batch_id}/consume-material")
@rate_limit(max_requests=20, window_seconds=60)
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
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        batch_id=batch_id,
        raw_material_batch_id=data.raw_material_batch_id,
        quantity=data.quantity_used_kg,
        idempotency_key=idempotency_key
    )
    return {"message": "Material consumed", "log_id": log.id}


# ============================================================
# 6. المنتجات الذكية والتوأم الرقمي
# ============================================================

@router.post("/product-items/{product_item_id}/digital-twin", response_model=ProductDigitalTwinResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_digital_twin(
    product_item_id: int,
    batch_id: int,
    production_line_id: Optional[int] = None,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    twin = await service.create_digital_twin(
        product_item_id=product_item_id,
        batch_id=batch_id,
        production_line_id=production_line_id,
        tenant_id=cast(int, tenant.id),
        user_id=cast(int, current_user.id)
    )
    return twin


@router.get("/product-items/{product_item_id}/digital-twin", response_model=ProductDigitalTwinResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_digital_twin(
    product_item_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    twin = await service.get_digital_twin(
        product_item_id=product_item_id,
        tenant_id=cast(int, tenant.id)
    )
    if not twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    return twin


# ============================================================
# 7. شهادات الجودة (Quality Certificates)
# ============================================================

@router.post("/quality-certificates", response_model=QualityCertificateResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def issue_quality_certificate(
    data: QualityCertificateCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    cert = await service.issue_quality_certificate(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return cert


@router.get("/quality-certificates/{entity_type}/{entity_id}", response_model=List[QualityCertificateResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_entity_certificates(
    entity_type: str,
    entity_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    certs = await service.get_entity_certificates(
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=cast(int, tenant.id)
    )
    return certs


# ============================================================
# 8. الصيانة التنبؤية (Predictive Maintenance)
# ============================================================

@router.post("/predictive-maintenance", response_model=PredictiveMaintenanceLogResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=30, window_seconds=60)
async def analyze_maintenance(
    data: PredictiveMaintenanceLogCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    log = await service.analyze_and_schedule_maintenance(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        production_line_id=data.production_line_id,
        sensor_data=data.sensor_data
    )
    return log


@router.get("/production-lines/{line_id}/pending-maintenance", response_model=List[PredictiveMaintenanceLogResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_pending_maintenance(
    line_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    logs = await service.get_pending_maintenance(
        production_line_id=line_id,
        tenant_id=cast(int, tenant.id)
    )
    return logs


@router.post("/maintenance/{log_id}/schedule")
@rate_limit(max_requests=10, window_seconds=60)
async def schedule_maintenance(
    log_id: int,
    scheduled_at: datetime,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    log = await service.schedule_maintenance(
        log_id=log_id,
        scheduled_at=scheduled_at
    )
    return {"message": "Maintenance scheduled", "scheduled_at": log.maintenance_scheduled_at}


# ============================================================
# 9. قطع الغيار (Spare Parts)
# ============================================================

@router.post("/spare-parts", response_model=SparePartResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_spare_part(
    data: SparePartCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    part = await service.create_spare_part(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return part


@router.post("/spare-parts/{part_id}/restock", response_model=SparePartResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def restock_spare_part(
    part_id: int,
    data: SparePartRestock,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    part = await service.restock_spare_part(
        part_id=part_id,
        quantity_added=data.quantity_added,
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id)
    )
    return part


@router.get("/spare-parts", response_model=List[SparePartResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_spare_parts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ManufacturingService(db)
    parts = await service.list_spare_parts(
        tenant_id=cast(int, tenant.id),
        skip=skip,
        limit=limit
    )
    return parts