# app/domains/command/schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.command.models import (
    DashboardType, AlertSeverity, AlertStatus, ReportType, BrandTier
)


# ============================================================
# لوحة القيادة (Dashboard)
# ============================================================

class DashboardResponse(BaseModel):
    dashboard: Dict[str, Any] = Field(description="إعدادات لوحة القيادة")
    stats: Dict[str, Any] = Field(description="الإحصائيات الأساسية")
    sector_stats: Dict[str, Any] = Field(description="إحصائيات القطاعات")
    alerts: List[Dict[str, Any]] = Field(description="التنبيهات النشطة")
    recommendations: List[Dict[str, Any]] = Field(description="توصيات الذكاء الاصطناعي")
    recent_activity: List[Dict[str, Any]] = Field(description="آخر النشاطات")

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# البراندات (Brands)
# ============================================================

class BrandSettingsCreate(BaseModel):
    brand_name: str = Field(..., min_length=2, max_length=255, description="اسم البراند")
    brand_slug: str = Field(..., min_length=2, max_length=255, pattern="^[a-z0-9-]+$", description="المعرف الفريد للبراند")
    brand_logo_url: Optional[str] = Field(default=None, description="رابط شعار البراند")
    brand_cover_url: Optional[str] = Field(default=None, description="رابط صورة الغلاف")
    primary_color: str = Field(default="#8CC63F", description="اللون الأساسي")
    secondary_color: str = Field(default="#06b6d4", description="اللون الثانوي")
    font_family: str = Field(default="Cairo", description="نوع الخط")
    tier: BrandTier = Field(default=BrandTier.FREE, description="مستوى البراند")
    features: Dict[str, Any] = Field(default_factory=dict, description="الميزات المتاحة")
    billing_email: Optional[str] = Field(default=None, description="بريد الفوترة")
    billing_address: Optional[str] = Field(default=None, description="عنوان الفوترة")
    tax_id: Optional[str] = Field(default=None, description="الرقم الضريبي")
    timezone: str = Field(default="Africa/Cairo", description="المنطقة الزمنية")
    language: str = Field(default="ar", description="اللغة")
    currency: str = Field(default="MR_USDT", description="العملة")


class BrandSettingsUpdate(BaseModel):
    brand_name: Optional[str] = Field(default=None, description="اسم البراند")
    brand_logo_url: Optional[str] = Field(default=None, description="رابط شعار البراند")
    brand_cover_url: Optional[str] = Field(default=None, description="رابط صورة الغلاف")
    primary_color: Optional[str] = Field(default=None, description="اللون الأساسي")
    secondary_color: Optional[str] = Field(default=None, description="اللون الثانوي")
    font_family: Optional[str] = Field(default=None, description="نوع الخط")
    features: Optional[Dict[str, Any]] = Field(default=None, description="الميزات المتاحة")
    billing_email: Optional[str] = Field(default=None, description="بريد الفوترة")
    billing_address: Optional[str] = Field(default=None, description="عنوان الفوترة")
    tax_id: Optional[str] = Field(default=None, description="الرقم الضريبي")
    timezone: Optional[str] = Field(default=None, description="المنطقة الزمنية")
    language: Optional[str] = Field(default=None, description="اللغة")
    currency: Optional[str] = Field(default=None, description="العملة")


class BrandSettingsResponse(BrandSettingsCreate):
    id: int
    tenant_id: int
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# التنبيهات (Alerts)
# ============================================================

class SystemAlertCreate(BaseModel):
    alert_type: str = Field(description="نوع التنبيه")
    severity: AlertSeverity = Field(description="خطورة التنبيه")
    title: str = Field(..., min_length=3, max_length=255, description="عنوان التنبيه")
    description: str = Field(description="وصف التنبيه")
    source: Optional[str] = Field(default=None, description="مصدر التنبيه (القطاع/الخدمة)")
    meta_data: Dict[str, Any] = Field(default_factory=dict, description="بيانات إضافية")


class SystemAlertResponse(SystemAlertCreate):
    id: int
    tenant_id: int
    status: AlertStatus
    acknowledged_by: Optional[int] = None
    acknowledged_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# التقارير (Reports)
# ============================================================

class CommandReportCreate(BaseModel):
    report_type: ReportType = Field(description="نوع التقرير")
    title: Optional[str] = Field(default=None, description="عنوان التقرير")
    description: Optional[str] = Field(default=None, description="وصف التقرير")
    filters: Dict[str, Any] = Field(default_factory=dict, description="الفلاتر المستخدمة")
    period_start: datetime = Field(description="بداية الفترة")
    period_end: datetime = Field(description="نهاية الفترة")
    format: str = Field(default="JSON", description="صيغة التقرير (JSON, PDF, EXCEL)")


class CommandReportResponse(CommandReportCreate):
    id: int
    tenant_id: int
    created_by: int
    report_data: Dict[str, Any]
    report_url: Optional[str] = None
    file_hash: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# توصيات الذكاء الاصطناعي (AI Recommendations)
# ============================================================

class AIRecommendationResponse(BaseModel):
    id: int
    tenant_id: int
    recommendation_type: str = Field(description="نوع التوصية")
    title: str = Field(description="عنوان التوصية")
    description: str = Field(description="وصف التوصية")
    impact_estimate: Optional[str] = Field(default=None, description="تقدير الأثر")
    analysis_data: Dict[str, Any] = Field(description="بيانات التحليل")
    confidence_score: float = Field(description="نسبة الثقة (0-100)")
    status: str = Field(description="حالة التوصية (PENDING, APPLIED, DISMISSED)")
    applied_by: Optional[int] = None
    applied_at: Optional[datetime] = None
    ai_agent_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# المقاييس (Metrics)
# ============================================================

class PlatformMetricCreate(BaseModel):
    metric_name: str = Field(description="اسم المقياس")
    metric_value: Decimal = Field(description="قيمة المقياس")
    metric_unit: Optional[str] = Field(default=None, description="وحدة القياس")
    recorded_at: datetime = Field(description="وقت التسجيل")
    period: str = Field(default="DAILY", description="الفترة (DAILY, WEEKLY, MONTHLY)")
    dimensions: Dict[str, Any] = Field(default_factory=dict, description="أبعاد إضافية")


class PlatformMetricResponse(PlatformMetricCreate):
    id: int
    tenant_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)