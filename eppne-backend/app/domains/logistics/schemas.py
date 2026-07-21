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


# ============================================================
# 1. المخازن (Warehouses)
# ============================================================

class WarehouseCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255, description="اسم المخزن")
    warehouse_type: WarehouseType = Field(description="نوع المخزن")
    location: str = Field(description="الموقع")
    gps_location: Optional[Dict[str, float]] = Field(default=None, description="الموقع الجغرافي")
    total_capacity_sqm: Decimal = Field(..., gt=0, description="السعة الإجمالية بالمتر المربع")
    total_capacity_units: int = Field(..., gt=0, description="السعة الإجمالية بالوحدات")
    manager_id: Optional[int] = Field(default=None, description="معرف المدير")


class WarehouseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, description="اسم المخزن")
    location: Optional[str] = Field(default=None, description="الموقع")
    gps_location: Optional[Dict[str, float]] = Field(default=None, description="الموقع الجغرافي")
    is_active: Optional[bool] = Field(default=None, description="هل المخزن نشط؟")
    manager_id: Optional[int] = Field(default=None, description="معرف المدير")


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
    zone_code: str = Field(..., min_length=1, max_length=50, description="رمز المنطقة")
    zone_type: str = Field(description="نوع المنطقة")
    capacity_units: int = Field(..., gt=0, description="سعة المنطقة بالوحدات")


class WarehouseZoneResponse(WarehouseZoneCreate):
    id: int
    tenant_id: int
    warehouse_id: int
    used_units: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# 2. المخزون (Inventory)
# ============================================================

class InventoryReceive(BaseModel):
    warehouse_id: int = Field(description="معرف المخزن")
    zone_id: Optional[int] = Field(default=None, description="معرف المنطقة")
    product_id: Optional[int] = Field(default=None, description="معرف المنتج")
    product_name: str = Field(..., min_length=1, description="اسم المنتج")
    product_sku: Optional[str] = Field(default=None, description="رمز المنتج")
    product_category: Optional[str] = Field(default=None, description="تصنيف المنتج")
    quantity: int = Field(..., gt=0, description="الكمية")
    unit: str = Field(default="UNIT", description="وحدة القياس")
    unit_price_mrusdt: Decimal = Field(default=Decimal("0.0"), description="سعر الوحدة")
    batch_number: Optional[str] = Field(default=None, description="رقم الدفعة")
    manufacture_date: Optional[datetime] = Field(default=None, description="تاريخ التصنيع")
    expiry_date: Optional[datetime] = Field(default=None, description="تاريخ الانتهاء")
    supplier_id: Optional[int] = Field(default=None, description="معرف المورد")
    source_order_id: Optional[int] = Field(default=None, description="معرف الطلب المصدر")
    reference_type: Optional[str] = Field(default=None, description="نوع المرجع")
    reference_id: Optional[int] = Field(default=None, description="معرف المرجع")

    @field_validator("expiry_date")
    @classmethod
    def validate_expiry(cls, v: Optional[datetime], info) -> Optional[datetime]:
        if v and "manufacture_date" in info.data:
            man_date = info.data.get("manufacture_date")
            if man_date and v <= man_date:
                raise ValueError("expiry_date must be after manufacture_date")
        return v


class InventoryIssue(BaseModel):
    inventory_item_id: int = Field(description="معرف عنصر المخزون")
    quantity: int = Field(..., gt=0, description="الكمية")
    destination_warehouse_id: Optional[int] = Field(default=None, description="معرف المخزن الوجهة")
    reference_type: Optional[str] = Field(default=None, description="نوع المرجع")
    reference_id: Optional[int] = Field(default=None, description="معرف المرجع")


class InventoryAdjust(BaseModel):
    new_quantity: int = Field(..., ge=0, description="الكمية الجديدة")
    note: Optional[str] = Field(default=None, description="ملاحظة")


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


# ============================================================
# 3. المعدات (Equipment)
# ============================================================

class EquipmentCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255, description="اسم المعدة")
    equipment_type: str = Field(description="نوع المعدة")
    serial_number: Optional[str] = Field(default=None, description="الرقم التسلسلي")
    manufacturer: Optional[str] = Field(default=None, description="الشركة المصنعة")
    model: Optional[str] = Field(default=None, description="الموديل")
    warehouse_id: Optional[int] = Field(default=None, description="معرف المخزن")
    current_location: Optional[str] = Field(default=None, description="الموقع الحالي")
    purchase_date: Optional[datetime] = Field(default=None, description="تاريخ الشراء")
    purchase_price_mrusdt: Decimal = Field(default=Decimal("0.0"), description="سعر الشراء")
    warranty_expiry: Optional[datetime] = Field(default=None, description="تاريخ انتهاء الضمان")
    smart_asset_id: Optional[int] = Field(default=None, description="معرف الأصل الذكي في قطاع IoT")


class EquipmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, description="اسم المعدة")
    status: Optional[EquipmentStatus] = Field(default=None, description="حالة المعدة")
    warehouse_id: Optional[int] = Field(default=None, description="معرف المخزن")
    current_location: Optional[str] = Field(default=None, description="الموقع الحالي")
    next_maintenance_date: Optional[datetime] = Field(default=None, description="تاريخ الصيانة القادمة")


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
    maintenance_type: str = Field(description="نوع الصيانة")
    description: str = Field(description="وصف الصيانة")
    cost_mrusdt: Decimal = Field(default=Decimal("0.0"), description="التكلفة")
    scheduled_date: Optional[datetime] = Field(default=None, description="تاريخ الصيانة المجدول")


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


# ============================================================
# 4. التنبؤ بالطلب (Forecasting)
# ============================================================

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


# ============================================================
# 5. إحصائيات (Stats)
# ============================================================

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