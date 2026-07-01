# app/domains/service_marketplace/models.py
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text, Boolean,
    Numeric, JSON, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ServiceType(str, enum.Enum):
    RIDE_HAILING = "RIDE_HAILING"           # تطبيق نقل ركاب (أوبر)
    DELIVERY = "DELIVERY"                   # تطبيق توصيل طلبات
    E_COMMERCE = "E_COMMERCE"               # متجر إلكتروني
    TOURISM_BOOKING = "TOURISM_BOOKING"     # منصة حجز سياحي
    EDUCATION_PLATFORM = "EDUCATION_PLATFORM" # منصة تعليمية (مثل يوديمي)
    JOB_MARKETPLACE = "JOB_MARKETPLACE"     # منصة توظيف
    SOCIAL_NETWORK = "SOCIAL_NETWORK"       # شبكة اجتماعية
    HEALTHCARE_PORTAL = "HEALTHCARE_PORTAL" # بوابة صحية (حجوزات، استشارات)
    REAL_ESTATE = "REAL_ESTATE"             # منصة عقارات
    EVENT_MANAGEMENT = "EVENT_MANAGEMENT"   # منصة إدارة فعاليات
    CUSTOM = "CUSTOM"                       # مخصص


class DeploymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    DEPLOYING = "DEPLOYING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    SUSPENDED = "SUSPENDED"


class SubscriptionPlan(str, enum.Enum):
    FREE = "FREE"
    BASIC = "BASIC"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"


# ========== 1. الخدمات/التطبيقات المتاحة في المتجر ==========
class MarketplaceService(Base):
    __tablename__ = "marketplace_services"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # المستأجر الذي يقدم الخدمة (EPPNE أو شريك)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    service_type = Column(SQLEnum(ServiceType), nullable=False, index=True)
    version = Column(String(20), default="1.0.0")

    # الملفات والموارد
    thumbnail_url = Column(String(512), nullable=True)
    demo_url = Column(String(512), nullable=True)
    documentation_url = Column(String(512), nullable=True)

    # هيكل التطبيق (JSON Schema لقواعد البيانات، API endpoints، إعدادات)
    database_schema = Column(JSON, nullable=True)       # الجداول الإضافية المطلوبة
    api_blueprint = Column(JSON, nullable=True)        # نقاط النهاية الإضافية
    frontend_template_url = Column(String(512), nullable=True)  # رابط قالب الواجهة (ZIP)
    default_config = Column(JSON, default=dict)        # الإعدادات الافتراضية

    # المتطلبات الأساسية
    requires_modules = Column(JSON, default=list)      # ["finance", "academy", "notifications"]
    min_sovereign_rank = Column(String(50), nullable=True)

    # التسعير
    base_price_mrusdt = Column(Numeric(30, 8), default=0)
    subscription_price_basic_mrusdt = Column(Numeric(30, 8), default=0)
    subscription_price_pro_mrusdt = Column(Numeric(30, 8), default=0)
    subscription_price_enterprise_mrusdt = Column(Numeric(30, 8), default=0)

    # الإضافات المتاحة
    available_addons = Column(JSON, default=list)      # قائمة معرفات الإضافات

    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)


# ========== 2. إصدارات الخدمة (Service Versions) ==========
class ServiceVersion(Base):
    __tablename__ = "service_versions"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("marketplace_services.id"), nullable=False, index=True)
    version = Column(String(20), nullable=False)
    changelog = Column(Text, nullable=True)
    database_schema = Column(JSON, nullable=True)
    api_blueprint = Column(JSON, nullable=True)
    frontend_template_url = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ========== 3. تراخيص المستخدمين للتطبيقات المشتراة ==========
class ServiceLicense(Base):
    __tablename__ = "service_licenses"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("marketplace_services.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # المستأجر المالك للترخيص
    buyer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # معلومات النشر
    deployed_domain = Column(String(255), nullable=True)          # النطاق الفرعي المُنشأ (مثل taxi.eppne.com)
    deployment_status = Column(SQLEnum(DeploymentStatus), default=DeploymentStatus.PENDING)
    deployment_log = Column(Text, nullable=True)                 # سجل عملية النشر

    # خيارات الشراء
    subscription_plan = Column(SQLEnum(SubscriptionPlan), default=SubscriptionPlan.FREE)
    purchased_addons = Column(JSON, default=list)                # قائمة معرفات الإضافات المشتراة
    custom_config = Column(JSON, default=dict)                   # إعدادات مخصصة للمستخدم

    # المالية
    paid_amount_mrusdt = Column(Numeric(30, 8), default=0)
    subscription_start = Column(DateTime(timezone=True), nullable=True)
    subscription_end = Column(DateTime(timezone=True), nullable=True)
    auto_renew = Column(Boolean, default=True)

    # 🔥 Idempotency Key (لمنع تكرار عمليات الشراء)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    # الحالة
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_license_tenant_service", "tenant_id", "service_id"),
        Index("ix_license_status", "deployment_status"),
    )


# ========== 4. الإضافات (Add-ons) ==========
class ServiceAddon(Base):
    __tablename__ = "service_addons"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    addon_type = Column(String(50), nullable=False)   # payment_gateway, chat_bot, affiliate_system, analytics, etc.
    version = Column(String(20), default="1.0.0")

    # ما هي أنواع الخدمات التي يدعمها هذا الإضافة؟
    compatible_service_types = Column(JSON, default=list)  # ["RIDE_HAILING", "E_COMMERCE"]

    # تنفيذ الإضافة (كود، قواعد بيانات، واجهة)
    database_schema = Column(JSON, nullable=True)
    api_blueprint = Column(JSON, nullable=True)
    frontend_component_url = Column(String(512), nullable=True)

    # التسعير
    price_mrusdt = Column(Numeric(30, 8), default=0)

    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_addon_tenant_type", "tenant_id", "addon_type"),
    )


# ========== 5. طلبات التخصيص ==========
class CustomizationRequest(Base):
    __tablename__ = "customization_requests"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    license_id = Column(Integer, ForeignKey("service_licenses.id"), nullable=False, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    proposed_budget_mrusdt = Column(Numeric(30, 8), nullable=True)

    status = Column(String(50), default="PENDING")   # PENDING, APPROVED, IN_PROGRESS, COMPLETED, REJECTED
    assigned_developer_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # 🔥 Idempotency Key (لمنع تكرار طلبات التخصيص)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_customization_tenant_status", "tenant_id", "status"),
        Index("ix_customization_license", "license_id"),
    )


# ============================================================
# 🆕 6. شراء الإضافات (Add-on Purchases) مع Idempotency
# ============================================================
class ServiceAddonPurchase(Base):
    __tablename__ = "service_addon_purchases"

    id = Column(Integer, primary_key=True, index=True)
    license_id = Column(Integer, ForeignKey("service_licenses.id"), nullable=False, index=True)
    addon_id = Column(Integer, ForeignKey("service_addons.id"), nullable=False, index=True)

    # 🔥 Idempotency Key (لمنع تكرار شراء الإضافة)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    price_paid_mrusdt = Column(Numeric(30, 8), default=0)
    purchased_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_addon_purchase_license", "license_id"),
        Index("ix_addon_purchase_addon", "addon_id"),
        Index("ix_addon_purchase_license_addon", "license_id", "addon_id", unique=True, postgresql_where="idempotency_key IS NULL"),
    )