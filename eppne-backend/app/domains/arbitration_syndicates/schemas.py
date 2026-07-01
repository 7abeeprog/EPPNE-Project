# app/domains/arbitration_syndicates/schemas.py (الإصدار النهائي المتكامل)
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.arbitration_syndicates.models import DisputeStatus, JudgingMode, SyndicateType, ElectionStatus

# ========== التحكيم ==========
class ArbitrationCaseCreate(BaseModel):
    contract_id: Optional[str] = None
    respondent_id: int
    dispute_reason: str
    evidence_hashes: List[str] = []
    judging_mode: JudgingMode = JudgingMode.AI_HYBRID

class ArbitrationCaseResponse(BaseModel):
    id: int
    claimant_id: int
    respondent_id: int
    dispute_reason: str
    evidence_hashes: List[str]
    judging_mode: JudgingMode
    status: DisputeStatus
    final_verdict: Optional[str]
    enforcement_tx_hash: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class JuryVoteCreate(BaseModel):
    case_id: int
    vote: bool  # True للمدعي, False للمدعى عليه
    justification: Optional[str] = None

class VerdictCreate(BaseModel):
    final_verdict: str
    enforcement_tx_hash: str

# ========== النقابات ==========
class SyndicateCreate(BaseModel):
    name: str
    syndicate_type: SyndicateType
    description: Optional[str] = None
    annual_fee_mrusdt: Decimal = 0
    dao_contract_address: Optional[str] = None
    treasury_wallet_address: Optional[str] = None
    governance_token: Optional[str] = None

class SyndicateResponse(SyndicateCreate):
    id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SyndicateMembershipCreate(BaseModel):
    syndicate_id: int
    join_date: datetime
    expiry_date: Optional[datetime] = None

    @field_validator("expiry_date")
    def validate_dates(cls, v, info):
        if v and "join_date" in info.data and v <= info.data["join_date"]:
            raise ValueError("expiry_date must be after join_date")
        return v

class SyndicateMembershipResponse(BaseModel):
    id: int
    syndicate_id: int
    member_user_id: int
    membership_number: str
    join_date: datetime
    expiry_date: datetime
    status: str
    membership_sbt_id: Optional[str]
    minting_tx_hash: Optional[str]
    model_config = ConfigDict(from_attributes=True)

class ProfessionalLicenseCreate(BaseModel):
    syndicate_id: int
    license_name: str
    issue_date: datetime
    expiry_date: datetime
    required_certificate_id: Optional[int] = None
    qualifies_for_job_id: Optional[int] = None

    @field_validator("expiry_date")
    def validate_dates(cls, v, info):
        if "issue_date" in info.data and v <= info.data["issue_date"]:
            raise ValueError("expiry_date must be after issue_date")
        return v

class ProfessionalLicenseResponse(ProfessionalLicenseCreate):
    id: int
    user_id: int
    license_number: str
    status: str
    license_sbt_id: Optional[str]
    minting_tx_hash: Optional[str]
    model_config = ConfigDict(from_attributes=True)

# ========== الانتخابات ==========
class ElectionCreate(BaseModel):
    syndicate_id: int
    title: str
    election_type: str
    election_year: int
    nomination_start: datetime
    nomination_end: datetime
    voting_start: datetime
    voting_end: datetime

    @field_validator("nomination_end")
    def validate_nomination(cls, v, info):
        if "nomination_start" in info.data and v <= info.data["nomination_start"]:
            raise ValueError("nomination_end must be after nomination_start")
        return v

    @field_validator("voting_start")
    def validate_voting_start(cls, v, info):
        if "nomination_end" in info.data and v <= info.data["nomination_end"]:
            raise ValueError("voting_start must be after nomination_end")
        return v

    @field_validator("voting_end")
    def validate_voting_end(cls, v, info):
        if "voting_start" in info.data and v <= info.data["voting_start"]:
            raise ValueError("voting_end must be after voting_start")
        return v

class ElectionResponse(ElectionCreate):
    id: int
    status: ElectionStatus
    smart_contract_address: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CandidateCreate(BaseModel):
    election_id: int
    manifesto: str

class CandidateResponse(CandidateCreate):
    id: int
    user_id: int
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class VoteCast(BaseModel):
    candidate_id: int