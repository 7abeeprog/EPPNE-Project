# app/domains/command/models.py
"""
نماذج (Models) قطاع القيادة الاستراتيجية – لوحة التحكم السيادية الموحدة
يدعم: لوحات القيادة، إدارة البراندات، مراقبة النظام، التقارير، والإعدادات
"""
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB  # ✅ تم إضافة الاستيراد الصحيح
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class DashboardType(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    BRAND_ADMIN = "BRAND_ADMIN"
    OPERATOR = "OPERATOR"


class AlertSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


class AlertStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class ReportType(str, enum.Enum):
    FINANCIAL = "FINANCIAL"
    OPERATIONAL = "OPERATIONAL"
    USER_GROWTH = "USER_GROWTH"
    SECTOR_PERFORMANCE = "SECTOR_PERFORMANCE"
    SYSTEM_HEALTH = "SYSTEM_HEALTH"


class BrandTier(str, enum.Enum):
    FREE = "FREE"
    BASIC = "BASIC"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"


# ========== 1. لوحات القيادة والإعدادات ==========

class CommandDashboard(Base):
    __tablename__ = "command_dashboards"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    dashboard_type = Column(SQLEnum(DashboardType), nullable=False, default=DashboardType.BRAND_ADMIN)

    layout = Column(JSONB, default=dict)
    widgets = Column(JSONB, default=list)
    theme = Column(JSONB, default=dict)

    brand_name = Column(String(255), nullable=True)
    brand_logo_url = Column(String(512), nullable=True)
    primary_color = Column(String(7), default="#8CC63F")
    secondary_color = Column(String(7), default="#06b6d4")

    notification_preferences = Column(JSONB, default=dict)
    report_preferences = Column(JSONB, default=dict)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_command_dashboard_tenant", "tenant_id"),
        Index("ix_command_dashboard_type", "dashboard_type"),
    )


class BrandSettings(Base):
    __tablename__ = "command_brand_settings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), unique=True, nullable=False, index=True)

    brand_name = Column(String(255), nullable=False)
    brand_slug = Column(String(255), unique=True, nullable=False, index=True)
    brand_logo_url = Column(String(512), nullable=True)
    brand_cover_url = Column(String(512), nullable=True)

    primary_color = Column(String(7), default="#8CC63F")
    secondary_color = Column(String(7), default="#06b6d4")
    font_family = Column(String(100), default="Cairo")

    tier = Column(SQLEnum(BrandTier), default=BrandTier.FREE)
    features = Column(JSONB, default=dict)

    billing_email = Column(String(255), nullable=True)
    billing_address = Column(Text, nullable=True)
    tax_id = Column(String(100), nullable=True)

    timezone = Column(String(50), default="Africa/Cairo")
    language = Column(String(10), default="ar")
    currency = Column(String(10), default="MR_USDT")

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_brand_settings_tenant", "tenant_id"),
        Index("ix_brand_settings_slug", "brand_slug"),
    )


# ========== 2. مراقبة النظام والتنبيهات ==========

class SystemAlert(Base):
    __tablename__ = "command_system_alerts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    alert_type = Column(String(50), nullable=False)
    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    source = Column(String(255), nullable=True)

    meta_data = Column(JSONB, default=dict)

    status = Column(SQLEnum(AlertStatus), default=AlertStatus.ACTIVE)
    acknowledged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_system_alert_tenant", "tenant_id"),
        Index("ix_system_alert_status", "status"),
        Index("ix_system_alert_severity", "severity"),
        Index("ix_system_alert_status_severity", "status", "severity"),
    )


class PlatformMetric(Base):
    __tablename__ = "command_platform_metrics"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Numeric(30, 8), nullable=False)
    metric_unit = Column(String(50), nullable=True)

    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)
    period = Column(String(20), default="DAILY")

    dimensions = Column(JSONB, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_platform_metric_tenant", "tenant_id"),
        Index("ix_platform_metric_name_time", "metric_name", "recorded_at"),
        Index("ix_platform_metric_period", "period"),
    )


class UserSession(Base):
    __tablename__ = "command_user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    session_token = Column(String(255), unique=True, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    device_type = Column(String(50), nullable=True)

    login_time = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    logout_time = Column(DateTime(timezone=True), nullable=True)

    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index("ix_user_session_tenant", "tenant_id"),
        Index("ix_user_session_user", "user_id"),
        Index("ix_user_session_active", "is_active"),
        Index("ix_user_session_user_active", "user_id", "is_active"),
    )


# ========== 3. التقارير والتحليلات ==========

class CommandReport(Base):
    __tablename__ = "command_reports"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    report_type = Column(SQLEnum(ReportType), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    report_data = Column(JSONB, nullable=False)
    filters = Column(JSONB, default=dict)

    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    format = Column(String(20), default="JSON")

    report_url = Column(String(512), nullable=True)
    file_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_command_report_tenant", "tenant_id"),
        Index("ix_command_report_type", "report_type"),
        Index("ix_command_report_type_created", "report_type", "created_at"),
    )


# ========== 4. توصيات الذكاء الاصطناعي ==========

class AIRecommendation(Base):
    __tablename__ = "command_ai_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    recommendation_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    impact_estimate = Column(String(255), nullable=True)

    analysis_data = Column(JSONB, nullable=False)
    confidence_score = Column(Numeric(5, 2), default=0)

    status = Column(String(50), default="PENDING")
    applied_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)

    ai_agent_id = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_ai_recommendation_tenant", "tenant_id"),
        Index("ix_ai_recommendation_status", "status"),
        Index("ix_ai_recommendation_type_status", "recommendation_type", "status"),
    )