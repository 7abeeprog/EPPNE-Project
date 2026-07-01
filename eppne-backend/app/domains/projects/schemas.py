from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from .models import ProjectType, ProjectStatus, ContributionType, CarbonImpactScope
# ---------- Project ----------
class ProjectCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: str
    project_type: ProjectType
    country: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    funding_goal_mrusdt: Decimal = Field(..., gt=0)
    min_investment_mrusdt: Decimal = 0
    currency: str = "MR_USDT"
    expected_roi_percentage: Optional[Decimal] = None
    expected_irr_percentage: Optional[Decimal] = None
    payback_period_years: Optional[int] = None
    projected_cash_flows: Optional[List[Dict[str, Any]]] = None  # قائمة التدفقات
    carbon_impact_scope: Optional[CarbonImpactScope] = None
    estimated_carbon_emissions_tonnes: Optional[Decimal] = None
    estimated_carbon_offset_tonnes: Optional[Decimal] = None
    allow_in_kind_contributions: bool = True
    allow_fractional_ownership: bool = False
    shares_total: Optional[Decimal] = None
    share_price_mrusdt: Optional[Decimal] = None
    cover_image_url: Optional[str] = None
    gallery_urls: List[str] = []
    documents_urls: List[str] = []

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    expected_roi_percentage: Optional[Decimal] = None
    expected_irr_percentage: Optional[Decimal] = None
    actual_carbon_emissions_tonnes: Optional[Decimal] = None
    actual_carbon_offset_tonnes: Optional[Decimal] = None
    is_published: Optional[bool] = None

class ProjectResponse(ProjectCreate):
    id: int
    owner_id: int
    status: ProjectStatus
    current_funding_mrusdt: Decimal
    start_date: Optional[datetime]
    expected_completion_date: Optional[datetime]
    actual_completion_date: Optional[datetime]
    is_published: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ---------- Contributions ----------
class ContributionCreate(BaseModel):
    project_id: int
    contribution_type: ContributionType
    # monetary
    amount_mrusdt: Optional[Decimal] = None
    # land / facility
    land_area_sqm: Optional[Decimal] = None
    land_address: Optional[str] = None
    land_title_deed_hash: Optional[str] = None
    # labor hours
    labor_hours: Optional[Decimal] = None
    labor_description: Optional[str] = None
    # equipment
    equipment_description: Optional[str] = None
    equipment_estimated_value: Optional[Decimal] = None
    # consulting
    consulting_hours: Optional[Decimal] = None
    consulting_expertise: Optional[str] = None

class ContributionResponse(BaseModel):
    id: int
    project_id: int
    contributor_id: int
    contribution_type: ContributionType
    equivalent_value_mrusdt: Decimal
    status: str
    created_at: datetime
    approved_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)

class ContributionApprove(BaseModel):
    approved: bool = Field(..., description="True للموافقة، False للرفض")
    notes: Optional[str] = None

# ---------- Milestones ----------
class MilestoneCreate(BaseModel):
    title: str
    description: Optional[str] = None
    target_date: datetime
    funds_to_release: Decimal = 0

class MilestoneResponse(MilestoneCreate):
    id: int
    project_id: int
    is_completed: bool
    actual_date: Optional[datetime]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class MilestoneComplete(BaseModel):
    actual_date: datetime
    completion_notes: Optional[str] = None

# ---------- Updates & Follow ----------
class ProjectUpdateCreate(BaseModel):
    title: str
    content: str
    media_urls: List[str] = []

class ProjectUpdateResponse(ProjectUpdateCreate):
    id: int
    project_id: int
    author_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class FollowResponse(BaseModel):
    user_id: int
    project_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ---------- Analytics ----------
class ProjectAnalyticsResponse(BaseModel):
    project_id: int
    total_contributors: int
    total_monetary_contributions: Decimal
    total_in_kind_value: Decimal
    funding_percentage: float
    remaining_to_goal: Decimal
    milestones_completed: int
    milestones_total: int
    carbon_emissions_actual_vs_estimated: Optional[Dict[str, float]] = None
    roi_progress: Optional[float] = None  # العائد الحالي مقابل المتوقع