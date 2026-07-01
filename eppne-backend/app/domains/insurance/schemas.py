"""
نماذج (Schemas) Pydantic لقطاع التأمينات السيادية
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.insurance.models import PolicyType, PremiumCycle, ClaimStatus, PensionStatus


# ========== Insurance Policies ==========
class InsurancePolicyCreate(BaseModel):
    issuer_entity_id: int
    name: str = Field(..., min_length=3, max_length=255)
    policy_type: PolicyType
    description: Optional[str] = None
    base_premium_mrusdt: Decimal = Field(..., gt=0)
    premium_cycle: PremiumCycle = PremiumCycle.MONTHLY
    max_coverage_limit_mrusdt: Decimal = Field(..., gt=0)
    terms_and_conditions: Dict[str, Any] = {}
    smart_contract_address: Optional[str] = Field(None, pattern="^0x[a-fA-F0-9]{40}$")


class InsurancePolicyResponse(InsurancePolicyCreate):
    id: int
    tenant_id: int
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========== Insurance Subscriptions (مع التحقق من التواريخ) ==========
class InsuranceSubscriptionCreate(BaseModel):
    policy_id: int
    subscriber_user_id: Optional[int] = None
    fleet_id: Optional[int] = None
    land_asset_id: Optional[int] = None
    project_id: Optional[int] = None
    bio_asset_id: Optional[int] = None
    shipment_id: Optional[int] = None
    employment_contract_id: Optional[int] = None
    beneficiaries_json: Optional[Dict[str, Any]] = None
    start_date: datetime
    end_date: Optional[datetime] = None

    @field_validator("end_date")
    def validate_dates(cls, v, info):
        if v and "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v

    @field_validator("subscriber_user_id", "fleet_id", "land_asset_id", "project_id", "bio_asset_id", "shipment_id", "employment_contract_id")
    def validate_exclusive_target(cls, v, info):
        # التحقق من وجود هدف واحد فقط يتم في الـ model عبر CheckConstraint
        return v


class InsuranceSubscriptionResponse(InsuranceSubscriptionCreate):
    id: int
    status: str
    policy_nft_id: Optional[str]
    subscription_tx_hash: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========== Insurance Claims ==========
class InsuranceClaimCreate(BaseModel):
    subscription_id: int
    incident_date: datetime
    incident_description: str
    evidence_urls: List[str] = []
    claimed_amount_mrusdt: Decimal = Field(..., gt=0)


class InsuranceClaimUpdate(BaseModel):
    status: Optional[ClaimStatus] = None
    approved_amount_mrusdt: Optional[Decimal] = Field(None, ge=0)
    investigation_notes: Optional[str] = None
    oracle_verification_hash: Optional[str] = None


class InsuranceClaimResponse(InsuranceClaimCreate):
    id: int
    claimant_user_id: int
    approved_amount_mrusdt: Decimal
    status: ClaimStatus
    investigation_notes: Optional[str]
    oracle_verification_hash: Optional[str]
    payout_tx_hash: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========== Pensions ==========
class PensionRecordCreate(BaseModel):
    beneficiary_id: int
    source_entity_id: Optional[int] = None
    pension_type: str
    monthly_amount_mrusdt: Decimal = Field(..., gt=0)
    start_date: datetime
    end_date: Optional[datetime] = None


class PensionRecordResponse(PensionRecordCreate):
    id: int
    total_disbursed_mrusdt: Decimal
    status: PensionStatus
    streaming_contract_address: Optional[str]
    last_payout_tx: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========== Employee Insurance Profiles ==========
class EmployeeInsuranceProfileCreate(BaseModel):
    user_id: int
    government_insurance_number: str = Field(..., min_length=5, max_length=50)
    employee_share_percentage: Decimal = Field(..., ge=0, le=100)
    employer_share_percentage: Decimal = Field(..., ge=0, le=100)


class EmployeeInsuranceProfileResponse(EmployeeInsuranceProfileCreate):
    id: int
    total_contributed_mrusdt: Decimal
    last_contribution_date: Optional[datetime]
    status: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)