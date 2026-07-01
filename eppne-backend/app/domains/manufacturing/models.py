from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, JSON, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class FacilityType(str, enum.Enum):
    HEAVY_FACTORY = "HEAVY_FACTORY"
    ASSEMBLY_LINE = "ASSEMBLY_LINE"
    BIO_REFINERY = "BIO_REFINERY"
    FARM_PROCESSING = "FARM_PROCESSING"

class ProductionStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    QC_TESTING = "QC_TESTING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"

class ProductCategory(str, enum.Enum):
    FOOD_AND_BEVERAGE = "FOOD_AND_BEVERAGE"
    AUTOMOTIVE = "AUTOMOTIVE"
    ELECTRONICS = "ELECTRONICS"
    ROBOTICS_AI = "ROBOTICS_AI"
    TEXTILES_APPAREL = "TEXTILES_APPAREL"
    TOYS_AND_GAMES = "TOYS_AND_GAMES"
    HOME_APPLIANCES = "HOME_APPLIANCES"
    OFFICE_SUPPLIES = "OFFICE_SUPPLIES"
    HEAVY_MACHINERY = "HEAVY_MACHINERY"
    SMART_BIO_UNITS = "SMART_BIO_UNITS"

class TrackingStatus(str, enum.Enum):
    IN_FACTORY = "IN_FACTORY"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    RECALLED = "RECALLED"

# ========== المنشآت الصناعية ==========
class ManufacturingFacility(Base):
    __tablename__ = "manufacturing_facilities"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    real_estate_unit_id = Column(Integer, ForeignKey("property_units.id"), nullable=True, index=True)  # ربط بالعقار
    entity_id = Column(Integer, nullable=False, index=True) # تم تأجيل الـ ForeignKey
    name = Column(String(255), nullable=False)
    facility_type = Column(SQLEnum(FacilityType), nullable=False)
    location_gps = Column(JSON, nullable=True)

    manager_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    safety_compliance_score = Column(Numeric(5, 2), default=100.0)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)


class ProductionLine(Base):
    __tablename__ = "production_lines"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("manufacturing_facilities.id"), nullable=False, index=True)
    smart_asset_id = Column(Integer, ForeignKey("smart_assets.id"), nullable=True)  # رصد IoT

    name = Column(String(100), nullable=False)
    hourly_capacity = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ProductBlueprint(Base):
    __tablename__ = "product_blueprints"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    facility_id = Column(Integer, ForeignKey("manufacturing_facilities.id"), nullable=False, index=True)

    sku = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    product_category = Column(SQLEnum(ProductCategory), nullable=False)
    description = Column(Text, nullable=True)

    bill_of_materials = Column(JSON, default=dict)  # المواد الخام المطلوبة
    base_price_mrusdt = Column(Numeric(15, 2), nullable=False)

    is_perishable = Column(Boolean, default=False)
    shelf_life_days = Column(Integer, nullable=True)
    warranty_months = Column(Integer, nullable=True)
    has_digital_twin = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ProductionBatch(Base):
    __tablename__ = "production_batches"

    id = Column(Integer, primary_key=True, index=True)
    product_blueprint_id = Column(Integer, ForeignKey("product_blueprints.id"), nullable=False, index=True)
    line_id = Column(Integer, ForeignKey("production_lines.id"), nullable=False, index=True)

    batch_number = Column(String(100), unique=True, index=True, nullable=False)
    source_tracking_number = Column(String(100), nullable=True)  # تتبع المواد الخام

    target_quantity = Column(Integer, nullable=False)
    produced_quantity = Column(Integer, default=0)
    status = Column(SQLEnum(ProductionStatus), default=ProductionStatus.PLANNED)
    quality_control_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SmartProductItem(Base):
    __tablename__ = "smart_product_items"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("production_batches.id"), nullable=False, index=True)

    serial_number = Column(String(100), unique=True, index=True, nullable=False)
    smart_barcode = Column(String(255), unique=True, index=True, nullable=False)  # QR/NFC
    digital_twin_nft_id = Column(String(100), unique=True, nullable=True)

    item_metadata = Column(JSON, default=dict)  # خصائص فردية (لون، مقاس، مواصفات)
    qc_passed = Column(Boolean, nullable=True)
    expiration_date = Column(DateTime(timezone=True), nullable=True)

    status = Column(SQLEnum(TrackingStatus), default=TrackingStatus.IN_FACTORY)
    current_location = Column(String(255), nullable=True)
    owner_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # ========== توسعة التصنيع: سلسلة الإمداد الصناعية ==========
class RawMaterialBatch(Base):
    __tablename__ = "raw_material_batches"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    material_name = Column(String(255), nullable=False)
    supplier_id = Column(Integer, ForeignKey("financial_partners.id"), nullable=True)
    source_traceability = Column(String(255), nullable=True)  # من زراعة، منجم، إلخ

    quantity_kg = Column(Numeric(15, 2), nullable=False)
    unit_price_mrusdt = Column(Numeric(30, 8), nullable=False)
    total_cost_mrusdt = Column(Numeric(30, 8), nullable=False)

    received_date = Column(DateTime(timezone=True), nullable=False)
    quality_check_passed = Column(Boolean, default=True)
    quality_certificate_hash = Column(String(100), nullable=True)

    batch_number = Column(String(100), unique=True, nullable=False)
    blockchain_tx_hash = Column(String(100), nullable=True)   # تسجيل على السلسلة

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)


class MaterialConsumptionLog(Base):
    __tablename__ = "material_consumption_logs"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("production_batches.id"), nullable=False, index=True)
    raw_material_batch_id = Column(Integer, ForeignKey("raw_material_batches.id"), nullable=False, index=True)
    quantity_used_kg = Column(Numeric(15, 2), nullable=False)

    consumed_at = Column(DateTime(timezone=True), server_default=func.now())
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    blockchain_tx_hash = Column(String(100), nullable=True)


# ========== توسعة التصنيع: التوأم الرقمي للمنتج ==========
class ProductDigitalTwin(Base):
    __tablename__ = "product_digital_twins"

    id = Column(Integer, primary_key=True, index=True)
    product_item_id = Column(Integer, ForeignKey("smart_product_items.id"), unique=True, nullable=False, index=True)

    # التاريخ الكامل للمنتج
    manufacturing_date = Column(DateTime(timezone=True), nullable=False)
    batch_number = Column(String(100), nullable=False)
    production_line_id = Column(Integer, ForeignKey("production_lines.id"), nullable=True)

    # خريطة الأجزاء المكونة (Bill of Materials الفعلية لهذه القطعة)
    actual_bom = Column(JSON, default=dict)   # {"raw_material_1": "2kg", "component_2": "1pc"}

    # سجل الصيانة
    maintenance_log = Column(JSON, default=list)   # قائمة بأحداث الصيانة والإصلاحات
    total_maintenance_cost_mrusdt = Column(Numeric(30, 8), default=0)

    # شهادات المنتج
    quality_certificates = Column(JSON, default=list)   # قائمة بـ NFTs

    # التوثيق
    digital_twin_nft_id = Column(String(100), unique=True, nullable=True)  # المنتج كـ NFT
    ipfs_metadata_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ========== توسعة التصنيع: شهادات الجودة ==========
class QualityCertificate(Base):
    __tablename__ = "quality_certificates"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    certificate_type = Column(String(50), nullable=False)   # ISO9001, CE, FDA, HALAL, ORGANIC
    certificate_name = Column(String(255), nullable=False)
    issuing_body = Column(String(255), nullable=False)

    # الجهة الحاصلة على الشهادة (مصنع، منتج، دفعة إنتاج)
    certified_entity_type = Column(String(50), nullable=False)  # MANUFACTURING_FACILITY, PRODUCT, PRODUCT_BATCH
    certified_entity_id = Column(Integer, nullable=False, index=True)

    issue_date = Column(DateTime(timezone=True), nullable=False)
    expiry_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="ACTIVE")

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


# ========== توسعة التصنيع: الصيانة التنبؤية ==========
class PredictiveMaintenanceLog(Base):
    __tablename__ = "predictive_maintenance_logs"

    id = Column(Integer, primary_key=True, index=True)
    production_line_id = Column(Integer, ForeignKey("production_lines.id"), nullable=False, index=True)

    # قراءات المستشعرات
    sensor_data = Column(JSON, nullable=False)   # {temperature: 85, vibration: 0.2, rpm: 1450}
    ai_prediction = Column(JSON, nullable=False)  # {failure_probability: 0.7, expected_remaining_hours: 120}
    recommended_action = Column(Text, nullable=True)

    status = Column(String(50), default="PENDING")  # PENDING, SCHEDULED, COMPLETED
    maintenance_scheduled_at = Column(DateTime(timezone=True), nullable=True)
    maintenance_completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SparePart(Base):
    __tablename__ = "spare_parts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    part_name = Column(String(255), nullable=False)
    part_number = Column(String(100), unique=True, nullable=False)
    compatible_machines = Column(JSON, default=list)   # قائمة بمعرفات خطوط الإنتاج المتوافقة

    stock_quantity = Column(Integer, default=0)
    min_stock_threshold = Column(Integer, default=5)
    unit_price_mrusdt = Column(Numeric(30, 8), nullable=False)

    supplier_id = Column(Integer, ForeignKey("financial_partners.id"), nullable=True)
    last_restocked_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)# app/domains/manufacturing/models.py (الإصدار النهائي المتكامل)
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, JSON, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class FacilityType(str, enum.Enum):
    HEAVY_FACTORY = "HEAVY_FACTORY"
    ASSEMBLY_LINE = "ASSEMBLY_LINE"
    BIO_REFINERY = "BIO_REFINERY"
    FARM_PROCESSING = "FARM_PROCESSING"

class ProductionStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    QC_TESTING = "QC_TESTING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"

class ProductCategory(str, enum.Enum):
    FOOD_AND_BEVERAGE = "FOOD_AND_BEVERAGE"
    AUTOMOTIVE = "AUTOMOTIVE"
    ELECTRONICS = "ELECTRONICS"
    ROBOTICS_AI = "ROBOTICS_AI"
    TEXTILES_APPAREL = "TEXTILES_APPAREL"
    TOYS_AND_GAMES = "TOYS_AND_GAMES"
    HOME_APPLIANCES = "HOME_APPLIANCES"
    OFFICE_SUPPLIES = "OFFICE_SUPPLIES"
    HEAVY_MACHINERY = "HEAVY_MACHINERY"
    SMART_BIO_UNITS = "SMART_BIO_UNITS"

class TrackingStatus(str, enum.Enum):
    IN_FACTORY = "IN_FACTORY"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    RECALLED = "RECALLED"

# ========== المنشآت الصناعية ==========
class ManufacturingFacility(Base):
    __tablename__ = "manufacturing_facilities"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    real_estate_unit_id = Column(Integer, ForeignKey("property_units.id"), nullable=True, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    facility_type = Column(SQLEnum(FacilityType), nullable=False)
    location_gps = Column(JSON, nullable=True)

    manager_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    safety_compliance_score = Column(Numeric(5, 2), default=100.0)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

# ========== خطوط الإنتاج (مع Multi-Tenancy) ==========
class ProductionLine(Base):
    __tablename__ = "production_lines"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    facility_id = Column(Integer, ForeignKey("manufacturing_facilities.id"), nullable=False, index=True)
    smart_asset_id = Column(Integer, ForeignKey("smart_assets.id"), nullable=True)

    name = Column(String(100), nullable=False)
    hourly_capacity = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_prodline_tenant_facility", "tenant_id", "facility_id"),
    )

# ========== النماذج/المنتجات ==========
class ProductBlueprint(Base):
    __tablename__ = "product_blueprints"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    facility_id = Column(Integer, ForeignKey("manufacturing_facilities.id"), nullable=False, index=True)

    sku = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    product_category = Column(SQLEnum(ProductCategory), nullable=False)
    description = Column(Text, nullable=True)

    bill_of_materials = Column(JSON, default=dict)
    base_price_mrusdt = Column(Numeric(15, 2), nullable=False)

    is_perishable = Column(Boolean, default=False)
    shelf_life_days = Column(Integer, nullable=True)
    warranty_months = Column(Integer, nullable=True)
    has_digital_twin = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# ========== دفعات الإنتاج (مع Multi-Tenancy + Idempotency) ==========
class ProductionBatch(Base):
    __tablename__ = "production_batches"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    product_blueprint_id = Column(Integer, ForeignKey("product_blueprints.id"), nullable=False, index=True)
    line_id = Column(Integer, ForeignKey("production_lines.id"), nullable=False, index=True)

    batch_number = Column(String(100), unique=True, index=True, nullable=False)
    source_tracking_number = Column(String(100), nullable=True)

    target_quantity = Column(Integer, nullable=False)
    produced_quantity = Column(Integer, default=0)
    status = Column(SQLEnum(ProductionStatus), default=ProductionStatus.PLANNED)
    quality_control_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_batch_tenant_line", "tenant_id", "line_id"),
    )

# ========== المنتجات النهائية (مع Multi-Tenancy) ==========
class SmartProductItem(Base):
    __tablename__ = "smart_product_items"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    batch_id = Column(Integer, ForeignKey("production_batches.id"), nullable=False, index=True)

    serial_number = Column(String(100), unique=True, index=True, nullable=False)
    smart_barcode = Column(String(255), unique=True, index=True, nullable=False)
    digital_twin_nft_id = Column(String(100), unique=True, nullable=True)

    item_metadata = Column(JSON, default=dict)
    qc_passed = Column(Boolean, nullable=True)
    expiration_date = Column(DateTime(timezone=True), nullable=True)

    status = Column(SQLEnum(TrackingStatus), default=TrackingStatus.IN_FACTORY)
    current_location = Column(String(255), nullable=True)
    owner_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_product_tenant_batch", "tenant_id", "batch_id"),
    )

# ========== المواد الخام (مع Idempotency) ==========
class RawMaterialBatch(Base):
    __tablename__ = "raw_material_batches"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد

    material_name = Column(String(255), nullable=False)
    supplier_id = Column(Integer, ForeignKey("financial_partners.id"), nullable=True)
    source_traceability = Column(String(255), nullable=True)

    quantity_kg = Column(Numeric(15, 2), nullable=False)
    unit_price_mrusdt = Column(Numeric(30, 8), nullable=False)
    total_cost_mrusdt = Column(Numeric(30, 8), nullable=False)

    received_date = Column(DateTime(timezone=True), nullable=False)
    quality_check_passed = Column(Boolean, default=True)
    quality_certificate_hash = Column(String(100), nullable=True)

    batch_number = Column(String(100), unique=True, nullable=False)
    blockchain_tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_raw_tenant", "tenant_id"),
    )

# ========== استهلاك المواد (مع Multi-Tenancy + Idempotency) ==========
class MaterialConsumptionLog(Base):
    __tablename__ = "material_consumption_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    batch_id = Column(Integer, ForeignKey("production_batches.id"), nullable=False, index=True)
    raw_material_batch_id = Column(Integer, ForeignKey("raw_material_batches.id"), nullable=False, index=True)
    quantity_used_kg = Column(Numeric(15, 2), nullable=False)

    consumed_at = Column(DateTime(timezone=True), server_default=func.now())
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    blockchain_tx_hash = Column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_consumption_tenant_batch", "tenant_id", "batch_id"),
    )

# ========== التوأم الرقمي للمنتج (مع Multi-Tenancy) ==========
class ProductDigitalTwin(Base):
    __tablename__ = "product_digital_twins"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    product_item_id = Column(Integer, ForeignKey("smart_product_items.id"), unique=True, nullable=False, index=True)

    manufacturing_date = Column(DateTime(timezone=True), nullable=False)
    batch_number = Column(String(100), nullable=False)
    production_line_id = Column(Integer, ForeignKey("production_lines.id"), nullable=True)

    actual_bom = Column(JSON, default=dict)
    maintenance_log = Column(JSON, default=list)
    total_maintenance_cost_mrusdt = Column(Numeric(30, 8), default=0)

    quality_certificates = Column(JSON, default=list)
    digital_twin_nft_id = Column(String(100), unique=True, nullable=True)
    ipfs_metadata_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_digitaltwin_tenant_product", "tenant_id", "product_item_id"),
    )

# ========== شهادات الجودة ==========
class QualityCertificate(Base):
    __tablename__ = "quality_certificates"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    certificate_type = Column(String(50), nullable=False)
    certificate_name = Column(String(255), nullable=False)
    issuing_body = Column(String(255), nullable=False)

    certified_entity_type = Column(String(50), nullable=False)
    certified_entity_id = Column(Integer, nullable=False, index=True)

    issue_date = Column(DateTime(timezone=True), nullable=False)
    expiry_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="ACTIVE")

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

# ========== الصيانة التنبؤية (مع Multi-Tenancy) ==========
class PredictiveMaintenanceLog(Base):
    __tablename__ = "predictive_maintenance_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    production_line_id = Column(Integer, ForeignKey("production_lines.id"), nullable=False, index=True)

    sensor_data = Column(JSON, nullable=False)
    ai_prediction = Column(JSON, nullable=False)
    recommended_action = Column(Text, nullable=True)

    status = Column(String(50), default="PENDING")
    maintenance_scheduled_at = Column(DateTime(timezone=True), nullable=True)
    maintenance_completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_maintenance_tenant_line", "tenant_id", "production_line_id"),
    )

# ========== قطع الغيار ==========
class SparePart(Base):
    __tablename__ = "spare_parts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    part_name = Column(String(255), nullable=False)
    part_number = Column(String(100), unique=True, nullable=False)
    compatible_machines = Column(JSON, default=list)

    stock_quantity = Column(Integer, default=0)
    min_stock_threshold = Column(Integer, default=5)
    unit_price_mrusdt = Column(Numeric(30, 8), nullable=False)

    supplier_id = Column(Integer, ForeignKey("financial_partners.id"), nullable=True)
    last_restocked_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)