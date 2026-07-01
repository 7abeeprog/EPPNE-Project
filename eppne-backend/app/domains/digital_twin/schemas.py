from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.digital_twin.models import TwinAccessLevel, TwinCapability, LifeStatus, MilestoneType

# ========== Digital Twin ==========
class TwinConfigCreate(BaseModel):
    global_access_level: TwinAccessLevel = TwinAccessLevel.PRIVATE
    interaction_fee_mrusdt: Decimal = 0
    subscription_monthly_mrusdt: Decimal = 0
    capabilities: List[TwinCapability] = [TwinCapability.CHAT]
    knowledge_boundaries: Dict[str, Any] = {}
    max_spending_limit: Decimal = 0
    settlement_type: str = "WEB2_FIAT"

class TwinConfigResponse(TwinConfigCreate):
    id: int
    user_id: int
    agent_id: Optional[int]
    is_active: bool
    physical_embodiment_status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TwinPermissionCreate(BaseModel):
    grantee_user_id: Optional[int] = None
    grantee_rank: Optional[str] = None
    access_granted: bool = True
    override_fee: bool = False

class TwinPermissionResponse(TwinPermissionCreate):
    id: int
    twin_config_id: int
    model_config = ConfigDict(from_attributes=True)

class TwinInteractionCreate(BaseModel):
    interaction_type: str  # TEXT, VOICE, METAVERSE_AVATAR
    duration_minutes: int

class TwinInteractionResponse(BaseModel):
    id: int
    twin_config_id: int
    visitor_id: int
    interaction_type: str
    duration_minutes: int
    fee_paid_mrusdt: float
    payout_tx_hash: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Legacy ==========
class TimeCapsuleCreate(BaseModel):
    encrypted_payload_hash: str
    video_will_ipfs: Optional[str] = None
    heartbeat_interval_days: int = 90
    encrypted_credentials: Optional[Dict[str, Any]] = None

class TimeCapsuleResponse(TimeCapsuleCreate):
    id: int
    user_id: int
    status: str
    last_heartbeat_at: datetime
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class BeneficiaryCreate(BaseModel):
    beneficiary_user_id: int
    relationship_type: Optional[str] = None
    access_share_percentage: int = 100
    heir_wallet_address: str

class BeneficiaryResponse(BeneficiaryCreate):
    id: int
    capsule_id: int
    model_config = ConfigDict(from_attributes=True)

class DigitalWillCreate(BaseModel):
    will_content_ipfs: str
    legal_witness_tx: Optional[str] = None

class DigitalWillResponse(DigitalWillCreate):
    id: int
    user_id: int
    will_nft_id: str
    is_executed: bool
    executed_at: Optional[datetime]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Death Oracle ==========
class ProofOfLife(BaseModel):
    proof_type: str  # ON_CHAIN_TX, BIOMETRIC_SCAN, MULTI_SIG_CONSENSUS
    proof_payload_hash: str

class DeathReport(BaseModel):
    reporter_user_id: int
    evidence_ipfs_hash: str

class DeathOracleResponse(BaseModel):
    id: int
    user_id: int
    status: str
    last_confirmed_alive_at: datetime
    check_interval_days: int
    grace_period_days: int
    release_tx_hash: Optional[str]
    model_config = ConfigDict(from_attributes=True)

# ========== Life Milestones ==========
class LifeMilestoneCreate(BaseModel):
    milestone_type: MilestoneType
    title: str
    description: Optional[str] = None
    evidence_ipfs_hash: Optional[str] = None
    occurrence_date: datetime

class LifeMilestoneResponse(LifeMilestoneCreate):
    id: int
    user_id: int
    milestone_nft_id: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Pre-Birth ==========
class PreBirthRecordCreate(BaseModel):
    parent_1_id: int
    parent_2_id: Optional[int] = None
    reserved_sovereign_id: str
    trust_fund_wallet: Optional[str] = None
    expected_arrival_date: Optional[datetime] = None
    genetic_profile_hash: Optional[str] = None

class PreBirthRecordResponse(PreBirthRecordCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)