# app/domains/iot/models.py (الإصدار النهائي المتكامل مع ترقية JSONB)
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime,
    Text, Boolean, Numeric, Enum as SQLEnum, Index
)
from sqlalchemy.dialects.postgresql import JSONB  # ✅ تم إضافة الاستيراد الصحيح
from sqlalchemy.sql import func
from app.core.database import Base
import enum

# ========== الأنواع المساعدة ==========
class AssetClass(str, enum.Enum):
    SURVEILLANCE = "SURVEILLANCE"
    SMART_BIO_UNIT = "SMART_BIO_UNIT"
    ACCESS_GATE = "ACCESS_GATE"
    HVAC = "HVAC"
    UTILITY_METER = "UTILITY_METER"
    INDUSTRIAL_ROBOT = "INDUSTRIAL_ROBOT"

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
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    owner_id = Column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)

    asset_code = Column(String(100), unique=True, index=True, nullable=False)
    asset_class = Column(SQLEnum(AssetClass), nullable=False, index=True)
    location_gps = Column(JSONB, nullable=True)
    specs = Column(JSONB, default=dict)

    is_online = Column(Boolean, default=False)
    health_status = Column(SQLEnum(DeviceHealthStatus), default=DeviceHealthStatus.EXCELLENT)

    hardware_did = Column(String(255), unique=True, nullable=True)
    iot_wallet_address = Column(String(42), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_smart_asset_entity", "entity_id"),
        Index("ix_smart_asset_owner", "owner_id"),
        Index("ix_smart_asset_class", "asset_class"),
    )


# ========== 2. المحطات المركزية (شبكات كهرباء، مياه، غاز حيوي) ==========
class UtilityGrid(Base):
    __tablename__ = "utility_grids"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    development_id = Column(Integer, nullable=True, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    name = Column(String(255), nullable=False)
    grid_type = Column(SQLEnum(GridStationType), nullable=False, index=True)

    max_capacity = Column(Numeric(20, 4), nullable=False)
    current_load = Column(Numeric(20, 4), default=0)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_utility_grid_entity", "entity_id"),
        Index("ix_utility_grid_type", "grid_type"),
    )


# ========== 3. القراءات الحالية (Telemetry) ==========
class UtilityReading(Base):
    __tablename__ = "utility_readings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
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

    __table_args__ = (
        Index("ix_utility_reading_grid", "grid_id"),
        Index("ix_utility_reading_asset", "asset_id"),
        Index("ix_utility_reading_type_time", "reading_type", "reading_timestamp"),
    )


# ========== 4. سجلات الصيانة ==========
class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
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

    __table_args__ = (
        Index("ix_maintenance_asset", "asset_id"),
        Index("ix_maintenance_grid", "grid_id"),
        Index("ix_maintenance_resolved", "is_resolved"),
    )


# ========== 5. جدول Idempotency (مع ترقية JSONB) ==========
class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    response_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    __table_args__ = (
        Index("ix_idempotency_key", "key"),
        Index("ix_idempotency_expires", "expires_at"),
    )


# ========== 6. جدول سجلات التدقيق (مع ترقية JSONB) ==========
class IoTRequestLog(Base):
    __tablename__ = "iot_request_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    idempotency_key = Column(String(64), nullable=True, index=True)
    request_body = Column(JSONB, nullable=True)
    status_code = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_iot_request_user", "user_id"),
        Index("ix_iot_request_endpoint", "endpoint"),
        Index("ix_iot_request_created", "created_at"),
        Index("ix_iot_request_idempotency", "idempotency_key"),
    )