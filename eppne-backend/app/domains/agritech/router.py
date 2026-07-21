# app/domains/agritech/router.py (الإصدار النهائي المتكامل)
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, cast
from datetime import datetime
import uuid

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser
from app.domains.identity.models import User
from app.domains.agritech.service import AgriTechService
from app.domains.agritech.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/agritech", tags=["Smart AgriTech"])

# ==========================================
# 1. المزارع (Farms) - مع Rate Limiting
# ==========================================

@router.post("/farms", response_model=SmartFarmResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_farm(
    data: SmartFarmCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إنشاء مزرعة سيادية جديدة"""
    service = AgriTechService(db)
    farm = await service.create_farm(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return farm

@router.get("/farms", response_model=List[SmartFarmResponse])
async def list_farms(
    farm_type: Optional[str] = Query(None, description="نوع المزرعة"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب قائمة المزارع للمستأجر الحالي"""
    service = AgriTechService(db)
    farms = await service.list_farms(
        tenant_id=cast(int, tenant.id),
        farm_type=farm_type,
        skip=skip,
        limit=limit
    )
    return farms

@router.get("/farms/{farm_id}", response_model=SmartFarmResponse)
async def get_farm(
    farm_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب تفاصيل مزرعة محددة"""
    service = AgriTechService(db)
    farm = await service.get_farm(
        farm_id=farm_id,
        tenant_id=cast(int, tenant.id)
    )
    if not farm:
        raise HTTPException(status_code=404, detail="المزرعة غير موجودة")
    return farm

# ==========================================
# 2. المناطق (Zones) - مع صلاحيات محسنة
# ==========================================

@router.post("/farms/{farm_id}/zones", response_model=FarmZoneResponse, status_code=201)
@rate_limit(max_requests=20, window_seconds=60)
async def add_farm_zone(
    farm_id: int,
    data: FarmZoneCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إضافة منطقة جديدة لمزرعة (يتطلب صلاحية مدرب أو إداري)"""
    service = AgriTechService(db)
    zone = await service.add_farm_zone(
        farm_id=farm_id,
        tenant_id=cast(int, tenant.id),
        user_id=cast(int, current_user.id),
        data=data.model_dump()
    )
    return zone

@router.get("/farms/{farm_id}/zones", response_model=List[FarmZoneResponse])
async def list_farm_zones(
    farm_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """جلب مناطق مزرعة محددة"""
    service = AgriTechService(db)
    zones = await service.list_farm_zones(
        farm_id=farm_id,
        tenant_id=cast(int, tenant.id)
    )
    return zones

# ==========================================
# 3. الدورات الزراعية (Crop Cycles) - مع Idempotency
# ==========================================

@router.post("/zones/{zone_id}/crop-cycles", response_model=CropCycleResponse, status_code=201)
@rate_limit(max_requests=15, window_seconds=60)
async def start_crop_cycle(
    zone_id: int,
    data: CropCycleCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """بدء دورة زراعية جديدة (مع Idempotency)"""
    service = AgriTechService(db)
    cycle = await service.start_crop_cycle(
        zone_id=zone_id,
        tenant_id=cast(int, tenant.id),
        user_id=cast(int, current_user.id),
        data=data.model_dump(),
        idempotency_key=idempotency_key or f"CYCLE-{uuid.uuid4().hex[:12].upper()}"
    )
    return cycle

@router.get("/zones/{zone_id}/crop-cycles", response_model=List[CropCycleResponse])
async def list_crop_cycles(
    zone_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """جلب الدورات الزراعية لمنطقة محددة"""
    service = AgriTechService(db)
    cycles = await service.list_crop_cycles(
        zone_id=zone_id,
        tenant_id=cast(int, tenant.id)
    )
    return cycles

# ==========================================
# 4. الحصاد (Harvest) - مع Idempotency و AI
# ==========================================

@router.post("/crop-cycles/{cycle_id}/harvest", response_model=HarvestBatchResponse, status_code=201)
@rate_limit(max_requests=20, window_seconds=60)
async def register_harvest(
    cycle_id: int,
    data: HarvestBatchCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """تسجيل محصول جديد (مع Idempotency و تحليل AI)"""
    service = AgriTechService(db)
    harvest_data = data.model_dump()
    harvest_data["cycle_id"] = cycle_id
    result = await service.register_harvest(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=harvest_data,
        idempotency_key=idempotency_key or f"HARVEST-{uuid.uuid4().hex[:12].upper()}"
    )
    return HarvestBatchResponse(
        id=result["harvest_id"],
        cycle_id=cycle_id,
        grade=result["grade"],
        quantity_kg=Decimal(str(result["quantity_kg"])),
        waste_for_smart_bio_kg=data.waste_for_smart_bio_kg,
        fodder_for_livestock_kg=data.fodder_for_livestock_kg,
        destination_facility_id=data.destination_facility_id,
        harvest_date=datetime.utcnow(),
        shipment_tracking_number=result.get("tracking_number")
    )

# ==========================================
# 5. الأصول الحيوانية (Bio Assets) - مع صلاحيات محسنة
# ==========================================

@router.post("/zones/{zone_id}/bio-cohorts", response_model=BioAssetCohortResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def add_bio_cohort(
    zone_id: int,
    data: BioAssetCohortCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إضافة مجموعة حيوانية جديدة (مع Idempotency)"""
    service = AgriTechService(db)
    cohort = await service.add_bio_cohort(
        zone_id=zone_id,
        tenant_id=cast(int, tenant.id),
        user_id=cast(int, current_user.id),
        data=data.model_dump(),
        idempotency_key=idempotency_key or f"BIO-{uuid.uuid4().hex[:12].upper()}"
    )
    return cohort

@router.post("/bio-cohorts/{cohort_id}/yields", response_model=BioProductYieldResponse, status_code=201)
@rate_limit(max_requests=20, window_seconds=60)
async def register_bio_yield(
    cohort_id: int,
    data: BioProductYieldCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """تسجيل إنتاج حيواني جديد (مع Idempotency)"""
    service = AgriTechService(db)
    yield_data = data.model_dump()
    yield_data["cohort_id"] = cohort_id
    result = await service.register_bio_yield(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        yield_data=yield_data,
        idempotency_key=idempotency_key or f"YIELD-{uuid.uuid4().hex[:12].upper()}"
    )
    return BioProductYieldResponse(
        id=result["yield_id"],
        cohort_id=cohort_id,
        product_type=data.product_type,
        quantity_unit=data.quantity_unit,
        collection_date=data.collection_date,
        destination_farm_id=data.destination_farm_id,
        waste_for_smart_bio_kg=data.waste_for_smart_bio_kg,
        created_at=datetime.utcnow()
    )

# ==========================================
# 6. سلسلة التوريد (Supply Chain) - مع صلاحيات محسنة
# ==========================================

@router.post("/traceability/stage", response_model=SupplyChainStageResponse, status_code=201)
@rate_limit(max_requests=15, window_seconds=60)
async def add_traceability_stage(
    data: SupplyChainStageCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إضافة مرحلة جديدة في سلسلة التوريد"""
    service = AgriTechService(db)
    stage = await service.add_traceability_stage(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return stage

@router.get("/traceability/{traceable_type}/{traceable_id}", response_model=List[SupplyChainStageResponse])
async def get_traceability(
    traceable_type: str,
    traceable_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """جلب سلسلة التوريد لكيان معين"""
    service = AgriTechService(db)
    stages = await service.get_traceability_stages(
        traceable_type=traceable_type,
        traceable_id=traceable_id,
        tenant_id=cast(int, tenant.id)
    )
    return stages

@router.post("/traceability/qr/{traceable_type}/{traceable_id}", response_model=TraceabilityQRResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def generate_traceability_qr(
    traceable_type: str,
    traceable_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """توليد QR للتتبع"""
    service = AgriTechService(db)
    qr = await service.generate_traceability_qr(
        tenant_id=cast(int, tenant.id),
        traceable_type=traceable_type,
        traceable_id=traceable_id,
        user_id=cast(int, current_user.id)
    )
    return qr

# ==========================================
# 7. الشهادات (Certificates) - مع صلاحيات Superuser
# ==========================================

@router.post("/certificates", response_model=AgriculturalCertificateResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def issue_certificate(
    data: AgriculturalCertificateCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),  # ✅ صلاحية عالية
    db: AsyncSession = Depends(get_db)
):
    """إصدار شهادة زراعية (للإدارة فقط)"""
    service = AgriTechService(db)
    cert = await service.issue_certificate(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return cert

@router.get("/certificates/{entity_type}/{entity_id}", response_model=List[AgriculturalCertificateResponse])
async def get_entity_certificates(
    entity_type: str,
    entity_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """جلب شهادات كيان معين"""
    service = AgriTechService(db)
    certs = await service.get_entity_certificates(
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=cast(int, tenant.id)
    )
    return certs

# ==========================================
# 8. مستشعرات التربة (Soil Sensors) - مع Rate Limiting
# ==========================================

@router.post("/soil-readings", response_model=SoilSensorReadingResponse, status_code=201)
@rate_limit(max_requests=30, window_seconds=60)
async def record_soil_reading(
    data: SoilSensorReadingCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """تسجيل قراءة جديدة من مستشعر التربة"""
    service = AgriTechService(db)
    reading = await service.record_soil_data(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return reading

@router.get("/soil-readings/{zone_id}", response_model=List[SoilSensorReadingResponse])
async def get_soil_readings(
    zone_id: int,
    limit: int = Query(100, ge=1, le=500),
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """جلب قراءات المستشعرات لمنطقة محددة"""
    service = AgriTechService(db)
    readings = await service.get_recent_soil_readings(
        zone_id=zone_id,
        tenant_id=cast(int, tenant.id),
        limit=limit
    )
    return readings

# ==========================================
# 9. تنبيهات الطقس - مع صلاحيات Superuser
# ==========================================

@router.post("/weather-alerts", response_model=WeatherAlertResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_weather_alert(
    data: WeatherAlertCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),  # ✅ صلاحية عالية
    db: AsyncSession = Depends(get_db)
):
    """إنشاء تنبيه طقس جديد (للإدارة فقط)"""
    service = AgriTechService(db)
    alert = await service.create_weather_alert(
        tenant_id=cast(int, tenant.id),
        user_id=cast(int, current_user.id),
        data=data.model_dump()
    )
    return alert

@router.get("/weather-alerts", response_model=List[WeatherAlertResponse])
async def get_active_weather_alerts(
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """جلب تنبيهات الطقس النشطة"""
    service = AgriTechService(db)
    alerts = await service.get_weather_alerts(tenant_id=cast(int, tenant.id))
    return alerts