# app/domains/command/schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.command.models import (
    DashboardType, AlertSeverity, AlertStatus, ReportType, BrandTier
)


# ========== Dashboard ==========
class DashboardResponse(BaseModel):
    dashboard: Dict[str, Any]
    stats: Dict[str, Any]
    sector_stats: Dict[str, Any]
    alerts: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]
    model_config = ConfigDict(from_attributes=True)


# ========== Brands ==========
class BrandSettingsCreate(BaseModel):
    brand_name: str = Field(..., min_length=2, max_length=255)
    brand_slug: str = Field(..., min_length=2, max_length=255, pattern="^[a-z0-9-]+$")
    brand_logo_url: Optional[str] = None
    brand_cover_url: Optional[str] = None
    primary_color: str = "#8CC63F"
    secondary_color: str = "#06b6d4"
    font_family: str = "Cairo"
    tier: BrandTier = BrandTier.FREE
    features: Dict[str, Any] = {}
    billing_email: Optional[str] = None
    billing_address: Optional[str] = None
    tax_id: Optional[str] = None
    timezone: str = "Africa/Cairo"
    language: str = "ar"
    currency: str = "MR_USDT"


class BrandSettingsUpdate(BaseModel):
    brand_name: Optional[str] = None
    brand_logo_url: Optional[str] = None
    brand_cover_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    font_family: Optional[str] = None
    features: Optional[Dict[str, Any]] = None
    billing_email: Optional[str] = None
    billing_address: Optional[str] = None
    tax_id: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    currency: Optional[str] = None


class BrandSettingsResponse(BrandSettingsCreate):
    id: int
    tenant_id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========== Alerts ==========
class SystemAlertCreate(BaseModel):
    alert_type: str
    severity: AlertSeverity
    title: str = Field(..., min_length=3, max_length=255)
    description: str
    source: Optional[str] = None
    metadata: Dict[str, Any] = {}


class SystemAlertResponse(SystemAlertCreate):
    id: int
    tenant_id: int
    status: AlertStatus
    acknowledged_by: Optional[int]
    acknowledged_at: Optional[datetime]
    resolved_by: Optional[int]
    resolved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========== Reports ==========
class CommandReportCreate(BaseModel):
    report_type: ReportType
    title: Optional[str] = None
    description: Optional[str] = None
    filters: Dict[str, Any] = {}
    period_start: datetime
    period_end: datetime
    format: str = "JSON"


class CommandReportResponse(CommandReportCreate):
    id: int
    tenant_id: int
    created_by: int
    report_data: Dict[str, Any]
    report_url: Optional[str]
    file_hash: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========== AI Recommendations ==========
class AIRecommendationResponse(BaseModel):
    id: int
    tenant_id: int
    recommendation_type: str
    title: str
    description: str
    impact_estimate: Optional[str]
    analysis_data: Dict[str, Any]
    confidence_score: float
    status: str
    applied_by: Optional[int]
    applied_at: Optional[datetime]
    ai_agent_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========== Metrics ==========
class PlatformMetricCreate(BaseModel):
    metric_name: str
    metric_value: Decimal
    metric_unit: Optional[str] = None
    recorded_at: datetime
    period: str = "DAILY"
    dimensions: Dict[str, Any] = {}


class PlatformMetricResponse(PlatformMetricCreate):
    id: int
    tenant_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)