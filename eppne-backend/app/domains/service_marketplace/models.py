# app/domains/service_marketplace/models.py
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text, Boolean,
    Numeric, Enum as SQLEnum, Index, CheckConstraint, text
)
from sqlalchemy.dialects.postgresql import JSONB  # ✅ تم إضافة الاستيراد الصحيح
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ServiceType(str, enum.Enum):
    RIDE_HAILING = "RIDE_HAILING"
    DELIVERY = "DELIVERY"
    E_COMMERCE = "E_COMMERCE"
    TOURISM_BOOKING = "TOURISM_BOOKING"
    EDUCATION_PLATFORM = "EDUCATION_PLATFORM"
    JOB_MARKETPLACE = "JOB_MARKETPLACE"
    SOCIAL_NETWORK = "SOCIAL_NETWORK"
    HEALTHCARE_PORTAL = "HEALTHCARE_PORTAL"
    REAL_ESTATE = "REAL_ESTATE"
    EVENT_MANAGEMENT = "EVENT_MANAGEMENT"
    CUSTOM = "CUSTOM"


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
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    service_type = Column(SQLEnum(ServiceType), nullable=False, index=True)
    version = Column(String(20), default="1.0.0")

    thumbnail_url = Column(String(512), nullable=True)
    demo_url = Column(String(512), nullable=True)
    documentation_url = Column(String(512), nullable=True)

    database_schema = Column(JSONB, nullable=True)
    api_blueprint = Column(JSONB, nullable=True)
    frontend_template_url = Column(String(512), nullable=True)
    default_config = Column(JSONB, default=dict)

    requires_modules = Column(JSONB, default=list)
    min_sovereign_rank = Column(String(50), nullable=True)

    base_price_mrusdt = Column(Numeric(30, 8), default=0)
    subscription_price_basic_mrusdt = Column(Numeric(30, 8), default=0)
    subscription_price_pro_mrusdt = Column(Numeric(30, 8), default=0)
    subscription_price_enterprise_mrusdt = Column(Numeric(30, 8), default=0)

    available_addons = Column(JSONB, default=list)

    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_marketplace_service_tenant", "tenant_id"),
        Index("ix_marketplace_service_type", "service_type"),
        Index("ix_marketplace_service_created_at", "created_at"),
    )


# ========== 2. إصدارات الخدمة (Service Versions) ==========
class ServiceVersion(Base):
    __tablename__ = "service_versions"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("marketplace_services.id"), nullable=False, index=True)
    version = Column(String(20), nullable=False)
    changelog = Column(Text, nullable=True)
    database_schema = Column(JSONB, nullable=True)
    api_blueprint = Column(JSONB, nullable=True)
    frontend_template_url = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_service_version_service", "service_id"),
        Index("ix_service_version_created_at", "created_at"),
    )


# ========== 3. تراخيص المستخدمين للتطبيقات المشتراة ==========
class ServiceLicense(Base):
    __tablename__ = "service_licenses"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("marketplace_services.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    buyer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    deployed_domain = Column(String(255), nullable=True)
    deployment_status = Column(SQLEnum(DeploymentStatus), default=DeploymentStatus.PENDING)
    deployment_log = Column(Text, nullable=True)

    subscription_plan = Column(SQLEnum(SubscriptionPlan), default=SubscriptionPlan.FREE)
    purchased_addons = Column(JSONB, default=list)
    custom_config = Column(JSONB, default=dict)

    paid_amount_mrusdt = Column(Numeric(30, 8), default=0)
    subscription_start = Column(DateTime(timezone=True), nullable=True)
    subscription_end = Column(DateTime(timezone=True), nullable=True)
    auto_renew = Column(Boolean, default=True)

    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_license_tenant_service", "tenant_id", "service_id"),
        Index("ix_license_status", "deployment_status"),
        Index("ix_license_created_at", "created_at"),
        Index("ix_license_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


# ========== 4. الإضافات (Add-ons) ==========
class ServiceAddon(Base):
    __tablename__ = "service_addons"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    addon_type = Column(String(50), nullable=False)
    version = Column(String(20), default="1.0.0")

    compatible_service_types = Column(JSONB, default=list)

    database_schema = Column(JSONB, nullable=True)
    api_blueprint = Column(JSONB, nullable=True)
    frontend_component_url = Column(String(512), nullable=True)

    price_mrusdt = Column(Numeric(30, 8), default=0)

    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_addon_tenant_type", "tenant_id", "addon_type"),
        Index("ix_addon_created_at", "created_at"),
    )


# ========== 5. طلبات التخصيص ==========
class CustomizationRequest(Base):
    __tablename__ = "customization_requests"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    license_id = Column(Integer, ForeignKey("service_licenses.id"), nullable=False, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    proposed_budget_mrusdt = Column(Numeric(30, 8), nullable=True)

    status = Column(String(50), default="PENDING")
    assigned_developer_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_customization_tenant_status", "tenant_id", "status"),
        Index("ix_customization_license", "license_id"),
        Index("ix_customization_created_at", "created_at"),
        Index("ix_customization_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


# ========== 6. شراء الإضافات (Add-on Purchases) مع Idempotency ==========
class ServiceAddonPurchase(Base):
    __tablename__ = "service_addon_purchases"

    id = Column(Integer, primary_key=True, index=True)
    license_id = Column(Integer, ForeignKey("service_licenses.id"), nullable=False, index=True)
    addon_id = Column(Integer, ForeignKey("service_addons.id"), nullable=False, index=True)

    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    price_paid_mrusdt = Column(Numeric(30, 8), default=0)
    purchased_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_addon_purchase_license", "license_id"),
        Index("ix_addon_purchase_addon", "addon_id"),
        Index("ix_addon_purchase_license_addon", "license_id", "addon_id", unique=True, postgresql_where=text("idempotency_key IS NULL")),
        Index("ix_addon_purchase_created_at", "purchased_at"),
        Index("ix_addon_purchase_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )