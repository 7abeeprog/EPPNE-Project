# app/domains/zamakana/schemas.py (الإصدار النهائي المتكامل)
"""
نماذج (Schemas) Pydantic لقطاع الزمكان – التحقق من صحة البيانات وتسلسلها.
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.zamakana.models import ZamakanaNodeType, ScenarioStatus, ClaimStatus


# ========== Nodes & Edges ==========
class ZamakanaNodeCreate(BaseModel):
    node_type: ZamakanaNodeType
    title: str = Field(..., min_length=1, max_length=255)
    description: str
    timeline_year: Optional[int] = None
    geo_location: Optional[str] = None
    verified_sources: List[str] = []
    extra_data: Dict[str, Any] = {}


class ZamakanaNodeResponse(ZamakanaNodeCreate):
    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ZamakanaEdgeCreate(BaseModel):
    source_node_id: int
    target_node_id: int
    impact_description: str
    impact_weight: Decimal = 1.0
    is_alternative_timeline: bool = False


class ZamakanaEdgeResponse(ZamakanaEdgeCreate):
    id: int
    created_by: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========== Planetary Campaigns ==========
class PlanetaryCampaignCreate(BaseModel):
    title: str
    description: str
    target_time_hours: Decimal = Field(..., gt=0)
    end_date: datetime

    @field_validator("end_date")
    def validate_end_date(cls, v, info):
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class PlanetaryCampaignResponse(PlanetaryCampaignCreate):
    id: int
    created_by: int
    collected_time_hours: Decimal
    status: str
    campaign_contract_address: Optional[str]
    start_date: datetime
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TimePledgeCreate(BaseModel):
    campaign_id: int
    pledged_hours: Decimal = Field(..., gt=0)
    skill_category: Optional[str] = None


class TimePledgeResponse(TimePledgeCreate):
    id: int
    user_id: int
    status: str
    proof_hash: Optional[str]
    verified_by: Optional[int]
    verified_at: Optional[datetime]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TimePledgeFulfill(BaseModel):
    proof_hash: str  # رابط IPFS لإثبات الإنجاز


# ========== Future Scenarios ==========
class FutureScenarioCreate(BaseModel):
    scenario_title: str
    description: str
    target_year: int = Field(..., ge=2025, le=3000)
    assumptions: Dict[str, Any] = {}


class FutureScenarioResponse(FutureScenarioCreate):
    id: int
    created_by: int
    ai_analysis_report: Optional[Dict[str, Any]]
    ai_agent_id: Optional[int]
    status: ScenarioStatus
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class HumanFeedbackCreate(BaseModel):
    scenario_id: int
    feedback_text: str
    agreement_score: Optional[int] = Field(None, ge=0, le=100)


class HumanFeedbackResponse(HumanFeedbackCreate):
    id: int
    reviewer_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)