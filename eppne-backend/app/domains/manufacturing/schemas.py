# app/domains/manufacturing/schemas.py (الإصدار النهائي المتكامل)
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.manufacturing.models import FacilityType, ProductionStatus, ProductCategory, TrackingStatus


# ============================================================
# المنشآت (Facilities)
# ============================================================

class ManufacturingFacilityCreate(BaseModel):
    name: str = Field(description="اسم المنشأة")
    facility_type: FacilityType = Field(description="نوع المنشأة")
    location_gps: Optional[Dict[str, float]] = Field(default=None, description="الموقع الجغرافي")
    real_estate_unit_id: Optional[int] = Field(default=None, description="معرف الوحدة العقارية")


class ManufacturingFacilityResponse(ManufacturingFacilityCreate):
    id: int
    manager_id: int
    safety_compliance_score: float
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# خطوط الإنتاج (Production Lines)
# ============================================================

class ProductionLineCreate(BaseModel):
    name: str = Field(description="اسم الخط")
    hourly_capacity: int = Field(description="السعة بالساعة")
    smart_asset_id: Optional[int] = Field(default=None, description="معرف الأصل الذكي")


class ProductionLineResponse(ProductionLineCreate):
    id: int
    facility_id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# النماذج (Blueprints)
# ============================================================

class ProductBlueprintCreate(BaseModel):
    sku: str = Field(description="رمز المنتج")
    name: str = Field(description="اسم المنتج")
    product_category: ProductCategory = Field(description="فئة المنتج")
    description: Optional[str] = Field(default=None, description="وصف المنتج")
    bill_of_materials: Dict[str, Any] = Field(default_factory=dict, description="قائمة المواد")
    base_price_mrusdt: Decimal = Field(description="السعر الأساسي")
    is_perishable: bool = Field(default=False, description="هل المنتج قابل للتلف؟")
    shelf_life_days: Optional[int] = Field(default=None, description="مدة الصلاحية بالأيام")
    warranty_months: Optional[int] = Field(default=None, description="مدة الضمان بالأشهر")
    has_digital_twin: bool = Field(default=True, description="هل له توأم رقمي؟")


class ProductBlueprintResponse(ProductBlueprintCreate):
    id: int
    facility_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# دفعات الإنتاج (Production Batches)
# ============================================================

class ProductionBatchCreate(BaseModel):
    product_blueprint_id: int = Field(description="معرف النموذج")
    line_id: int = Field(description="معرف خط الإنتاج")
    batch_number: str = Field(description="رقم الدفعة")
    source_tracking_number: Optional[str] = Field(default=None, description="رقم تتبع المصدر")
    target_quantity: int = Field(description="الكمية المستهدفة")


class ProductionBatchResponse(ProductionBatchCreate):
    id: int
    produced_quantity: int
    status: ProductionStatus
    quality_control_notes: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class StartProductionResponse(BaseModel):
    message: str
    batch_number: str
    items_generated: int
    status: str


# ============================================================
# المنتجات الذكية (Smart Product Items)
# ============================================================

class SmartProductItemResponse(BaseModel):
    id: int
    batch_id: int
    serial_number: str
    smart_barcode: str
    digital_twin_nft_id: Optional[str]
    item_metadata: Dict[str, Any]
    qc_passed: Optional[bool]
    expiration_date: Optional[datetime]
    status: TrackingStatus
    owner_id: Optional[int]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class QualityControlUpdate(BaseModel):
    qc_passed: bool = Field(description="هل اجتاز مراقبة الجودة؟")
    item_metadata: Optional[Dict[str, Any]] = Field(default=None, description="بيانات إضافية")


# ============================================================
# المواد الخام (Raw Materials)
# ============================================================

class RawMaterialBatchCreate(BaseModel):
    material_name: str = Field(description="اسم المادة")
    supplier_id: Optional[int] = Field(default=None, description="معرف المورد")
    source_traceability: Optional[str] = Field(default=None, description="تتبع المصدر")
    quantity_kg: Decimal = Field(description="الكمية بالكيلوغرام")
    unit_price_mrusdt: Decimal = Field(description="سعر الوحدة")
    received_date: datetime = Field(description="تاريخ الاستلام")
    quality_check_passed: bool = Field(default=True, description="هل اجتاز فحص الجودة؟")
    quality_certificate_hash: Optional[str] = Field(default=None, description="هاش شهادة الجودة")


class RawMaterialBatchResponse(RawMaterialBatchCreate):
    id: int
    total_cost_mrusdt: Decimal
    batch_number: str
    blockchain_tx_hash: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MaterialConsumptionCreate(BaseModel):
    raw_material_batch_id: int = Field(description="معرف دفعة المواد الخام")
    quantity_used_kg: Decimal = Field(description="الكمية المستخدمة بالكيلوغرام")


# ============================================================
# التوأم الرقمي (Digital Twin)
# ============================================================

class ProductDigitalTwinResponse(BaseModel):
    id: int
    product_item_id: int
    manufacturing_date: datetime
    batch_number: str
    production_line_id: Optional[int]
    actual_bom: Dict[str, Any]
    maintenance_log: List[Dict[str, Any]]
    total_maintenance_cost_mrusdt: Decimal
    quality_certificates: List[Dict[str, Any]]
    digital_twin_nft_id: Optional[str]
    ipfs_metadata_hash: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# شهادات الجودة (Quality Certificates)
# ============================================================

class QualityCertificateCreate(BaseModel):
    certificate_type: str = Field(description="نوع الشهادة")
    certificate_name: str = Field(description="اسم الشهادة")
    issuing_body: str = Field(description="جهة الإصدار")
    certified_entity_type: str = Field(description="نوع الكيان المعتمد")
    certified_entity_id: int = Field(description="معرف الكيان المعتمد")
    issue_date: datetime = Field(description="تاريخ الإصدار")
    expiry_date: datetime = Field(description="تاريخ الانتهاء")
    ipfs_document_hash: Optional[str] = Field(default=None, description="هاش مستند IPFS")

    @field_validator("expiry_date")
    @classmethod
    def validate_expiry_after_issue(cls, v: datetime, info) -> datetime:
        issue = info.data.get("issue_date")
        if issue and v <= issue:
            raise ValueError("expiry_date must be after issue_date")
        return v


class QualityCertificateResponse(QualityCertificateCreate):
    id: int
    tenant_id: int
    status: str
    certificate_nft_id: Optional[str]
    created_by: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# الصيانة التنبؤية (Predictive Maintenance)
# ============================================================

class PredictiveMaintenanceLogCreate(BaseModel):
    production_line_id: int = Field(description="معرف خط الإنتاج")
    sensor_data: Dict[str, Any] = Field(description="بيانات المستشعرات")
    ai_prediction: Dict[str, Any] = Field(description="توقع الذكاء الاصطناعي")
    recommended_action: Optional[str] = Field(default=None, description="الإجراء الموصى به")


class PredictiveMaintenanceLogResponse(PredictiveMaintenanceLogCreate):
    id: int
    status: str
    maintenance_scheduled_at: Optional[datetime]
    maintenance_completed_at: Optional[datetime]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# قطع الغيار (Spare Parts)
# ============================================================

class SparePartCreate(BaseModel):
    part_name: str = Field(description="اسم القطعة")
    part_number: str = Field(description="رقم القطعة")
    compatible_machines: List[int] = Field(default_factory=list, description="الآلات المتوافقة")
    stock_quantity: int = Field(default=0, description="الكمية في المخزون")
    min_stock_threshold: int = Field(default=5, description="الحد الأدنى للمخزون")
    unit_price_mrusdt: Decimal = Field(description="سعر الوحدة")
    supplier_id: Optional[int] = Field(default=None, description="معرف المورد")


class SparePartResponse(SparePartCreate):
    id: int
    tenant_id: int
    last_restocked_at: Optional[datetime]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SparePartRestock(BaseModel):
    quantity_added: int = Field(description="الكمية المضافة")
    unit_price_paid: Optional[Decimal] = Field(default=None, description="سعر الوحدة المدفوع")