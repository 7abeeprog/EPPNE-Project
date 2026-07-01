# app/domains/manufacturing/schemas.py (الإصدار النهائي المتكامل)
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.manufacturing.models import FacilityType, ProductionStatus, ProductCategory, TrackingStatus

class ManufacturingFacilityCreate(BaseModel):
    name: str
    facility_type: FacilityType
    location_gps: Optional[Dict[str, float]] = None
    real_estate_unit_id: Optional[int] = None

class ManufacturingFacilityResponse(ManufacturingFacilityCreate):
    id: int
    manager_id: int
    safety_compliance_score: float
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ProductionLineCreate(BaseModel):
    name: str
    hourly_capacity: int
    smart_asset_id: Optional[int] = None

class ProductionLineResponse(ProductionLineCreate):
    id: int
    facility_id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ProductBlueprintCreate(BaseModel):
    sku: str
    name: str
    product_category: ProductCategory
    description: Optional[str] = None
    bill_of_materials: Dict[str, Any] = {}
    base_price_mrusdt: Decimal
    is_perishable: bool = False
    shelf_life_days: Optional[int] = None
    warranty_months: Optional[int] = None
    has_digital_twin: bool = True

class ProductBlueprintResponse(ProductBlueprintCreate):
    id: int
    facility_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ProductionBatchCreate(BaseModel):
    product_blueprint_id: int
    line_id: int
    batch_number: str
    source_tracking_number: Optional[str] = None
    target_quantity: int

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
    qc_passed: bool
    item_metadata: Optional[Dict[str, Any]] = None

# ========== Supply Chain ==========
class RawMaterialBatchCreate(BaseModel):
    material_name: str
    supplier_id: Optional[int] = None
    source_traceability: Optional[str] = None
    quantity_kg: Decimal
    unit_price_mrusdt: Decimal
    received_date: datetime
    quality_check_passed: bool = True
    quality_certificate_hash: Optional[str] = None

class RawMaterialBatchResponse(RawMaterialBatchCreate):
    id: int
    total_cost_mrusdt: Decimal
    batch_number: str
    blockchain_tx_hash: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class MaterialConsumptionCreate(BaseModel):
    raw_material_batch_id: int
    quantity_used_kg: Decimal

# ========== Digital Twin ==========
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

# ========== Quality Certificates (مع التحقق من التواريخ) ==========
class QualityCertificateCreate(BaseModel):
    certificate_type: str
    certificate_name: str
    issuing_body: str
    certified_entity_type: str
    certified_entity_id: int
    issue_date: datetime
    expiry_date: datetime
    ipfs_document_hash: Optional[str] = None

    @field_validator("expiry_date")
    def validate_expiry_after_issue(cls, v, info):
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

# ========== Predictive Maintenance ==========
class PredictiveMaintenanceLogCreate(BaseModel):
    production_line_id: int
    sensor_data: Dict[str, Any]
    ai_prediction: Dict[str, Any]
    recommended_action: Optional[str] = None

class PredictiveMaintenanceLogResponse(PredictiveMaintenanceLogCreate):
    id: int
    status: str
    maintenance_scheduled_at: Optional[datetime]
    maintenance_completed_at: Optional[datetime]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SparePartCreate(BaseModel):
    part_name: str
    part_number: str
    compatible_machines: List[int] = []
    stock_quantity: int = 0
    min_stock_threshold: int = 5
    unit_price_mrusdt: Decimal
    supplier_id: Optional[int] = None

class SparePartResponse(SparePartCreate):
    id: int
    tenant_id: int
    last_restocked_at: Optional[datetime]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SparePartRestock(BaseModel):
    quantity_added: int
    unit_price_paid: Optional[Decimal] = None