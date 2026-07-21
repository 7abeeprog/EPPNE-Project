"""
نماذج (Schemas) Pydantic لقطاع التأمينات السيادية
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.insurance.models import PolicyType, PremiumCycle, ClaimStatus, PensionStatus


# ============================================================
# بوالص التأمين (Insurance Policies)
# ============================================================

class InsurancePolicyCreate(BaseModel):
    issuer_entity_id: int = Field(description="معرف الكيان المصدر")
    name: str = Field(..., min_length=3, max_length=255, description="اسم البوليصة")
    policy_type: PolicyType = Field(description="نوع التأمين")
    description: Optional[str] = Field(default=None, description="وصف البوليصة")
    base_premium_mrusdt: Decimal = Field(..., gt=0, description="القسط الأساسي")
    premium_cycle: PremiumCycle = Field(default=PremiumCycle.MONTHLY, description="دورة القسط")
    max_coverage_limit_mrusdt: Decimal = Field(..., gt=0, description="الحد الأقصى للتغطية")
    terms_and_conditions: Dict[str, Any] = Field(default_factory=dict, description="الشروط والأحكام")
    smart_contract_address: Optional[str] = Field(
        default=None,
        pattern="^0x[a-fA-F0-9]{40}$",
        description="عنوان العقد الذكي"
    )


class InsurancePolicyResponse(InsurancePolicyCreate):
    id: int
    tenant_id: int
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# اشتراكات التأمين (Insurance Subscriptions)
# ============================================================

class InsuranceSubscriptionCreate(BaseModel):
    policy_id: int = Field(description="معرف البوليصة")
    subscriber_user_id: Optional[int] = Field(default=None, description="معرف المستخدم المشترك")
    fleet_id: Optional[int] = Field(default=None, description="معرف الأسطول")
    land_asset_id: Optional[int] = Field(default=None, description="معرف الأصل العقاري")
    project_id: Optional[int] = Field(default=None, description="معرف المشروع")
    bio_asset_id: Optional[int] = Field(default=None, description="معرف الأصل الحيوي")
    shipment_id: Optional[int] = Field(default=None, description="معرف الشحنة")
    employment_contract_id: Optional[int] = Field(default=None, description="معرف عقد العمل")
    beneficiaries_json: Optional[Dict[str, Any]] = Field(default=None, description="المستفيدون")
    start_date: datetime = Field(description="تاريخ البدء")
    end_date: Optional[datetime] = Field(default=None, description="تاريخ الانتهاء")

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v: Optional[datetime], info) -> Optional[datetime]:
        if v and "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class InsuranceSubscriptionResponse(InsuranceSubscriptionCreate):
    id: int
    status: str
    policy_nft_id: Optional[str] = None
    subscription_tx_hash: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# مطالبات التعويض (Insurance Claims)
# ============================================================

class InsuranceClaimCreate(BaseModel):
    subscription_id: int = Field(description="معرف الاشتراك")
    incident_date: datetime = Field(description="تاريخ الحادث")
    incident_description: str = Field(description="وصف الحادث")
    evidence_urls: List[str] = Field(default_factory=list, description="روابط الأدلة")
    claimed_amount_mrusdt: Decimal = Field(..., gt=0, description="المبلغ المطالب به")


class InsuranceClaimUpdate(BaseModel):
    status: Optional[ClaimStatus] = Field(default=None, description="حالة المطالبة")
    approved_amount_mrusdt: Optional[Decimal] = Field(default=None, ge=0, description="المبلغ المعتمد")
    investigation_notes: Optional[str] = Field(default=None, description="ملاحظات التحقيق")
    oracle_verification_hash: Optional[str] = Field(default=None, description="هاش التحقق من Oracle")


class InsuranceClaimResponse(InsuranceClaimCreate):
    id: int
    claimant_user_id: int
    approved_amount_mrusdt: Decimal
    status: ClaimStatus
    investigation_notes: Optional[str] = None
    oracle_verification_hash: Optional[str] = None
    payout_tx_hash: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# المعاشات (Pensions)
# ============================================================

class PensionRecordCreate(BaseModel):
    beneficiary_id: int = Field(description="معرف المستفيد")
    source_entity_id: Optional[int] = Field(default=None, description="معرف الكيان المصدر")
    pension_type: str = Field(description="نوع المعاش")
    monthly_amount_mrusdt: Decimal = Field(..., gt=0, description="المبلغ الشهري")
    start_date: datetime = Field(description="تاريخ البدء")
    end_date: Optional[datetime] = Field(default=None, description="تاريخ الانتهاء")


class PensionRecordResponse(PensionRecordCreate):
    id: int
    total_disbursed_mrusdt: Decimal
    status: PensionStatus
    streaming_contract_address: Optional[str] = None
    last_payout_tx: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# ملفات التأمين للموظفين (Employee Insurance Profiles)
# ============================================================

class EmployeeInsuranceProfileCreate(BaseModel):
    user_id: int = Field(description="معرف المستخدم")
    government_insurance_number: str = Field(..., min_length=5, max_length=50, description="رقم التأمين الحكومي")
    employee_share_percentage: Decimal = Field(..., ge=0, le=100, description="نسبة استقطاع الموظف")
    employer_share_percentage: Decimal = Field(..., ge=0, le=100, description="نسبة صاحب العمل")


class EmployeeInsuranceProfileResponse(EmployeeInsuranceProfileCreate):
    id: int
    total_contributed_mrusdt: Decimal
    last_contribution_date: Optional[datetime] = None
    status: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)