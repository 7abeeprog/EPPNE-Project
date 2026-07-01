# app/domains/iot/models.py (الإصدار النهائي المتكامل)
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime,
    Text, Boolean, Numeric, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum

# ========== الأنواع المساعدة ==========
class AssetClass(str, enum.Enum):
    SURVEILLANCE = "SURVEILLANCE"           # كاميرات مراقبة
    SMART_BIO_UNIT = "SMART_BIO_UNIT"       # وحدات تحويل المخلفات لطاقة
    ACCESS_GATE = "ACCESS_GATE"             # بوابات دخول
    HVAC = "HVAC"                           # تكييف وتهوية
    UTILITY_METER = "UTILITY_METER"         # عدادات كهرباء/مياه
    INDUSTRIAL_ROBOT = "INDUSTRIAL_ROBOT"   # روبوتات مصانع

class UtilityType(str, enum.Enum):
    ELECTRICITY = "ELECTRICITY"
    WATER = "WATER"
    BIOGAS = "BIOGAS"
    CARBON_CREDIT = "CARBON_CREDIT"

class GridStationType(str, enum.Enum):
    ELECTRICAL_POWER = "ELECTRICAL_POWER"
    WATER_TREATMENT = "WATER_TREATMENT"
    SEWAGE_AND_WASTE = "SEWAGE_AND_WASTE"
    FUEL_AND_GAS = "FUEL_AND_GAS"
    SMART_BIO_PLANT = "SMART_BIO_PLANT"

class DeviceHealthStatus(str, enum.Enum):
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    NEEDS_MAINTENANCE = "NEEDS_MAINTENANCE"
    OFFLINE = "OFFLINE"
    CRITICAL_FAILURE = "CRITICAL_FAILURE"

# ========== 1. الأصول الذكية (كاميرات، وحدات، عدادات) ==========
class SmartAsset(Base):
    __tablename__ = "smart_assets"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    owner_id = Column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)

    asset_code = Column(String(100), unique=True, index=True, nullable=False)
    asset_class = Column(SQLEnum(AssetClass), nullable=False, index=True)
    location_gps = Column(JSON, nullable=True)
    specs = Column(JSON, default=dict)

    is_online = Column(Boolean, default=False)
    health_status = Column(SQLEnum(DeviceHealthStatus), default=DeviceHealthStatus.EXCELLENT)

    hardware_did = Column(String(255), unique=True, nullable=True)
    iot_wallet_address = Column(String(42), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)


# ========== 2. المحطات المركزية (شبكات كهرباء، مياه، غاز حيوي) ==========
class UtilityGrid(Base):
    __tablename__ = "utility_grids"

    id = Column(Integer, primary_key=True, index=True)
    development_id = Column(Integer, nullable=True, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    name = Column(String(255), nullable=False)
    grid_type = Column(SQLEnum(GridStationType), nullable=False, index=True)

    max_capacity = Column(Numeric(20, 4), nullable=False)
    current_load = Column(Numeric(20, 4), default=0)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ========== 3. القراءات الحالية (Telemetry) ==========
class UtilityReading(Base):
    __tablename__ = "utility_readings"

    id = Column(Integer, primary_key=True, index=True)
    grid_id = Column(Integer, ForeignKey("utility_grids.id"), nullable=True, index=True)
    asset_id = Column(Integer, ForeignKey("smart_assets.id"), nullable=True, index=True)

    reading_type = Column(SQLEnum(UtilityType), nullable=False, index=True)
    reading_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    consumed_value = Column(Numeric(15, 4), default=0)
    produced_value = Column(Numeric(15, 4), default=0)

    carbon_emissions_mt = Column(Numeric(15, 4), default=0)
    carbon_credits_generated = Column(Numeric(15, 4), default=0)

    is_settled_on_chain = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ========== 4. سجلات الصيانة ==========
class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("smart_assets.id"), nullable=True, index=True)
    grid_id = Column(Integer, ForeignKey("utility_grids.id"), nullable=True, index=True)

    technician_id = Column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)
    maintenance_type = Column(String(50))
    task_description = Column(Text)

    cost_mrusdt = Column(Numeric(10, 2), default=0)
    time_credits_spent = Column(Numeric(10, 2), default=0)

    is_resolved = Column(Boolean, default=False)
    resolution_date = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ========== 5. جدول Idempotency (جديد) ==========
class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    response_data = Column(JSON, nullable=False)          # تخزين النتيجة كـ JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)  # صلاحية 24 ساعة


# ========== 6. جدول سجلات التدقيق (جديد) ==========
class IoTRequestLog(Base):
    __tablename__ = "iot_request_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    idempotency_key = Column(String(64), nullable=True, index=True)
    request_body = Column(JSON, nullable=True)           # اختياري لتتبع
    status_code = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())