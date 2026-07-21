# app/domains/realestate/schemas.py
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.realestate.models import ZoningCategory, LegalStatus, ConstructionStatus, PropertyType
import re


# ========== Land Assets ==========
class LandAssetCreate(BaseModel):
    plot_number: str = Field(description="رقم القطعة")
    area_sqm: Decimal = Field(description="المساحة بالمتر المربع")
    gps_polygon: Dict[str, Any] = Field(description="بيانات GPS على شكل GeoJSON")
    zoning: ZoningCategory = Field(description="نوع التقسيم")
    legal_status: LegalStatus = Field(description="الوضع القانوني")
    current_value_mrusdt: Decimal = Field(default=Decimal('0.0'), description="القيمة الحالية")
    has_insurance: bool = Field(default=False, description="هل يوجد تأمين")

class LandAssetResponse(LandAssetCreate):
    id: int = Field(description="معرف الأصل")
    parent_id: Optional[int] = Field(default=None, description="معرف الأصل الأب")
    owner_id: int = Field(description="معرف المالك")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

# ========== Developments ==========
class DevelopmentCreate(BaseModel):
    land_asset_id: int = Field(description="معرف الأرض")
    name: str = Field(description="اسم المشروع")
    development_type: str = Field(description="نوع التطوير")
    total_budget_mrusdt: Decimal = Field(default=Decimal('0.0'), description="الميزانية الإجمالية")

class DevelopmentResponse(DevelopmentCreate):
    id: int = Field(description="معرف المشروع")
    construction_status: ConstructionStatus = Field(description="حالة البناء")
    spent_budget_mrusdt: Decimal = Field(description="المبلغ المنفق")
    completion_percentage: float = Field(description="نسبة الإنجاز")
    bim_model_hash: Optional[str] = Field(default=None, description="هاش نموذج BIM")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

# ========== Property Units ==========
class PropertyUnitCreate(BaseModel):
    development_id: int = Field(description="معرف المشروع التطويري")
    unit_number: str = Field(description="رقم الوحدة")
    floor_number: Optional[int] = Field(default=None, description="رقم الطابق")
    area_sqm: Decimal = Field(description="المساحة بالمتر المربع")
    property_type: PropertyType = Field(description="نوع الوحدة")
    sale_price_mrusdt: Optional[Decimal] = Field(default=None, description="سعر البيع")
    rent_per_month_mrusdt: Optional[Decimal] = Field(default=None, description="الإيجار الشهري")
    smart_asset_id: Optional[int] = Field(default=None, description="معرف الأصل الذكي المرتبط")

class PropertyUnitResponse(PropertyUnitCreate):
    id: int = Field(description="معرف الوحدة")
    is_available_for_sale: bool = Field(description="متاحة للبيع")
    is_available_for_rent: bool = Field(description="متاحة للإيجار")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

# ========== Ownership ==========
class BuyFractionalOwnership(BaseModel):
    ownership_percentage: Decimal = Field(..., gt=0, le=100, description="نسبة الملكية المطلوبة")

class OwnershipResponse(BaseModel):
    id: int = Field(description="معرف سجل الملكية")
    unit_id: int = Field(description="معرف الوحدة")
    owner_user_id: int = Field(description="معرف المالك")
    ownership_percentage: float = Field(description="نسبة الملكية")
    acquisition_date: datetime = Field(description="تاريخ الاستحواذ")
    deed_nft_token_id: Optional[str] = Field(default=None, description="معرف NFT للصك")
    purchase_tx_hash: Optional[str] = Field(default=None, description="هاش معاملة الشراء")
    model_config = ConfigDict(from_attributes=True)

# ========== Rental ==========
class RentalContractCreate(BaseModel):
    unit_id: int = Field(description="معرف الوحدة")
    tenant_user_id: int = Field(description="معرف المستأجر")
    start_date: datetime = Field(description="تاريخ بدء الإيجار")
    end_date: datetime = Field(description="تاريخ انتهاء الإيجار")
    monthly_rent_mrusdt: Decimal = Field(gt=0, description="الإيجار الشهري")

class RentalContractResponse(RentalContractCreate):
    id: int = Field(description="معرف العقد")
    landlord_user_id: int = Field(description="معرف المؤجر")
    status: str = Field(description="حالة العقد")
    contract_tx_hash: Optional[str] = Field(default=None, description="هاش معاملة العقد")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

# ========== Master Plan ==========
class MasterPlanCreate(BaseModel):
    land_asset_id: int = Field(description="معرف الأرض")
    name: str = Field(description="اسم المخطط")
    description: Optional[str] = Field(default=None, description="وصف المخطط")
    gis_data: Optional[Dict[str, Any]] = Field(default=None, description="بيانات GIS (GeoJSON)")
    bim_model_hash: Optional[str] = Field(default=None, description="هاش نموذج BIM")
    total_units_planned: int = Field(default=0, description="إجمالي الوحدات المخططة")
    total_area_sqm: Decimal = Field(description="المساحة الإجمالية للمخطط")

    @field_validator("gis_data")
    @classmethod
    def validate_gis_data(cls, v):
        if v is None:
            return v
        if not isinstance(v, dict):
            raise ValueError("GIS data must be a valid GeoJSON object")
        if "type" not in v or "coordinates" not in v:
            raise ValueError("GIS data must contain 'type' and 'coordinates'")
        if v["type"] not in ["Polygon", "MultiPolygon", "Point", "LineString"]:
            raise ValueError("Invalid GeoJSON type. Must be Polygon, MultiPolygon, Point, or LineString.")
        return v

    @field_validator("bim_model_hash")
    @classmethod
    def validate_bim_hash(cls, v):
        if v is None:
            return v
        if not re.match(r'^[a-fA-F0-9]{64}$', v):
            raise ValueError("BIM model hash must be a valid 64-character hex string")
        return v

class MasterPlanResponse(MasterPlanCreate):
    id: int = Field(description="معرف المخطط")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

# ========== Tokenization ==========
class TokenizationCreate(BaseModel):
    total_shares: int = Field(..., gt=0, description="إجمالي الأسهم")
    share_price_mrusdt: Decimal = Field(..., gt=0, description="سعر السهم")
    minimum_investment_shares: int = Field(default=1, description="الحد الأدنى للاستثمار بالأسهم")

class TokenizationResponse(TokenizationCreate):
    id: int = Field(description="معرف التجزئة")
    unit_id: int = Field(description="معرف الوحدة المرتبطة")
    is_active: bool = Field(description="نشط")
    is_fully_subscribed: bool = Field(description="هل اكتتب بالكامل")
    smart_contract_address: Optional[str] = Field(default=None, description="عنوان العقد الذكي")
    token_symbol: Optional[str] = Field(default=None, description="رمز التوكن")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

# ========== Smart Contract ==========
class SmartContractCreate(BaseModel):
    contract_type: str = Field(description="نوع العقد (SALE, RENTAL, MORTGAGE, LEASE)")
    reference_id: int = Field(description="معرف المرجع (مثلاً unit_id أو ownership_id)")
    contract_metadata: Dict[str, Any] = Field(description="بيانات العقد")

    @field_validator("contract_metadata")
    @classmethod
    def validate_contract_metadata(cls, v):
        if not isinstance(v, dict):
            raise ValueError("Contract metadata must be a valid JSON object")
        
        contract_type = v.get("contract_type")
        if contract_type == "SALE":
            required = ["price", "buyer", "seller"]
            for field in required:
                if field not in v:
                    raise ValueError(f"Sale contract requires '{field}' field")
        elif contract_type == "RENTAL":
            required = ["monthly_rent", "tenant", "landlord"]
            for field in required:
                if field not in v:
                    raise ValueError(f"Rental contract requires '{field}' field")
        elif contract_type == "MORTGAGE":
            required = ["loan_amount", "borrower", "lender", "interest_rate"]
            for field in required:
                if field not in v:
                    raise ValueError(f"Mortgage contract requires '{field}' field")
        elif contract_type == "LEASE":
            required = ["lease_amount", "lessee", "lessor", "duration_months"]
            for field in required:
                if field not in v:
                    raise ValueError(f"Lease contract requires '{field}' field")
        else:
            raise ValueError(f"Unsupported contract type: {contract_type}")
        
        return v

class SmartContractResponse(SmartContractCreate):
    id: int = Field(description="معرف العقد")
    blockchain_tx_hash: Optional[str] = Field(default=None, description="هاش المعاملة على البلوكشين")
    execution_status: str = Field(description="حالة التنفيذ (PENDING, CONFIRMED, FAILED)")
    executed_at: Optional[datetime] = Field(default=None, description="تاريخ التنفيذ")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)