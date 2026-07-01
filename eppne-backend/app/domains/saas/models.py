# app/domains/saas/models.py
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, Text, Boolean,
    Numeric, DateTime, JSON, Index, CheckConstraint, text
)
from sqlalchemy.sql import func
from app.core.database import Base


class ServiceCatalog(Base):
    __tablename__ = "saas_service_catalog"
    __table_args__ = (
        Index("ix_saas_service_catalog_code", "code", unique=True),
        Index("ix_saas_service_catalog_is_active", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    icon = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ServicePlan(Base):
    __tablename__ = "saas_service_plans"
    __table_args__ = (
        Index("ix_saas_service_plans_service_id", "service_id"),
        Index("ix_saas_service_plans_code", "service_id", "code", unique=True),
        Index("ix_saas_service_plans_is_active", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("saas_service_catalog.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=False)

    price_monthly = Column(Numeric(30, 8), nullable=False)
    price_yearly = Column(Numeric(30, 8), nullable=False)
    currency = Column(String(20), default="MR_USDT")

    features = Column(JSON, default=list)
    max_users = Column(Integer, default=10)
    max_products = Column(Integer, default=50)
    max_courses = Column(Integer, default=20)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TenantSubscription(Base):
    __tablename__ = "saas_tenant_subscriptions"
    __table_args__ = (
        Index("ix_saas_tenant_subscriptions_tenant_id", "tenant_id"),
        Index("ix_saas_tenant_subscriptions_plan_id", "plan_id"),
        Index("ix_saas_tenant_subscriptions_status", "status"),
        Index("ix_saas_tenant_subscriptions_next_billing", "next_billing_date"),
        Index("ix_saas_tenant_subscriptions_idempotency", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("saas_service_plans.id"), nullable=False, index=True)

    # ✅ Idempotency Key للفوترة (يمنع تكرار الفواتير)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    status = Column(String(50), default="ACTIVE")  # ACTIVE, PAST_DUE, EXPIRED, CANCELLED, TRIAL
    grace_period_end_date = Column(DateTime(timezone=True), nullable=True)  # ✅ فترة السماح

    trial_end_date = Column(DateTime(timezone=True), nullable=True)
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=True)
    next_billing_date = Column(DateTime(timezone=True), nullable=True)

    payment_method = Column(String(50), default="WALLET")
    auto_renew = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TenantServiceAccess(Base):
    __tablename__ = "saas_tenant_service_access"
    __table_args__ = (
        Index("ix_saas_tenant_service_access_tenant_id", "tenant_id"),
        Index("ix_saas_tenant_service_access_service_id", "service_id"),
        Index("ix_saas_tenant_service_access_unique", "tenant_id", "service_id", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    service_id = Column(Integer, ForeignKey("saas_service_catalog.id"), nullable=False, index=True)

    access_level = Column(String(50), default="BASIC")
    user_limit = Column(Integer, nullable=True)
    storage_limit = Column(Integer, nullable=True)
    api_calls_limit = Column(Integer, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Invoice(Base):
    __tablename__ = "saas_invoices"
    __table_args__ = (
        Index("ix_saas_invoices_tenant_id", "tenant_id"),
        Index("ix_saas_invoices_subscription_id", "subscription_id"),
        Index("ix_saas_invoices_status", "status"),
        Index("ix_saas_invoices_invoice_number", "invoice_number", unique=True),
        Index("ix_saas_invoices_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("saas_tenant_subscriptions.id"), nullable=False, index=True)

    invoice_number = Column(String(50), unique=True, nullable=False)
    amount = Column(Numeric(30, 8), nullable=False)
    currency = Column(String(20), default="MR_USDT")

    description = Column(Text, nullable=True)
    items = Column(JSON, default=list)

    status = Column(String(50), default="PENDING")
    due_date = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    paid_tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TenantFeatureFlag(Base):
    __tablename__ = "saas_tenant_feature_flags"
    __table_args__ = (
        Index("ix_saas_tenant_feature_flags_unique", "tenant_id", "service_id", "feature_key", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    service_id = Column(Integer, ForeignKey("saas_service_catalog.id"), nullable=False, index=True)

    feature_key = Column(String(100), nullable=False)
    is_enabled = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ============================================================
# 🆕 النماذج الجديدة (SaaS Plan & Subscription المرنة)
# ============================================================
class SaaSPlan(Base):
    __tablename__ = "saas_plans"
    __table_args__ = (
        Index("ix_saas_plans_code", "code", unique=True),
        Index("ix_saas_plans_is_active", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    price_monthly = Column(Numeric(30, 8), nullable=False)
    price_yearly = Column(Numeric(30, 8), nullable=False)
    currency = Column(String(20), default="MR_USDT")

    # 🔥 ميزات الخطة كـ JSON (مرنة)
    features = Column(JSON, default=dict)  # {"ai_agents": true, "max_agents": 5, "monthly_ai_calls": 500, ...}

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SaaSSubscription(Base):
    __tablename__ = "saas_subscriptions"
    __table_args__ = (
        Index("ix_saas_subscriptions_tenant_id", "tenant_id"),
        Index("ix_saas_subscriptions_plan_id", "plan_id"),
        Index("ix_saas_subscriptions_status", "status"),
        Index("ix_saas_subscriptions_end_date", "end_date"),
        Index("ix_saas_subscriptions_idempotency", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("saas_plans.id"), nullable=False, index=True)

    # ✅ Idempotency Key للفوترة
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    status = Column(String(50), default="ACTIVE")  # ACTIVE, EXPIRED, CANCELLED, TRIAL, PAST_DUE

    # 🔥 حقل الميزات (JSONB) – يحتوي على حدود الـ AI وغيرها (يمكن أن يورث من الخطة أو يتجاوزها)
    features = Column(JSON, default=dict)  # {"ai_agents": true, "max_agents": 5, "monthly_ai_calls": 500}

    # 🔥 حقل جديد لنقاط التفتيش الشهرية
    last_billed_month = Column(DateTime(timezone=True), nullable=True)

    trial_end_date = Column(DateTime(timezone=True), nullable=True)
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=True)
    next_billing_date = Column(DateTime(timezone=True), nullable=True)

    payment_method = Column(String(50), default="WALLET")
    auto_renew = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())