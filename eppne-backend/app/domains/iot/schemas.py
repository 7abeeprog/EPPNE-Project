from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from app.domains.iot.models import AssetClass, UtilityType, GridStationType, DeviceHealthStatus

# ========== SmartAsset ==========
class SmartAssetCreate(BaseModel):
    entity_id: Optional[int] = None
    asset_code: str
    asset_class: AssetClass
    location_gps: Optional[Dict[str, float]] = None
    specs: Dict[str, Any] = {}
    hardware_did: Optional[str] = None
    iot_wallet_address: Optional[str] = None

class SmartAssetUpdate(BaseModel):
    location_gps: Optional[Dict[str, float]] = None
    specs: Optional[Dict[str, Any]] = None
    is_online: Optional[bool] = None
    health_status: Optional[DeviceHealthStatus] = None

class SmartAssetResponse(SmartAssetCreate):
    id: int
    owner_id: Optional[int]
    is_online: bool
    health_status: DeviceHealthStatus
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== UtilityGrid ==========
class UtilityGridCreate(BaseModel):
    development_id: Optional[int] = None
    entity_id: Optional[int] = None
    name: str
    grid_type: GridStationType
    max_capacity: Decimal

class UtilityGridResponse(UtilityGridCreate):
    id: int
    current_load: Decimal
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== UtilityReading ==========
class UtilityReadingCreate(BaseModel):
    grid_id: Optional[int] = None
    asset_id: Optional[int] = None
    reading_type: UtilityType
    consumed_value: Decimal = 0
    produced_value: Decimal = 0
    # الحقول التالية تُحسب آلياً في الخدمة
    carbon_emissions_mt: Optional[Decimal] = None
    carbon_credits_generated: Optional[Decimal] = None
    # يمكن إضافة idempotency_key اختياري هنا أو في الـ Header

class UtilityReadingResponse(UtilityReadingCreate):
    id: int
    reading_timestamp: datetime
    carbon_emissions_mt: Decimal
    carbon_credits_generated: Decimal
    is_settled_on_chain: bool
    model_config = ConfigDict(from_attributes=True)

# ========== MaintenanceLog ==========
class MaintenanceLogCreate(BaseModel):
    asset_id: Optional[int] = None
    grid_id: Optional[int] = None
    maintenance_type: str
    task_description: str
    cost_mrusdt: Decimal = 0
    time_credits_spent: Decimal = 0

class MaintenanceLogResponse(MaintenanceLogCreate):
    id: int
    technician_id: Optional[int]
    is_resolved: bool
    resolution_date: Optional[datetime]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== عمليات تسييل الكربون ==========
class CarbonSettlementRequest(BaseModel):
    asset_ids: Optional[List[int]] = None   # إذا ترك فارغاً، يتم تسييل كل الأرصدة غير المسواة
    # idempotency_key يمكن تمريره في الـ Header