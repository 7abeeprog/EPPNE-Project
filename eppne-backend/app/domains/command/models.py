# app/domains/command/models.py
"""
نماذج (Models) قطاع القيادة الاستراتيجية – لوحة التحكم السيادية الموحدة
يدعم: لوحات القيادة، إدارة البراندات، مراقبة النظام، التقارير، والإعدادات
"""
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, JSON, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class DashboardType(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"      # لوحة القيادة العليا
    BRAND_ADMIN = "BRAND_ADMIN"      # لوحة قيادة البراند
    OPERATOR = "OPERATOR"            # لوحة المراقبة التشغيلية


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

    # إعدادات اللوحة
    layout = Column(JSON, default=dict)          # ترتيب وتخطيط البطاقات
    widgets = Column(JSON, default=list)         # قائمة عناصر الواجهة النشطة
    theme = Column(JSON, default=dict)           # إعدادات الألوان والخطوط

    # تخصيص البراند
    brand_name = Column(String(255), nullable=True)
    brand_logo_url = Column(String(512), nullable=True)
    primary_color = Column(String(7), default="#8CC63F")
    secondary_color = Column(String(7), default="#06b6d4")

    # إعدادات الإشعارات
    notification_preferences = Column(JSON, default=dict)  # {email: true, push: true, sms: false}

    # إعدادات التقارير
    report_preferences = Column(JSON, default=dict)        # {frequency: "monthly", format: "pdf"}

    # التوثيق
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

    # معلومات البراند
    brand_name = Column(String(255), nullable=False)
    brand_slug = Column(String(255), unique=True, nullable=False, index=True)
    brand_logo_url = Column(String(512), nullable=True)
    brand_cover_url = Column(String(512), nullable=True)

    # الهوية البصرية
    primary_color = Column(String(7), default="#8CC63F")
    secondary_color = Column(String(7), default="#06b6d4")
    font_family = Column(String(100), default="Cairo")

    # مستوى البراند
    tier = Column(SQLEnum(BrandTier), default=BrandTier.FREE)
    features = Column(JSON, default=dict)  # {"ai_analytics": true, "custom_reports": true, ...}

    # إعدادات الفوترة
    billing_email = Column(String(255), nullable=True)
    billing_address = Column(Text, nullable=True)
    tax_id = Column(String(100), nullable=True)

    # الإعدادات الإقليمية
    timezone = Column(String(50), default="Africa/Cairo")
    language = Column(String(10), default="ar")
    currency = Column(String(10), default="MR_USDT")

    # التوثيق
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

    alert_type = Column(String(50), nullable=False)  # SERVER_DOWN, HIGH_LOAD, LOW_STORAGE, SECURITY_BREACH
    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    source = Column(String(255), nullable=True)      # القطاع أو الخدمة المسببة
    
    # ✅ تم تغيير اسم الحقل من metadata إلى meta_data لحل التعارض مع Base.metadata
    meta_data = Column(JSON, default=dict)            # بيانات إضافية (مثل: {"cpu": 95, "memory": 80})

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
    )


class PlatformMetric(Base):
    __tablename__ = "command_platform_metrics"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    metric_name = Column(String(100), nullable=False, index=True)  # total_users, revenue, active_sessions
    metric_value = Column(Numeric(30, 8), nullable=False)
    metric_unit = Column(String(50), nullable=True)

    # السياق الزمني
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)
    period = Column(String(20), default="DAILY")  # DAILY, WEEKLY, MONTHLY

    # بيانات إضافية
    dimensions = Column(JSON, default=dict)        # {"sector": "finance", "region": "Egypt"}

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_platform_metric_tenant", "tenant_id"),
        Index("ix_platform_metric_name_time", "metric_name", "recorded_at"),
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

    # محتوى التقرير (JSON)
    report_data = Column(JSON, nullable=False)      # البيانات الفعلية
    filters = Column(JSON, default=dict)            # الفلاتر المستخدمة

    # إعدادات التقرير
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    format = Column(String(20), default="JSON")     # JSON, PDF, EXCEL

    # التوثيق
    report_url = Column(String(512), nullable=True)  # رابط التحميل
    file_hash = Column(String(100), nullable=True)   # للتأكد من سلامة الملف

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_command_report_tenant", "tenant_id"),
        Index("ix_command_report_type", "report_type"),
    )


# ========== 4. توصيات الذكاء الاصطناعي ==========

class AIRecommendation(Base):
    __tablename__ = "command_ai_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    recommendation_type = Column(String(50), nullable=False)  # FINANCIAL, OPERATIONAL, MARKETING, SECURITY
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    impact_estimate = Column(String(255), nullable=True)      # "زيادة الإيرادات 15%"

    # بيانات التحليل
    analysis_data = Column(JSON, nullable=False)              # البيانات التي أدت إلى التوصية
    confidence_score = Column(Numeric(5, 2), default=0)       # 0-100

    status = Column(String(50), default="PENDING")            # PENDING, APPLIED, DISMISSED
    applied_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)

    ai_agent_id = Column(Integer, nullable=True)              # وكيل الذكاء الاصطناعي الذي أنشأ التوصية

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_ai_recommendation_tenant", "tenant_id"),
        Index("ix_ai_recommendation_status", "status"),
    )