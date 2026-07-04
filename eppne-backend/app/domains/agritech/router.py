# app/domains/agritech/router.py (الإصدار النهائي المتكامل)
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser
from app.domains.identity.models import User
from app.domains.agritech.service import AgriTechService
from app.domains.agritech.repository import AgriTechRepository
from app.domains.agritech.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/agritech", tags=["Smart AgriTech"])

# ========== Farms (مع Rate Limiting واستخدام الخدمة) ==========
@router.post("/farms", response_model=SmartFarmResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_farm(
    data: SmartFarmCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db)
    farm = await service.create_farm(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump()
    )
    return farm

@router.get("/farms", response_model=list[SmartFarmResponse])
async def list_farms(
    farm_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = AgriTechRepository(db)
    farms = await repo.list_farms(tenant.id, farm_type, skip, limit)
    return farms

# ========== Zones ==========
@router.post("/farms/{farm_id}/zones", response_model=FarmZoneResponse, status_code=201)
async def add_farm_zone(
    farm_id: int,
    data: FarmZoneCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AgriTechRepository(db)
    zone = await repo.create_zone(farm_id=farm_id, **data.model_dump())
    return zone

# ========== Crop Cycles ==========
@router.post("/zones/{zone_id}/crop-cycles", response_model=CropCycleResponse, status_code=201)
async def start_crop_cycle(
    zone_id: int,
    data: CropCycleCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AgriTechRepository(db)
    cycle = await repo.create_crop_cycle(zone_id=zone_id, **data.model_dump())
    return cycle

# ========== Harvest (مع Idempotency و Rate Limiting) ==========
@router.post("/crop-cycles/{cycle_id}/harvest", response_model=HarvestBatchResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def register_harvest(
    cycle_id: int,
    data: HarvestBatchCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db)
    result = await service.register_harvest(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data={**data.model_dump(), "cycle_id": cycle_id},
        idempotency_key=idempotency_key
    )
    return HarvestBatchResponse(
        id=result["harvest_id"],
        cycle_id=cycle_id,
        grade=data.grade,
        quantity_kg=data.quantity_kg,
        waste_for_smart_bio_kg=data.waste_for_smart_bio_kg,
        fodder_for_livestock_kg=data.fodder_for_livestock_kg,
        destination_facility_id=data.destination_facility_id,
        harvest_date=datetime.utcnow(),
        shipment_tracking_number=result.get("tracking_number")
    )

# ========== Bio Assets ==========
@router.post("/zones/{zone_id}/bio-cohorts", response_model=BioAssetCohortResponse, status_code=201)
async def add_bio_cohort(
    zone_id: int,
    data: BioAssetCohortCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AgriTechRepository(db)
    cohort = await repo.create_bio_cohort(
        zone_id=zone_id,
        current_count_or_kg=data.initial_count_or_kg,
        **data.model_dump()
    )
    return cohort

@router.post("/bio-cohorts/{cohort_id}/yields", response_model=BioProductYieldResponse)
async def register_bio_yield(
    cohort_id: int,
    data: BioProductYieldCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db)
    result = await service.register_bio_yield(
        user_id=current_user.id,
        tenant_id=cohort_id,  # مؤقت، سيتم تحسينه لاحقاً
        yield_data={"cohort_id": cohort_id, **data.model_dump()}
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

# ========== Supply Chain ==========
@router.post("/traceability/stage", response_model=SupplyChainStageResponse, status_code=201)
async def add_traceability_stage(
    data: SupplyChainStageCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db)
    stage = await service.add_traceability_stage(
        user_id=current_user.id,
        tenant_id=1,  # مؤقت، سيتم تحسينه لاحقاً
        data=data.model_dump()
    )
    return stage

@router.get("/traceability/{traceable_type}/{traceable_id}", response_model=List[SupplyChainStageResponse])
async def get_traceability(
    traceable_type: str,
    traceable_id: int,
    db: AsyncSession = Depends(get_db)
):
    repo = AgriTechRepository(db)
    stages = await repo.get_supply_chain_stages(traceable_type, traceable_id)
    return stages

@router.post("/traceability/qr/{traceable_type}/{traceable_id}", response_model=TraceabilityQRResponse)
async def generate_traceability_qr(
    traceable_type: str,
    traceable_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db)
    qr = await service.generate_traceability_qr(1, traceable_type, traceable_id)  # tenant_id مؤقت
    return qr

# ========== Certifications ==========
@router.post("/certificates", response_model=AgriculturalCertificateResponse, status_code=201)
async def issue_certificate(
    data: AgriculturalCertificateCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db)
    cert = await service.issue_certificate(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data={**data.model_dump(), "tenant_id": tenant.id}
    )
    return cert

@router.get("/certificates/{entity_type}/{entity_id}", response_model=List[AgriculturalCertificateResponse])
async def get_entity_certificates(
    entity_type: str,
    entity_id: int,
    db: AsyncSession = Depends(get_db)
):
    repo = AgriTechRepository(db)
    certs = await repo.get_certificates_for_entity(entity_type, entity_id)
    return certs

# ========== IoT Soil Sensors (مع Rate Limiting واستخدام الخدمة) ==========
@router.post("/soil-readings", response_model=SoilSensorReadingResponse, status_code=201)
@rate_limit(max_requests=30, window_seconds=60)
async def record_soil_reading(
    data: SoilSensorReadingCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db)
    reading = await service.record_soil_data(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump()
    )
    return reading

@router.get("/soil-readings/{zone_id}", response_model=List[SoilSensorReadingResponse])
async def get_soil_readings(
    zone_id: int,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    repo = AgriTechRepository(db)
    readings = await repo.get_recent_soil_readings(zone_id, limit)
    return readings

# ========== Weather Alerts ==========
@router.post("/weather-alerts", response_model=WeatherAlertResponse, status_code=201)
async def create_weather_alert(
    data: WeatherAlertCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    repo = AgriTechRepository(db)
    alert = await repo.create_weather_alert(tenant_id=tenant.id, **data.model_dump())
    return alert

@router.get("/weather-alerts", response_model=List[WeatherAlertResponse])
async def get_active_weather_alerts(
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db)
    alerts = await service.get_weather_alerts(tenant.id)
    return alerts