# app/domains/commerce/models.py
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, Text, Boolean,
    Numeric, DateTime, Index, CheckConstraint, text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base

# ========== المتاجر والتصنيفات ==========
class StoreProfile(Base):
    __tablename__ = "store_profiles"
    __table_args__ = (
        Index("ix_store_profiles_tenant_id", "tenant_id"),
        Index("ix_store_profiles_is_active", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    currency = Column(String(10), default="MR_USDT")
    tax_rate = Column(Numeric(5, 2), default=0)
    settlement_type = Column(String(50), default="WEB2_FIAT")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    owner_email = Column(String(255), nullable=True)
    is_affiliate_enabled = Column(Boolean, default=True)


class ProductCategory(Base):
    __tablename__ = "product_categories"
    __table_args__ = (
        Index("ix_product_categories_store_id", "store_id"),
        Index("ix_product_categories_parent_id", "parent_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("store_profiles.id"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("product_categories.id"), nullable=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_store_published", "store_id", "is_published"),
        Index("ix_products_title", "title"),
        Index("ix_products_is_active", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("store_profiles.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("product_categories.id"), nullable=True, index=True)

    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    product_type = Column(String(50), nullable=False)  # PHYSICAL, DIGITAL, SERVICE, COURSE

    base_price_mrusdt = Column(Numeric(30, 8), nullable=False)

    seo_metadata = Column(JSONB, default=dict)
    media_gallery = Column(JSONB, default=list)

    is_affiliate_eligible = Column(Boolean, default=True)
    affiliate_model = Column(String(50), default="FLAT_RATE")
    affiliate_reward_percentage = Column(Numeric(5, 2), default=0)
    max_affiliate_tiers = Column(Integer, default=1)
    custom_affiliate_tiers = Column(JSONB, nullable=True)

    is_published = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ProductVariant(Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        Index("ix_product_variants_product_id", "product_id"),
        Index("ix_product_variants_sku", "sku"),
    )

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)

    sku = Column(String(100), nullable=False, index=True)
    attributes = Column(JSONB, default=dict)

    price_mrusdt = Column(Numeric(30, 8), nullable=False)
    discount_price = Column(Numeric(30, 8), nullable=True)
    discount_end_date = Column(DateTime(timezone=True), nullable=True)

    stock_quantity = Column(Integer, default=0)
    is_wholesale_enabled = Column(Boolean, default=False)
    wholesale_min_qty = Column(Integer, nullable=True)
    wholesale_price_mrusdt = Column(Numeric(30, 8), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ========== العناوين والشحن ==========
class Address(Base):
    __tablename__ = "addresses"
    __table_args__ = (
        Index("ix_addresses_user_id", "user_id"),
        Index("ix_addresses_country_city", "country", "city"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    country = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    street_line1 = Column(String(255), nullable=False)
    street_line2 = Column(String(255), nullable=True)

    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)

    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ========== الطلبات (مع tenant_id) ==========
class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_customer_status", "customer_id", "status"),
        Index("ix_orders_store_id", "store_id"),
        Index("ix_orders_created_status", "created_at", "status"),
        Index("ix_orders_created_at", "created_at"),
        Index("ix_orders_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
        Index("ix_orders_affiliate_code", "affiliate_code_used"),
        Index("ix_orders_tenant_id", "tenant_id"),
        Index("ix_orders_tenant_status", "tenant_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("store_profiles.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    transaction_id = Column(Integer, nullable=True)

    total_amount_mrusdt = Column(Numeric(30, 8), nullable=False)
    discount_applied = Column(Numeric(30, 8), default=0)
    tax_amount = Column(Numeric(30, 8), default=0)
    shipping_fee = Column(Numeric(30, 8), default=0)

    shipping_address_id = Column(Integer, ForeignKey("addresses.id"), nullable=True)

    status = Column(String(50), default="PENDING_PAYMENT")
    settlement_type = Column(String(50), default="WEB2_FIAT")

    affiliate_code_used = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        Index("ix_order_items_order_id", "order_id"),
        Index("ix_order_items_product_id", "product_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)

    quantity = Column(Integer, nullable=False)
    unit_price_mrusdt = Column(Numeric(30, 8), nullable=False)
    total_price_mrusdt = Column(Numeric(30, 8), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ========== نظام الإحالة (Affiliate 10x) ==========
class AffiliateTree(Base):
    __tablename__ = "affiliate_trees"
    __table_args__ = (
        Index("ix_affiliate_trees_user_id", "user_id", unique=True),
        Index("ix_affiliate_trees_sponsor_id", "sponsor_id"),
        Index("ix_affiliate_trees_network_depth", "network_depth"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    sponsor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    network_depth = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CommissionRecord(Base):
    __tablename__ = "commission_records"
    __table_args__ = (
        Index("ix_commission_records_beneficiary_id", "beneficiary_id"),
        Index("ix_commission_records_order_id", "order_id"),
        Index("ix_commission_records_status", "status"),
        Index("ix_commission_records_level_earned", "level_earned"),
    )

    id = Column(Integer, primary_key=True, index=True)
    beneficiary_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    level_earned = Column(Integer, nullable=False)
    amount = Column(Numeric(30, 8), nullable=False)
    currency = Column(String(20), default="MR_USDT")
    status = Column(String(50), default="PENDING")
    release_date = Column(DateTime(timezone=True), nullable=True)
    release_tx_hash = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AffiliateConfig(Base):
    __tablename__ = "affiliate_configs"
    __table_args__ = (
        Index("ix_affiliate_configs_tenant_id", "tenant_id", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    is_active = Column(Boolean, default=True)

    level_1_pct = Column(Numeric(5, 2), default=10.0)
    level_2_pct = Column(Numeric(5, 2), default=5.0)
    level_3_pct = Column(Numeric(5, 2), default=1.0)
    level_4_pct = Column(Numeric(5, 2), default=1.0)
    level_5_pct = Column(Numeric(5, 2), default=1.0)
    level_6_pct = Column(Numeric(5, 2), default=1.0)
    level_7_pct = Column(Numeric(5, 2), default=1.0)
    level_8_pct = Column(Numeric(5, 2), default=0.0)
    level_9_pct = Column(Numeric(5, 2), default=0.0)
    level_10_pct = Column(Numeric(5, 2), default=0.0)

    system_fee_pct = Column(Numeric(5, 2), default=5.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ========== طرق الدفع الإضافية (مع tenant_id) ==========
class PaymentRequest(Base):
    __tablename__ = "payment_requests"
    __table_args__ = (
        Index("ix_payment_requests_order_id", "order_id"),
        Index("ix_payment_requests_agent_code", "agent_code", unique=True),
        Index("ix_payment_requests_gateway_transaction_id", "gateway_transaction_id"),
        Index("ix_payment_requests_status", "status"),
        Index("ix_payment_requests_payment_method", "payment_method"),
        Index("ix_payment_requests_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
        Index("ix_payment_requests_tenant_id", "tenant_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_method = Column(String(50), nullable=False)
    amount = Column(Numeric(30, 8), nullable=False)
    currency = Column(String(20), nullable=False)

    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    agent_code = Column(String(20), unique=True, nullable=True)
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    agent_confirmed_at = Column(DateTime(timezone=True), nullable=True)

    gateway_transaction_id = Column(String(255), nullable=True, index=True)
    gateway_response = Column(JSONB, nullable=True)

    status = Column(String(50), default="PENDING")
    paid_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ========== ✅ سجل التدقيق التجاري (مع tenant_id) ==========
class CommerceAuditLog(Base):
    __tablename__ = "commerce_audit_logs"
    __table_args__ = (
        Index("ix_commerce_audit_logs_user_id", "user_id"),
        Index("ix_commerce_audit_logs_order_id", "order_id"),
        Index("ix_commerce_audit_logs_action", "action"),
        Index("ix_commerce_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_commerce_audit_logs_created_at", "created_at"),
        Index("ix_commerce_audit_logs_tenant_id", "tenant_id"),
        Index("ix_commerce_audit_logs_tenant_user", "tenant_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True, index=True)
    action = Column(String(50), nullable=False)
    details = Column(JSONB, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())