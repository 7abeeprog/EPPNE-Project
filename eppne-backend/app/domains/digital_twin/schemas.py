# app/domains/digital_twin/schemas.py
from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.digital_twin.models import TwinAccessLevel, TwinCapability, LifeStatus, MilestoneType


# ============================================================
# التوأم الرقمي (Digital Twin)
# ============================================================

class TwinConfigCreate(BaseModel):
    global_access_level: TwinAccessLevel = Field(default=TwinAccessLevel.PRIVATE, description="مستوى الوصول العام")
    interaction_fee_mrusdt: Decimal = Field(default=Decimal("0.0"), description="رسوم التفاعل بالدقيقة")
    subscription_monthly_mrusdt: Decimal = Field(default=Decimal("0.0"), description="رسوم الاشتراك الشهرية")
    capabilities: List[TwinCapability] = Field(default=[TwinCapability.CHAT], description="قدرات التوأم")
    knowledge_boundaries: Dict[str, Any] = Field(default_factory=dict, description="حدود المعرفة")
    max_spending_limit: Decimal = Field(default=Decimal("0.0"), description="الحد الأقصى للإنفاق الشهري")
    settlement_type: str = Field(default="WEB2_FIAT", description="نوع التسوية")


class TwinConfigResponse(TwinConfigCreate):
    id: int
    user_id: int
    agent_id: Optional[int] = None
    is_active: bool
    physical_embodiment_status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TwinPermissionCreate(BaseModel):
    grantee_user_id: Optional[int] = Field(default=None, description="معرف المستخدم الممنوح")
    grantee_rank: Optional[str] = Field(default=None, description="الرتبة الممنوحة")
    access_granted: bool = Field(default=True, description="هل الوصول ممنوح؟")
    override_fee: bool = Field(default=False, description="هل يُعفى من الرسوم؟")


class TwinPermissionResponse(TwinPermissionCreate):
    id: int
    twin_config_id: int
    model_config = ConfigDict(from_attributes=True)


class TwinInteractionCreate(BaseModel):
    interaction_type: str = Field(description="نوع التفاعل (TEXT, VOICE, METAVERSE_AVATAR)")
    duration_minutes: int = Field(description="مدة التفاعل بالدقائق")
    affiliate_code: Optional[str] = Field(default=None, description="كود الإحالة (اختياري)")


class TwinInteractionResponse(BaseModel):
    id: int
    twin_config_id: int
    visitor_id: int
    interaction_type: str
    duration_minutes: int
    fee_paid_mrusdt: float
    payout_tx_hash: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# الإرث والخزائن الزمنية (Legacy & Time Capsules)
# ============================================================

class TimeCapsuleCreate(BaseModel):
    encrypted_payload_hash: str = Field(description="هاش المحتوى المشفر")
    video_will_ipfs: Optional[str] = Field(default=None, description="وصية فيديو على IPFS")
    heartbeat_interval_days: int = Field(default=90, description="فترة نبض الحياة بالأيام")
    encrypted_credentials: Optional[Dict[str, Any]] = Field(default=None, description="المفاتيح المشفرة")
    beneficiaries: List[BeneficiaryCreate] = Field(..., description="قائمة المستفيدين")

class TimeCapsuleResponse(TimeCapsuleCreate):
    id: int
    user_id: int
    status: str
    last_heartbeat_at: datetime
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BeneficiaryCreate(BaseModel):
    beneficiary_user_id: int = Field(description="معرف المستفيد")
    relationship_type: Optional[str] = Field(default=None, description="نوع العلاقة")
    access_share_percentage: int = Field(default=100, description="نسبة الحصة")
    heir_wallet_address: str = Field(description="عنوان محفظة الوريث")


class BeneficiaryResponse(BeneficiaryCreate):
    id: int
    capsule_id: int
    model_config = ConfigDict(from_attributes=True)


class DigitalWillCreate(BaseModel):
    will_content_ipfs: str = Field(description="نص الوصية على IPFS")
    legal_witness_tx: Optional[str] = Field(default=None, description="توقيع الشهود")


class DigitalWillResponse(DigitalWillCreate):
    id: int
    user_id: int
    will_nft_id: str
    is_executed: bool
    executed_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# أوراكل الموت (Death Oracle)
# ============================================================

class ProofOfLife(BaseModel):
    proof_type: str = Field(description="نوع الدليل (ON_CHAIN_TX, BIOMETRIC_SCAN, MULTI_SIG_CONSENSUS)")
    proof_payload_hash: str = Field(description="هاش الدليل")


class DeathReport(BaseModel):
    reporter_user_id: int = Field(description="معرف المبلغ عن الوفاة")
    evidence_ipfs_hash: str = Field(description="دليل الوفاة على IPFS")


class DeathOracleResponse(BaseModel):
    id: int
    user_id: int
    status: str
    last_confirmed_alive_at: datetime
    check_interval_days: int
    grace_period_days: int
    release_tx_hash: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# محطات الحياة (Life Milestones)
# ============================================================

class LifeMilestoneCreate(BaseModel):
    milestone_type: MilestoneType = Field(description="نوع المحطة")
    title: str = Field(description="العنوان")
    description: Optional[str] = Field(default=None, description="الوصف")
    evidence_ipfs_hash: Optional[str] = Field(default=None, description="دليل على IPFS")
    occurrence_date: datetime = Field(description="تاريخ الحدوث")


class LifeMilestoneResponse(LifeMilestoneCreate):
    id: int
    user_id: int
    milestone_nft_id: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# الحجز قبل الولادة (Pre-Birth Identity)
# ============================================================

class PreBirthRecordCreate(BaseModel):
    parent_2_id: Optional[int] = Field(default=None, description="معرف الوالد الثاني")
    reserved_sovereign_id: str = Field(description="الاسم السيادي المحجوز")
    trust_fund_wallet: Optional[str] = Field(default=None, description="محفظة صندوق الثقة")
    expected_arrival_date: Optional[datetime] = Field(default=None, description="تاريخ الولادة المتوقع")
    genetic_profile_hash: Optional[str] = Field(default=None, description="هاش الملف الوراثي")


class PreBirthRecordResponse(PreBirthRecordCreate):
    id: int
    parent_1_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)