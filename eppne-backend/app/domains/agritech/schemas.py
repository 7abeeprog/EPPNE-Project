# app/domains/agritech/schemas.py (الإصدار النهائي المتكامل مع تصحيح Optional)
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.agritech.models import FarmType, CropCategory, HarvestGrade, BioAssetType, BioProductType

# ========== Farms ==========
class SmartFarmCreate(BaseModel):
    land_asset_id: int
    name: str
    farm_type: FarmType
    total_area_acres: Decimal
    has_insurance: bool = False

class SmartFarmResponse(SmartFarmCreate):
    id: int
    manager_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Zones ==========
class FarmZoneCreate(BaseModel):
    zone_code: str
    zone_type: str
    area_sqm: Optional[Decimal] = None
    soil_type: Optional[str] = None
    irrigation_type: Optional[str] = None
    smart_asset_id: Optional[int] = None

class FarmZoneResponse(FarmZoneCreate):
    id: int
    farm_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Crop Cycles ==========
class CropCycleCreate(BaseModel):
    crop_name: str
    category: CropCategory
    seed_nft_id: Optional[str] = None
    planting_date: datetime
    expected_harvest_date: datetime
    expected_yield_kg: Decimal

    @field_validator("expected_harvest_date")
    @classmethod
    def validate_harvest_after_planting(cls, v: datetime, info) -> datetime:
        planting = info.data.get("planting_date")
        if planting and v <= planting:
            raise ValueError("expected_harvest_date must be after planting_date")
        return v

class CropCycleResponse(CropCycleCreate):
    id: int
    zone_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Harvest ==========
class HarvestBatchCreate(BaseModel):
    grade: HarvestGrade
    quantity_kg: Decimal
    waste_for_smart_bio_kg: Decimal = Field(default=Decimal('0.0'), ge=Decimal('0.0'))
    fodder_for_livestock_kg: Decimal = Field(default=Decimal('0.0'), ge=Decimal('0.0'))
    destination_facility_id: Optional[int] = None

class HarvestBatchResponse(HarvestBatchCreate):
    id: int
    cycle_id: int
    harvest_date: datetime
    shipment_tracking_number: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

# ========== Bio Assets ==========
class BioAssetCohortCreate(BaseModel):
    bio_type: BioAssetType
    species_or_breed: str
    initial_count_or_kg: Decimal
    start_date: datetime

class BioAssetCohortResponse(BioAssetCohortCreate):
    id: int
    zone_id: int
    current_count_or_kg: Decimal
    health_status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class BioProductYieldCreate(BaseModel):
    product_type: BioProductType
    quantity_unit: Decimal
    collection_date: datetime
    destination_farm_id: Optional[int] = None
    waste_for_smart_bio_kg: Decimal = Field(default=Decimal('0.0'), ge=Decimal('0.0'))

class BioProductYieldResponse(BioProductYieldCreate):
    id: int
    cohort_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Supply Chain ==========
class SupplyChainStageCreate(BaseModel):
    traceable_type: str
    traceable_id: int
    stage_name: str
    stage_order: int
    location: Optional[str] = None
    ipfs_evidence_hash: Optional[str] = None

class SupplyChainStageResponse(SupplyChainStageCreate):
    id: int
    operator_id: Optional[int] = None
    timestamp: datetime
    blockchain_tx_hash: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class TraceabilityQRResponse(BaseModel):
    id: int
    traceable_type: str
    traceable_id: int
    qr_code: str
    public_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Certificates ==========
class AgriculturalCertificateCreate(BaseModel):
    certificate_type: str
    certificate_name: str
    issuing_body: str
    certified_entity_type: str
    certified_entity_id: int
    issue_date: datetime
    expiry_date: datetime
    ipfs_document_hash: Optional[str] = None

    @field_validator("expiry_date")
    @classmethod
    def validate_expiry_after_issue(cls, v: datetime, info) -> datetime:
        issue = info.data.get("issue_date")
        if issue and v <= issue:
            raise ValueError("expiry_date must be after issue_date")
        return v

class AgriculturalCertificateResponse(AgriculturalCertificateCreate):
    id: int
    tenant_id: int
    status: str
    certificate_nft_id: Optional[str] = None
    created_by: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== IoT Sensors ==========
class SoilSensorReadingCreate(BaseModel):
    zone_id: int
    sensor_device_id: str
    moisture_percent: Optional[Decimal] = None
    temperature_celsius: Optional[Decimal] = None
    ph_level: Optional[Decimal] = None
    nitrogen_ppm: Optional[Decimal] = None
    phosphorus_ppm: Optional[Decimal] = None
    potassium_ppm: Optional[Decimal] = None
    recorded_at: datetime

class SoilSensorReadingResponse(SoilSensorReadingCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Weather Alerts ==========
class WeatherAlertCreate(BaseModel):
    alert_type: str
    severity: str = "WARNING"
    location_gps: Optional[Dict[str, float]] = None
    message: str
    start_time: datetime
    end_time: Optional[datetime] = None
    affected_farm_ids: List[int] = Field(default_factory=list)

class WeatherAlertResponse(WeatherAlertCreate):
    id: int
    tenant_id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)