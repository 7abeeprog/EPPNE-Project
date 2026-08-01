# app/domains/logistics/models.py
"""
نماذج (Models) قطاع اللوجيستيات والمخازن السيادية
يدعم: إدارة المخازن، المخزون، المعدات، الحركات، سلسلة التوريد، والتنبؤ بالطلب
"""
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB  # ✅ تم إضافة الاستيراد الصحيح
from sqlalchemy.sql import func
from app.core.database import Base
import enum


# ========== الأنواع المساعدة ==========
class WarehouseType(str, enum.Enum):
    CENTRAL = "CENTRAL"          # مخزن مركزي
    REGIONAL = "REGIONAL"        # مخزن إقليمي
    RETAIL = "RETAIL"            # مخزن تجزئة
    COLD_STORAGE = "COLD_STORAGE" # مخزن تبريد
    HAZARDOUS = "HAZARDOUS"      # مخزن مواد خطرة
    FARM = "FARM"                # مخزن زراعي


class InventoryStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"      # متوفر
    RESERVED = "RESERVED"        # محجوز
    DAMAGED = "DAMAGED"          # تالف
    EXPIRED = "EXPIRED"          # منتهي الصلاحية
    IN_TRANSIT = "IN_TRANSIT"    # قيد النقل


class EquipmentStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"      # متاح
    IN_USE = "IN_USE"            # قيد الاستخدام
    MAINTENANCE = "MAINTENANCE"  # صيانة
    DAMAGED = "DAMAGED"          # تالف
    RETIRED = "RETIRED"          # مخرج من الخدمة


class TransactionType(str, enum.Enum):
    RECEIVE = "RECEIVE"          # استلام
    ISSUE = "ISSUE"              # صرف
    TRANSFER = "TRANSFER"        # نقل بين المخازن
    ADJUSTMENT = "ADJUSTMENT"    # تعديل (جرد)
    RETURN = "RETURN"            # إرجاع


class OrderStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


# ========== 1. المخازن (Warehouses) ==========
class Warehouse(Base):
    __tablename__ = "logistics_warehouses"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)  # من قطاع الكيانات

    name = Column(String(255), nullable=False)
    warehouse_type = Column(SQLEnum(WarehouseType), nullable=False)
    location = Column(String(255), nullable=False)
    gps_location = Column(JSONB, nullable=True)

    total_capacity_sqm = Column(Numeric(15, 2), nullable=False)
    used_capacity_sqm = Column(Numeric(15, 2), default=0)
    total_capacity_units = Column(Integer, nullable=False)
    used_capacity_units = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_warehouse_tenant", "tenant_id"),
        Index("ix_warehouse_type", "warehouse_type"),
    )


class WarehouseZone(Base):
    __tablename__ = "logistics_warehouse_zones"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("logistics_warehouses.id"), nullable=False, index=True)

    zone_code = Column(String(50), nullable=False)
    zone_type = Column(String(50), nullable=False)  # SHELF, RACK, BULK, COLD, HAZARDOUS
    capacity_units = Column(Integer, nullable=False)
    used_units = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_warehouse_zone_tenant", "tenant_id"),
        Index("ix_warehouse_zone_warehouse", "warehouse_id"),
    )


# ========== 2. المخزون (Inventory) ==========
class InventoryItem(Base):
    __tablename__ = "logistics_inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    warehouse_id = Column(Integer, ForeignKey("logistics_warehouses.id"), nullable=False, index=True)
    zone_id = Column(Integer, ForeignKey("logistics_warehouse_zones.id"), nullable=True, index=True)

    product_id = Column(Integer, nullable=True, index=True)
    product_name = Column(String(255), nullable=False)
    product_sku = Column(String(100), nullable=True, index=True)
    product_category = Column(String(100), nullable=True)

    quantity = Column(Integer, nullable=False, default=0)
    reserved_quantity = Column(Integer, default=0)
    min_stock_threshold = Column(Integer, default=0)
    max_stock_threshold = Column(Integer, default=0)

    unit = Column(String(20), default="UNIT")  # UNIT, KG, L, BOX, PALLET
    unit_price_mrusdt = Column(Numeric(30, 8), default=0)

    batch_number = Column(String(100), nullable=True)
    manufacture_date = Column(DateTime(timezone=True), nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(SQLEnum(InventoryStatus), default=InventoryStatus.AVAILABLE)

    supplier_id = Column(Integer, nullable=True)
    source_order_id = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_inventory_tenant_warehouse", "tenant_id", "warehouse_id"),
        Index("ix_inventory_product", "product_id"),
        Index("ix_inventory_status", "status"),
        CheckConstraint("quantity >= 0", name="check_quantity_positive"),
        CheckConstraint("reserved_quantity <= quantity", name="check_reserved_not_exceed_quantity"),
    )


class InventoryTransaction(Base):
    __tablename__ = "logistics_inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    inventory_item_id = Column(Integer, ForeignKey("logistics_inventory_items.id"), nullable=False, index=True)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    quantity = Column(Integer, nullable=False)

    source_warehouse_id = Column(Integer, ForeignKey("logistics_warehouses.id"), nullable=True)
    destination_warehouse_id = Column(Integer, ForeignKey("logistics_warehouses.id"), nullable=True)

    reference_type = Column(String(50), nullable=True)
    reference_id = Column(Integer, nullable=True)

    notes = Column(Text, nullable=True)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    blockchain_tx_hash = Column(String(100), nullable=True)
    document_url = Column(String(512), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_transaction_tenant", "tenant_id"),
        Index("ix_transaction_inventory", "inventory_item_id"),
        Index("ix_transaction_type", "transaction_type"),
        Index("ix_transaction_created", "created_at"),
        CheckConstraint("quantity > 0", name="check_transaction_quantity_positive"),
    )


# ========== 3. المعدات (Equipment) ==========
class Equipment(Base):
    __tablename__ = "logistics_equipment"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    name = Column(String(255), nullable=False)
    equipment_type = Column(String(100), nullable=False)  # FORKLIFT, CRANE, CONVEYOR, VEHICLE, TOOL
    serial_number = Column(String(100), unique=True, nullable=True)
    manufacturer = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)

    warehouse_id = Column(Integer, ForeignKey("logistics_warehouses.id"), nullable=True, index=True)
    current_location = Column(String(255), nullable=True)

    purchase_date = Column(DateTime(timezone=True), nullable=True)
    purchase_price_mrusdt = Column(Numeric(30, 8), default=0)
    warranty_expiry = Column(DateTime(timezone=True), nullable=True)

    status = Column(SQLEnum(EquipmentStatus), default=EquipmentStatus.AVAILABLE)
    last_maintenance_date = Column(DateTime(timezone=True), nullable=True)
    next_maintenance_date = Column(DateTime(timezone=True), nullable=True)

    smart_asset_id = Column(Integer, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_equipment_tenant", "tenant_id"),
        Index("ix_equipment_status", "status"),
    )


class EquipmentMaintenance(Base):
    __tablename__ = "logistics_equipment_maintenance"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    equipment_id = Column(Integer, ForeignKey("logistics_equipment.id"), nullable=False, index=True)

    maintenance_type = Column(String(50), nullable=False)  # PREVENTIVE, CORRECTIVE, URGENT
    description = Column(Text, nullable=False)
    cost_mrusdt = Column(Numeric(30, 8), default=0)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    scheduled_date = Column(DateTime(timezone=True), nullable=True)
    completed_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="SCHEDULED")  # SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_maintenance_equipment", "equipment_id"),
        Index("ix_maintenance_tenant", "tenant_id"),
    )


# ========== 4. سلسلة التوريد (Supply Chain) ==========
class SupplyChainOrder(Base):
    __tablename__ = "logistics_supply_chain_orders"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    order_number = Column(String(100), unique=True, nullable=False)
    order_type = Column(String(50), nullable=False)  # PURCHASE, TRANSFER, RETURN

    supplier_id = Column(Integer, nullable=True)
    supplier_name = Column(String(255), nullable=True)
    destination_warehouse_id = Column(Integer, ForeignKey("logistics_warehouses.id"), nullable=False)

    expected_delivery_date = Column(DateTime(timezone=True), nullable=True)
    actual_delivery_date = Column(DateTime(timezone=True), nullable=True)

    status = Column(SQLEnum(OrderStatus), default=OrderStatus.DRAFT)
    total_amount_mrusdt = Column(Numeric(30, 8), default=0)

    invoice_id = Column(Integer, nullable=True)
    shipment_tracking_number = Column(String(100), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_order_tenant", "tenant_id"),
        Index("ix_order_status", "status"),
        Index("ix_order_number", "order_number"),
    )


class SupplyChainOrderItem(Base):
    __tablename__ = "logistics_supply_chain_order_items"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("logistics_supply_chain_orders.id"), nullable=False, index=True)

    product_id = Column(Integer, nullable=True)
    product_name = Column(String(255), nullable=False)
    product_sku = Column(String(100), nullable=True)

    quantity = Column(Integer, nullable=False)
    received_quantity = Column(Integer, default=0)
    unit_price_mrusdt = Column(Numeric(30, 8), default=0)
    total_price_mrusdt = Column(Numeric(30, 8), default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_order_item_order", "order_id"),
        Index("ix_order_item_tenant", "tenant_id"),
    )


# ========== 5. التنبؤ بالطلب (Forecasting - مع ترقية JSONB) ==========
class InventoryForecast(Base):
    __tablename__ = "logistics_inventory_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    product_id = Column(Integer, nullable=True)
    product_sku = Column(String(100), nullable=True)

    forecast_period = Column(String(20), nullable=False)  # DAILY, WEEKLY, MONTHLY
    forecast_date = Column(DateTime(timezone=True), nullable=False)
    predicted_demand = Column(Integer, nullable=False)
    confidence_score = Column(Numeric(5, 2), default=0)  # 0-100

    seasonality_factor = Column(Numeric(5, 2), default=1.0)
    trend_factor = Column(Numeric(5, 2), default=1.0)
    external_factors = Column(JSONB, default=dict)

    ai_agent_id = Column(Integer, nullable=True)
    ai_model_version = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_forecast_tenant", "tenant_id"),
        Index("ix_forecast_product", "product_id"),
        Index("ix_forecast_period", "forecast_period"),
    )