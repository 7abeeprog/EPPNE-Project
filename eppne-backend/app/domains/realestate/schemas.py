# app/domains/realestate/schemas.py (الإصدار النهائي المتكامل مع جميع الإضافات)
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.realestate.models import ZoningCategory, LegalStatus, ConstructionStatus, PropertyType
import re

# ========== Land Assets ==========
class LandAssetCreate(BaseModel):
    plot_number: str
    area_sqm: Decimal
    gps_polygon: Dict[str, Any]
    zoning: ZoningCategory
    legal_status: LegalStatus
    current_value_mrusdt: Decimal = 0
    has_insurance: bool = False

class LandAssetResponse(LandAssetCreate):
    id: int
    parent_id: Optional[int]
    owner_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Developments ==========
class DevelopmentCreate(BaseModel):
    land_asset_id: int
    name: str
    development_type: str
    total_budget_mrusdt: Decimal = 0

class DevelopmentResponse(DevelopmentCreate):
    id: int
    construction_status: ConstructionStatus
    spent_budget_mrusdt: Decimal
    completion_percentage: float
    bim_model_hash: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Property Units ==========
class PropertyUnitCreate(BaseModel):
    development_id: int
    unit_number: str
    floor_number: Optional[int] = None
    area_sqm: Decimal
    property_type: PropertyType
    sale_price_mrusdt: Optional[Decimal] = None
    rent_per_month_mrusdt: Optional[Decimal] = None
    smart_asset_id: Optional[int] = None

class PropertyUnitResponse(PropertyUnitCreate):
    id: int
    is_available_for_sale: bool
    is_available_for_rent: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Ownership ==========
class BuyFractionalOwnership(BaseModel):
    ownership_percentage: Decimal = Field(..., gt=0, le=100)

class OwnershipResponse(BaseModel):
    id: int
    unit_id: int
    owner_user_id: int
    ownership_percentage: float
    acquisition_date: datetime
    deed_nft_token_id: Optional[str]
    purchase_tx_hash: Optional[str]
    model_config = ConfigDict(from_attributes=True)

# ========== Rental ==========
class RentalContractCreate(BaseModel):
    unit_id: int
    tenant_user_id: int
    start_date: datetime
    end_date: datetime
    monthly_rent_mrusdt: Decimal

class RentalContractResponse(RentalContractCreate):
    id: int
    landlord_user_id: int
    status: str
    contract_tx_hash: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Master Plan (جديد) ==========
class MasterPlanCreate(BaseModel):
    land_asset_id: int
    name: str
    description: Optional[str] = None
    gis_data: Optional[Dict[str, Any]] = None
    bim_model_hash: Optional[str] = None
    total_units_planned: int = 0
    total_area_sqm: Decimal

    @field_validator("gis_data")
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
    def validate_bim_hash(cls, v):
        if v is None:
            return v
        if not re.match(r'^[a-fA-F0-9]{64}$', v):
            raise ValueError("BIM model hash must be a valid 64-character hex string")
        return v

class MasterPlanResponse(MasterPlanCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Tokenization (جديد) ==========
class TokenizationCreate(BaseModel):
    total_shares: int = Field(..., gt=0)
    share_price_mrusdt: Decimal = Field(..., gt=0)
    minimum_investment_shares: int = 1

class TokenizationResponse(TokenizationCreate):
    id: int
    unit_id: int
    is_active: bool
    is_fully_subscribed: bool
    smart_contract_address: Optional[str]
    token_symbol: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Smart Contract (جديد) ==========
class SmartContractCreate(BaseModel):
    contract_type: str  # SALE, RENTAL, MORTGAGE, LEASE
    reference_id: int
    contract_metadata: Dict[str, Any]

    @field_validator("contract_metadata")
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
    id: int
    blockchain_tx_hash: Optional[str]
    execution_status: str
    executed_at: Optional[datetime]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)