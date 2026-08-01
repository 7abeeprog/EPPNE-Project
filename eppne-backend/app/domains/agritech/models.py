# app/domains/agritech/models.py
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base
import enum

# ========== الأنواع المساعدة ==========
class FarmType(str, enum.Enum):
    TRADITIONAL_SOIL = "TRADITIONAL_SOIL"
    HYDROPONICS = "HYDROPONICS"
    AEROPONICS = "AEROPONICS"
    VERTICAL_FARM = "VERTICAL_FARM"
    AQUAPONICS = "AQUAPONICS"
    LIVESTOCK_FARM = "LIVESTOCK_FARM"
    POULTRY_FARM = "POULTRY_FARM"
    FISH_FARM = "FISH_FARM"
    VERMICULTURE_FARM = "VERMICULTURE_FARM"
    ALGAE_FARM = "ALGAE_FARM"

class CropCategory(str, enum.Enum):
    VEGETABLES = "VEGETABLES"
    FRUITS = "FRUITS"
    GRAINS = "GRAINS"
    LEGUMES = "LEGUMES"
    MEDICINAL_AROMATIC = "MEDICINAL_AROMATIC"
    FODDER_CROPS = "FODDER_CROPS"
    INDUSTRIAL_CROPS = "INDUSTRIAL_CROPS"
    ORNAMENTAL_PLANTS = "ORNAMENTAL_PLANTS"
    TIMBER_TREES = "TIMBER_TREES"

class HarvestGrade(str, enum.Enum):
    GRADE_1_EXPORT = "GRADE_1_EXPORT"
    GRADE_2_LOCAL = "GRADE_2_LOCAL"
    GRADE_3_PROCESSING = "GRADE_3_PROCESSING"
    GRADE_4_FODDER = "GRADE_4_FODDER"
    WASTE_SMART_BIO = "WASTE_SMART_BIO"

class BioAssetType(str, enum.Enum):
    LIVESTOCK = "LIVESTOCK"
    POULTRY = "POULTRY"
    AQUACULTURE = "AQUACULTURE"
    VERMICULTURE = "VERMICULTURE"
    ALGAE = "ALGAE"
    INSECTS = "INSECTS"

class BioProductType(str, enum.Enum):
    MILK = "MILK"
    EGG = "EGG"
    MEAT = "MEAT"
    HONEY = "HONEY"
    VERMICOMPOST = "VERMICOMPOST"
    COMPOST_TEA = "COMPOST_TEA"
    BIO_WASTE = "BIO_WASTE"

# ========== 1. المزارع السيادية ==========
class SmartFarm(Base):
    __tablename__ = "smart_farms"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    land_asset_id = Column(Integer, ForeignKey("land_assets.id"), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    farm_type = Column(SQLEnum(FarmType), nullable=False)
    total_area_acres = Column(Numeric(10, 2), nullable=False)
    has_insurance = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

# ========== 2. قطاعات المزرعة ==========
class FarmZone(Base):
    __tablename__ = "farm_zones"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    farm_id = Column(Integer, ForeignKey("smart_farms.id"), nullable=False, index=True)
    smart_asset_id = Column(Integer, ForeignKey("smart_assets.id"), nullable=True)

    zone_code = Column(String(50), nullable=False)
    zone_type = Column(String(50), nullable=False)
    area_sqm = Column(Numeric(10, 2), nullable=True)

    soil_type = Column(String(100), nullable=True)
    irrigation_type = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_farmzone_tenant_farm", "tenant_id", "farm_id"),
    )

# ========== 3. الدورات الزراعية ==========
class CropCycle(Base):
    __tablename__ = "crop_cycles"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    zone_id = Column(Integer, ForeignKey("farm_zones.id"), nullable=False, index=True)

    crop_name = Column(String(150), nullable=False)
    category = Column(SQLEnum(CropCategory), nullable=False)
    seed_nft_id = Column(String(100), nullable=True)

    planting_date = Column(DateTime(timezone=True), nullable=False)
    expected_harvest_date = Column(DateTime(timezone=True), nullable=False)
    expected_yield_kg = Column(Numeric(15, 2), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_cropcycle_tenant_zone", "tenant_id", "zone_id"),
        CheckConstraint("expected_harvest_date > planting_date", name="check_harvest_after_planting"),
    )

# ========== 4. الحصاد ==========
class HarvestBatch(Base):
    __tablename__ = "harvest_batches"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    cycle_id = Column(Integer, ForeignKey("crop_cycles.id"), nullable=False, index=True)

    harvest_date = Column(DateTime(timezone=True), server_default=func.now())
    grade = Column(SQLEnum(HarvestGrade), nullable=False)
    quantity_kg = Column(Numeric(15, 2), nullable=False)

    waste_for_smart_bio_kg = Column(Numeric(15, 2), default=0)
    fodder_for_livestock_kg = Column(Numeric(15, 2), default=0)

    destination_facility_id = Column(Integer, nullable=True)
    shipment_tracking_number = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_harvest_tenant_cycle", "tenant_id", "cycle_id"),
    )

# ========== 5. الثروة الحيوانية ==========
class BioAssetCohort(Base):
    __tablename__ = "bio_asset_cohorts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    zone_id = Column(Integer, ForeignKey("farm_zones.id"), nullable=False, index=True)

    bio_type = Column(SQLEnum(BioAssetType), nullable=False)
    species_or_breed = Column(String(150), nullable=False)
    initial_count_or_kg = Column(Numeric(15, 2), nullable=False)
    current_count_or_kg = Column(Numeric(15, 2), nullable=False)

    start_date = Column(DateTime(timezone=True), nullable=False)
    health_status = Column(String(100), default="EXCELLENT")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_bio_tenant_zone", "tenant_id", "zone_id"),
    )

# ========== 6. الإنتاج الحيواني ==========
class BioProductYield(Base):
    __tablename__ = "bio_product_yields"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    cohort_id = Column(Integer, ForeignKey("bio_asset_cohorts.id"), nullable=False, index=True)

    product_type = Column(SQLEnum(BioProductType), nullable=False)
    quantity_unit = Column(Numeric(15, 2), nullable=False)
    collection_date = Column(DateTime(timezone=True), nullable=False)

    destination_farm_id = Column(Integer, ForeignKey("smart_farms.id"), nullable=True)
    waste_for_smart_bio_kg = Column(Numeric(15, 2), default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_bioyield_tenant_cohort", "tenant_id", "cohort_id"),
    )

# ========== 7. سلسلة التوريد ==========
class SupplyChainStage(Base):
    __tablename__ = "supply_chain_stages"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    traceable_type = Column(String(50), nullable=False)
    traceable_id = Column(Integer, nullable=False, index=True)

    stage_name = Column(String(100), nullable=False)
    stage_order = Column(Integer, nullable=False)
    location = Column(String(255), nullable=True)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    blockchain_tx_hash = Column(String(100), unique=True, nullable=True)
    ipfs_evidence_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_trace_tenant_type_id", "tenant_id", "traceable_type", "traceable_id"),
        Index("ix_traceable_stage", "traceable_type", "traceable_id", "stage_order"),
    )

# ========== 8. QR للتتبع ==========
class TraceabilityQR(Base):
    __tablename__ = "traceability_qrs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    traceable_type = Column(String(50), nullable=False)
    traceable_id = Column(Integer, nullable=False, index=True)
    qr_code = Column(String(255), unique=True, nullable=False)
    public_url = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_qr_tenant_traceable", "tenant_id", "traceable_type", "traceable_id"),
    )

# ========== 9. الشهادات الزراعية ==========
class AgriculturalCertificate(Base):
    __tablename__ = "agricultural_certificates"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    certificate_type = Column(String(50), nullable=False)
    certificate_name = Column(String(255), nullable=False)
    issuing_body = Column(String(255), nullable=False)

    certified_entity_type = Column(String(50), nullable=False)
    certified_entity_id = Column(Integer, nullable=False, index=True)

    issue_date = Column(DateTime(timezone=True), nullable=False)
    expiry_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="ACTIVE", index=True)

    certificate_nft_id = Column(String(100), unique=True, nullable=True)
    ipfs_document_hash = Column(String(100), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        CheckConstraint("expiry_date > issue_date", name="check_cert_dates"),
        Index("ix_cert_entity", "certified_entity_type", "certified_entity_id"),
    )

# ========== 10. مستشعرات التربة ==========
class SoilSensorReading(Base):
    __tablename__ = "soil_sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    zone_id = Column(Integer, ForeignKey("farm_zones.id"), nullable=False, index=True)
    sensor_device_id = Column(String(100), nullable=False)

    moisture_percent = Column(Numeric(5, 2), nullable=True)
    temperature_celsius = Column(Numeric(5, 2), nullable=True)
    ph_level = Column(Numeric(3, 2), nullable=True)
    nitrogen_ppm = Column(Numeric(10, 2), nullable=True)
    phosphorus_ppm = Column(Numeric(10, 2), nullable=True)
    potassium_ppm = Column(Numeric(10, 2), nullable=True)

    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_soil_tenant_zone_time", "tenant_id", "zone_id", "recorded_at"),
    )

# ========== 11. تنبيهات الطقس ==========
class WeatherAlert(Base):
    __tablename__ = "weather_alerts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), default="WARNING")
    location_gps = Column(JSONB, nullable=True)
    message = Column(Text, nullable=False)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)

    affected_farm_ids = Column(JSONB, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)