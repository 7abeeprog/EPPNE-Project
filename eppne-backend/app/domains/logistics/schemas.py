# app/domains/logistics/schemas.py
"""
نماذج (Schemas) Pydantic لقطاع اللوجيستيات والمخازن
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.logistics.models import (
    WarehouseType, InventoryStatus, EquipmentStatus, TransactionType, OrderStatus
)


# ========================================================================
# 1. المخازن (Warehouses)
# ========================================================================

class WarehouseCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    warehouse_type: WarehouseType
    location: str
    gps_location: Optional[Dict[str, float]] = None
    total_capacity_sqm: Decimal = Field(..., gt=0)
    total_capacity_units: int = Field(..., gt=0)
    manager_id: Optional[int] = None


class WarehouseUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    gps_location: Optional[Dict[str, float]] = None
    is_active: Optional[bool] = None
    manager_id: Optional[int] = None


class WarehouseResponse(WarehouseCreate):
    id: int
    tenant_id: int
    used_capacity_sqm: Decimal
    used_capacity_units: int
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class WarehouseZoneCreate(BaseModel):
    zone_code: str = Field(..., min_length=1, max_length=50)
    zone_type: str
    capacity_units: int = Field(..., gt=0)


class WarehouseZoneResponse(WarehouseZoneCreate):
    id: int
    tenant_id: int
    warehouse_id: int
    used_units: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========================================================================
# 2. المخزون (Inventory)
# ========================================================================

class InventoryReceive(BaseModel):
    warehouse_id: int
    zone_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: str = Field(..., min_length=1)
    product_sku: Optional[str] = None
    product_category: Optional[str] = None
    quantity: int = Field(..., gt=0)
    unit: str = "UNIT"
    unit_price_mrusdt: Decimal = 0
    batch_number: Optional[str] = None
    manufacture_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    supplier_id: Optional[int] = None
    source_order_id: Optional[int] = None
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None

    @field_validator("expiry_date")
    def validate_expiry(cls, v, info):
        if v and "manufacture_date" in info.data:
            man_date = info.data.get("manufacture_date")
            if man_date and v <= man_date:
                raise ValueError("expiry_date must be after manufacture_date")
        return v


class InventoryIssue(BaseModel):
    inventory_item_id: int
    quantity: int = Field(..., gt=0)
    destination_warehouse_id: Optional[int] = None
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None


class InventoryAdjust(BaseModel):
    new_quantity: int = Field(..., ge=0)
    note: Optional[str] = None


class InventoryItemResponse(BaseModel):
    id: int
    tenant_id: int
    warehouse_id: int
    zone_id: Optional[int]
    product_id: Optional[int]
    product_name: str
    product_sku: Optional[str]
    product_category: Optional[str]
    quantity: int
    reserved_quantity: int
    min_stock_threshold: int
    max_stock_threshold: int
    unit: str
    unit_price_mrusdt: Decimal
    batch_number: Optional[str]
    manufacture_date: Optional[datetime]
    expiry_date: Optional[datetime]
    status: InventoryStatus
    supplier_id: Optional[int]
    source_order_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class InventoryTransactionResponse(BaseModel):
    id: int
    tenant_id: int
    inventory_item_id: int
    transaction_type: TransactionType
    quantity: int
    source_warehouse_id: Optional[int]
    destination_warehouse_id: Optional[int]
    reference_type: Optional[str]
    reference_id: Optional[int]
    notes: Optional[str]
    performed_by: int
    blockchain_tx_hash: Optional[str]
    document_url: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========================================================================
# 3. المعدات (Equipment)
# ========================================================================

class EquipmentCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    equipment_type: str
    serial_number: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    warehouse_id: Optional[int] = None
    current_location: Optional[str] = None
    purchase_date: Optional[datetime] = None
    purchase_price_mrusdt: Decimal = 0
    warranty_expiry: Optional[datetime] = None
    smart_asset_id: Optional[int] = None


class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[EquipmentStatus] = None
    warehouse_id: Optional[int] = None
    current_location: Optional[str] = None
    next_maintenance_date: Optional[datetime] = None


class EquipmentResponse(EquipmentCreate):
    id: int
    tenant_id: int
    status: EquipmentStatus
    last_maintenance_date: Optional[datetime]
    next_maintenance_date: Optional[datetime]
    created_by: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EquipmentMaintenanceCreate(BaseModel):
    maintenance_type: str
    description: str
    cost_mrusdt: Decimal = 0
    scheduled_date: Optional[datetime] = None


class EquipmentMaintenanceResponse(EquipmentMaintenanceCreate):
    id: int
    tenant_id: int
    equipment_id: int
    performed_by: Optional[int]
    completed_date: Optional[datetime]
    status: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========================================================================
# 4. التنبؤ بالطلب (Forecasting)
# ========================================================================

class InventoryForecastResponse(BaseModel):
    id: int
    tenant_id: int
    product_id: Optional[int]
    product_sku: Optional[str]
    forecast_period: str
    forecast_date: datetime
    predicted_demand: int
    confidence_score: float
    seasonality_factor: float
    trend_factor: float
    external_factors: Dict[str, Any]
    ai_agent_id: Optional[int]
    ai_model_version: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========================================================================
# 5. إحصائيات (Stats)
# ========================================================================

class LogisticsStatsResponse(BaseModel):
    total_warehouses: int
    active_warehouses: int
    total_inventory_items: int
    total_quantity: int
    total_value_mrusdt: Decimal
    low_stock_items: int
    expired_items: int
    total_equipment: int
    available_equipment: int
    model_config = ConfigDict(from_attributes=True)