# app/domains/iot/schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from app.domains.iot.models import AssetClass, UtilityType, GridStationType, DeviceHealthStatus


# ============================================================
# SmartAsset
# ============================================================

class SmartAssetCreate(BaseModel):
    entity_id: Optional[int] = Field(default=None, description="معرف الكيان")
    asset_code: str = Field(description="رمز الأصل")
    asset_class: AssetClass = Field(description="فئة الأصل")
    location_gps: Optional[Dict[str, float]] = Field(default=None, description="الموقع الجغرافي")
    specs: Dict[str, Any] = Field(default_factory=dict, description="المواصفات")
    hardware_did: Optional[str] = Field(default=None, description="معرف الأجهزة")
    iot_wallet_address: Optional[str] = Field(default=None, description="عنوان محفظة IoT")


class SmartAssetUpdate(BaseModel):
    location_gps: Optional[Dict[str, float]] = Field(default=None, description="الموقع الجغرافي")
    specs: Optional[Dict[str, Any]] = Field(default=None, description="المواصفات")
    is_online: Optional[bool] = Field(default=None, description="هل الجهاز متصل؟")
    health_status: Optional[DeviceHealthStatus] = Field(default=None, description="حالة الصحة")


class SmartAssetResponse(SmartAssetCreate):
    id: int
    owner_id: Optional[int]
    is_online: bool
    health_status: DeviceHealthStatus
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# UtilityGrid
# ============================================================

class UtilityGridCreate(BaseModel):
    development_id: Optional[int] = Field(default=None, description="معرف التطوير")
    entity_id: Optional[int] = Field(default=None, description="معرف الكيان")
    name: str = Field(description="اسم المحطة")
    grid_type: GridStationType = Field(description="نوع المحطة")
    max_capacity: Decimal = Field(description="السعة القصوى")


class UtilityGridResponse(UtilityGridCreate):
    id: int
    current_load: Decimal
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# UtilityReading
# ============================================================

class UtilityReadingCreate(BaseModel):
    grid_id: Optional[int] = Field(default=None, description="معرف المحطة")
    asset_id: Optional[int] = Field(default=None, description="معرف الأصل")
    reading_type: UtilityType = Field(description="نوع القراءة")
    consumed_value: Decimal = Field(default=Decimal("0.0"), description="القيمة المستهلكة")
    produced_value: Decimal = Field(default=Decimal("0.0"), description="القيمة المنتجة")
    carbon_emissions_mt: Optional[Decimal] = Field(default=None, description="انبعاثات الكربون (تُحسب تلقائياً)")  # type: ignore
    carbon_credits_generated: Optional[Decimal] = Field(default=None, description="أرصدة الكربون (تُحسب تلقائياً)")  # type: ignore


class UtilityReadingResponse(UtilityReadingCreate):
    id: int
    reading_timestamp: datetime
    carbon_emissions_mt: Decimal  # type: ignore
    carbon_credits_generated: Decimal  # type: ignore
    is_settled_on_chain: bool
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# MaintenanceLog
# ============================================================

class MaintenanceLogCreate(BaseModel):
    asset_id: Optional[int] = Field(default=None, description="معرف الأصل")
    grid_id: Optional[int] = Field(default=None, description="معرف المحطة")
    maintenance_type: str = Field(description="نوع الصيانة")
    task_description: str = Field(description="وصف المهمة")
    cost_mrusdt: Decimal = Field(default=Decimal("0.0"), description="التكلفة")
    time_credits_spent: Decimal = Field(default=Decimal("0.0"), description="الوقت المستغرق")


class MaintenanceLogResponse(MaintenanceLogCreate):
    id: int
    technician_id: Optional[int]
    is_resolved: bool
    resolution_date: Optional[datetime]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# عمليات تسييل الكربون
# ============================================================

class CarbonSettlementRequest(BaseModel):
    asset_ids: Optional[List[int]] = Field(default=None, description="معرفات الأصول (إذا ترك فارغاً، يتم تسييل الكل)")