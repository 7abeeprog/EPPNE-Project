# app/domains/agritech/router.py
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, cast

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser
from app.domains.identity.models import User
from app.domains.agritech.service import AgriTechService
from app.domains.agritech.schemas import *
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/agritech", tags=["Sovereign Agritech"])


# ========== 1. المزارع (Farms) ==========
@router.post("/farms", response_model=SmartFarmResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_farm(
    data: SmartFarmCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db, cast(int, current_user.tenant_id))
    return await service.create_farm(cast(int, current_user.id), data.model_dump())


@router.get("/farms", response_model=List[SmartFarmResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_farms(
    farm_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db, cast(int, current_user.tenant_id))
    result = await service.list_farms(farm_type, skip, limit)
    return result["items"]


@router.get("/farms/{farm_id}", response_model=SmartFarmResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_farm(
    farm_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db, cast(int, current_user.tenant_id))
    farm = await service.get_farm(farm_id)
    if not farm:
        raise HTTPException(404, "المزرعة غير موجودة")
    return farm


# ========== 2. المناطق (Zones) ==========
@router.post("/farms/{farm_id}/zones", response_model=FarmZoneResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def add_farm_zone(
    farm_id: int,
    data: FarmZoneCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db, cast(int, current_user.tenant_id))
    return await service.add_farm_zone(farm_id, cast(int, current_user.id), data.model_dump())


@router.get("/farms/{farm_id}/zones", response_model=List[FarmZoneResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_farm_zones(
    farm_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db, cast(int, current_user.tenant_id))
    result = await service.list_farm_zones(farm_id)
    return result["items"]


# ========== 3. الدورات الزراعية (Crop Cycles) ==========
@router.post("/zones/{zone_id}/crop-cycles", response_model=CropCycleResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def start_crop_cycle(
    zone_id: int,
    data: CropCycleCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db, cast(int, current_user.tenant_id))
    return await service.start_crop_cycle(
        zone_id, cast(int, current_user.id), data.model_dump(), idempotency_key or ""
    )


@router.get("/zones/{zone_id}/crop-cycles", response_model=List[CropCycleResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_crop_cycles(
    zone_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db, cast(int, current_user.tenant_id))
    result = await service.list_crop_cycles(zone_id)
    return result["items"]


# ========== 4. الحصاد (Harvest) ==========
@router.post("/crop-cycles/{cycle_id}/harvest", response_model=HarvestRegistrationResult, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def register_harvest(
    cycle_id: int,
    data: HarvestBatchCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db, cast(int, current_user.tenant_id))
    payload = data.model_dump()
    payload["cycle_id"] = cycle_id
    return await service.register_harvest(cast(int, current_user.id), payload, idempotency_key or "")


# ========== 5. الأصول الحيوية (Bio Assets) ==========
@router.post("/zones/{zone_id}/bio-cohorts", response_model=BioAssetCohortResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def add_bio_cohort(
    zone_id: int,
    data: BioAssetCohortCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db, cast(int, current_user.tenant_id))
    return await service.add_bio_cohort(
        zone_id, cast(int, current_user.id), data.model_dump(), idempotency_key or ""
    )


@router.post("/bio-cohorts/{cohort_id}/yields", response_model=BioYieldRegistrationResult, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def register_bio_yield(
    cohort_id: int,
    data: BioProductYieldCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db, cast(int, current_user.tenant_id))
    payload = data.model_dump()
    payload["cohort_id"] = cohort_id
    return await service.register_bio_yield(cast(int, current_user.id), payload, idempotency_key or "")


# ========== 6. التتبع (Traceability) ==========
@router.post("/traceability/stage", response_model=SupplyChainStageResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def add_traceability_stage(
    data: SupplyChainStageCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db, cast(int, current_user.tenant_id))
    return await service.add_traceability_stage(cast(int, current_user.id), data.model_dump())


@router.get("/traceability/{traceable_type}/{traceable_id}", response_model=List[SupplyChainStageResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_traceability_stages(
    traceable_type: str,
    traceable_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db, cast(int, current_user.tenant_id))
    result = await service.get_traceability_stages(traceable_type, traceable_id)
    return result["items"]


@router.post("/traceability/qr/{traceable_type}/{traceable_id}", response_model=TraceabilityQRResponse, status_code=201)
@rate_limit(max_requests=5, window_seconds=60)
async def generate_traceability_qr(
    traceable_type: str,
    traceable_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db, cast(int, current_user.tenant_id))
    return await service.generate_traceability_qr(traceable_type, traceable_id, cast(int, current_user.id))


# ========== 7. الشهادات (Certificates) ==========
@router.post("/certificates", response_model=AgriculturalCertificateResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def issue_certificate(
    data: AgriculturalCertificateCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db, cast(int, current_user.tenant_id))
    return await service.issue_certificate(cast(int, current_user.id), data.model_dump())


@router.get("/certificates/{entity_type}/{entity_id}", response_model=List[AgriculturalCertificateResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_entity_certificates(
    entity_type: str,
    entity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db, cast(int, current_user.tenant_id))
    result = await service.get_entity_certificates(entity_type, entity_id)
    return result["items"]


# ========== 8. مستشعرات التربة (Soil Sensors) ==========
@router.post("/soil-readings", response_model=SoilSensorReadingResponse, status_code=201)
@rate_limit(max_requests=30, window_seconds=60)
async def record_soil_data(
    data: SoilSensorReadingCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db, cast(int, current_user.tenant_id))
    return await service.record_soil_data(cast(int, current_user.id), data.model_dump())


@router.get("/soil-readings/{zone_id}", response_model=List[SoilSensorReadingResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_recent_soil_readings(
    zone_id: int,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db, cast(int, current_user.tenant_id))
    result = await service.get_recent_soil_readings(zone_id, limit)
    return result["items"]


# ========== 9. تنبيهات الطقس (Weather Alerts) ==========
@router.post("/weather-alerts", response_model=WeatherAlertResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_weather_alert(
    data: WeatherAlertCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db, cast(int, current_user.tenant_id))
    return await service.create_weather_alert(cast(int, current_user.id), data.model_dump())


@router.get("/weather-alerts", response_model=List[WeatherAlertResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_active_weather_alerts(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AgriTechService(db, cast(int, current_user.tenant_id))
    return await service.get_weather_alerts()
