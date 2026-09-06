# app/domains/affiliate/models.py
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, Text, Boolean,
    Numeric, DateTime, JSON, Index, CheckConstraint, text, Enum as SQLEnum
)
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.enums import AffiliateStatus, CommissionStatus
import enum

class AffiliateProfile(Base):
    """ملف الداعي السيادي"""
    __tablename__ = "affiliate_profiles"
    __table_args__ = (
        Index("ix_affiliate_profiles_user_id", "user_id", unique=True),
        Index("ix_affiliate_profiles_tenant_id", "tenant_id"),
        Index("ix_affiliate_profiles_referral_code", "referral_code", unique=True),
        Index("ix_affiliate_profiles_is_active", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    referral_code = Column(String(20), unique=True, nullable=False, index=True)
    custom_slug = Column(String(50), unique=True, nullable=True)

    default_commission_rate = Column(Numeric(5, 2), default=5.0)
    is_active = Column(Boolean, default=True)

    total_clicks = Column(Integer, default=0)
    total_conversions = Column(Integer, default=0)
    total_earned = Column(Numeric(30, 8), default=0)
    total_paid = Column(Numeric(30, 8), default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AffiliateScopeType(str, enum.Enum):
    """نوع نطاق العمولة — راجع migration 045 وتقرير الجلسة
    referral-affiliate-unified-implementation-session-log.md §1."""
    SINGLE_PRODUCT = "SINGLE_PRODUCT"
    PRODUCT_GROUP = "PRODUCT_GROUP"
    ENTITY_WIDE = "ENTITY_WIDE"


class AffiliateScope(Base):
    """نطاق عمولة: منتج فردي، مجموعة منتجات، أو كل مبيعات الكيان
    (tenant). ReferralTree.entity_id وCommissionTier.target_scope_id
    وCommission.scope_id تشير كلها لهذا الجدول — نفس المستخدم يمكن أن
    يكون له شجر/عمولات منفصلة تمامًا لكل نطاق، لا تتداخل."""
    __tablename__ = "affiliate_scopes"
    __table_args__ = (
        Index("ix_affiliate_scopes_tenant_id", "tenant_id"),
        Index("ix_affiliate_scopes_scope_type", "scope_type"),
        Index("ix_affiliate_scopes_tenant_entity_wide_unique",
              "tenant_id", unique=True,
              postgresql_where=text("scope_type = 'ENTITY_WIDE'")),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    scope_type = Column(SQLEnum(AffiliateScopeType), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AffiliateScopeMember(Base):
    """عضوية "شيء قابل للبيع" داخل نطاق — منتج commerce، كورس academy،
    أو نوع حدث من أحد الـ12 دومين (member_id=NULL لعضوية دومين كامل
    بلا معرّف فردي، مثال: كل أحداث زمكانة). عضو واحد (member_type +
    member_id) لا يمكن أن يكون في أكثر من نطاق واحد فعّال — يمنع
    غموض "أي نسبة عمولة تُطبَّق؟"."""
    __tablename__ = "affiliate_scope_members"
    __table_args__ = (
        Index("ix_affiliate_scope_members_scope_id", "scope_id"),
        Index("ix_affiliate_scope_members_unique_typed",
              "member_type", "member_id", unique=True,
              postgresql_where=text("member_id IS NOT NULL")),
        Index("ix_affiliate_scope_members_unique_untyped",
              "member_type", unique=True,
              postgresql_where=text("member_id IS NULL")),
    )

    id = Column(Integer, primary_key=True, index=True)
    scope_id = Column(Integer, ForeignKey("affiliate_scopes.id", ondelete="CASCADE"), nullable=False, index=True)
    member_type = Column(String(30), nullable=False)
    member_id = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ReferralTree(Base):
    """شجرة الإحالة المخصصة (Scope-Based Affiliate)"""
    __tablename__ = "referral_trees"
    __table_args__ = (
        Index("ix_referral_trees_tenant_id", "tenant_id"),
        Index("ix_referral_trees_referrer_id", "referrer_id"),
        Index("ix_referral_trees_referred_id", "referred_id"),
        Index("ix_referral_trees_unique_referred_scope",
              "referred_id", "entity_type", text("COALESCE(entity_id, 0)"), unique=True),
        Index("ix_referral_trees_depth", "depth"),
        Index("ix_referral_trees_entity_type", "entity_type"),
        Index("ix_referral_trees_entity_id", "entity_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    referrer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    referred_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # entity_type دائمًا "SCOPE" للصفوف الجديدة (بعد migration 045) —
    # القيمة تبقى String عامة (بلا Enum) عمدًا، لأن القيد الفريد أدناه
    # يعتمد على قيمتها الخام بغض النظر عن معناها.
    entity_type = Column(String(50), default="GLOBAL", nullable=False)
    entity_id = Column(Integer, ForeignKey("affiliate_scopes.id", ondelete="CASCADE"), nullable=True)

    depth = Column(Integer, nullable=False, default=1)
    path = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Commission(Base):
    """سجل العمولات المستحقة والمحررة — معمَّم ليقبل أي مصدر بيع
    (commerce order، academy enrollment، أو حدث من أحد الـ12 دومين)،
    وليس order_id فقط. order_id/order_item_id/product_id nullable
    الآن — تُملأ فقط لو source_type == "COMMERCE_ORDER"."""
    __tablename__ = "affiliate_commissions"
    __table_args__ = (
        Index("ix_affiliate_commissions_affiliate_id", "affiliate_id"),
        Index("ix_affiliate_commissions_order_id", "order_id"),
        Index("ix_affiliate_commissions_user_id", "user_id"),
        Index("ix_affiliate_commissions_product_id", "product_id"),
        Index("ix_affiliate_commissions_status", "status"),
        Index("ix_affiliate_commissions_created_at", "created_at"),
        Index("ix_affiliate_commissions_tenant_id", "tenant_id"),
        Index("ix_affiliate_commissions_scope_id", "scope_id"),
        Index("ix_affiliate_commissions_source_type", "source_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    affiliate_id = Column(Integer, ForeignKey("affiliate_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=True, index=True)
    order_item_id = Column(Integer, ForeignKey("order_items.id", ondelete="CASCADE"), nullable=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # المصدر العام لحدث البيع — بديل عن الاعتماد الحصري على order_id
    source_type = Column(String(30), nullable=False)  # COMMERCE_ORDER | ACADEMY_ENROLLMENT | ZAMAKANA | TRANSPORT | ...
    source_id = Column(Integer, nullable=True)         # order_item_id لو COMMERCE_ORDER، enrollment_id لو ACADEMY، إلخ
    scope_id = Column(Integer, ForeignKey("affiliate_scopes.id", ondelete="RESTRICT"), nullable=False, index=True)

    item_amount = Column(Numeric(30, 8), nullable=False)
    order_amount = Column(Numeric(30, 8), nullable=False)
    commission_rate = Column(Numeric(5, 2), nullable=False)
    commission_amount = Column(Numeric(30, 8), nullable=False)
    currency = Column(String(20), default="MR_USDT")

    referral_level = Column(Integer, nullable=False)
    entity_type = Column(String(50), default="PRODUCT")

    status = Column(String(20), default="PENDING")
    paid_at = Column(DateTime(timezone=True), nullable=True)
    paid_tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CommissionTier(Base):
    """إعدادات نسب العمولات حسب المستوى لكل مستأجر (مع دعم النطاقات)"""
    __tablename__ = "affiliate_commission_tiers"
    __table_args__ = (
        Index("ix_affiliate_commission_tiers_tenant_id", "tenant_id"),
        Index("ix_affiliate_commission_tiers_target_scope", "target_scope_id"),
        Index("ix_affiliate_commission_tiers_unique", "tenant_id", "entity_type", "target_scope_id", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    entity_type = Column(String(50), default="GLOBAL")
    target_scope_id = Column(Integer, ForeignKey("affiliate_scopes.id", ondelete="CASCADE"), nullable=True)

    level_1_pct = Column(Numeric(5, 2), default=10.0)
    level_2_pct = Column(Numeric(5, 2), default=5.0)
    level_3_pct = Column(Numeric(5, 2), default=3.0)
    level_4_pct = Column(Numeric(5, 2), default=2.0)
    level_5_pct = Column(Numeric(5, 2), default=2.0)
    level_6_pct = Column(Numeric(5, 2), default=1.0)
    level_7_pct = Column(Numeric(5, 2), default=1.0)
    level_8_pct = Column(Numeric(5, 2), default=0.5)
    level_9_pct = Column(Numeric(5, 2), default=0.5)
    level_10_pct = Column(Numeric(5, 2), default=0.0)

    system_fee_pct = Column(Numeric(5, 2), default=5.0)
    min_withdrawal = Column(Numeric(30, 8), default=10.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AffiliateLink(Base):
    """روابط الدعوة المخصصة"""
    __tablename__ = "affiliate_links"
    __table_args__ = (
        Index("ix_affiliate_links_tenant_id", "tenant_id"),
        Index("ix_affiliate_links_affiliate_id", "affiliate_id"),
        Index("ix_affiliate_links_target", "target"),
        Index("ix_affiliate_links_product_id", "product_id"),
        Index("ix_affiliate_links_utm_campaign", "utm_campaign"),
        Index("ix_affiliate_links_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    affiliate_id = Column(Integer, ForeignKey("affiliate_profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    target = Column(String(255), nullable=False)
    target_id = Column(Integer, nullable=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=True)

    utm_source = Column(String(100), nullable=True)
    utm_medium = Column(String(100), nullable=True)
    utm_campaign = Column(String(100), nullable=True)

    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)

    status = Column(String(20), default="ACTIVE", nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AffiliateClickLog(Base):
    """سجل نقرات روابط الدعوة (للتحليلات)"""
    __tablename__ = "affiliate_click_logs"
    __table_args__ = (
        Index("ix_affiliate_click_logs_tenant_id", "tenant_id"),
        Index("ix_affiliate_click_logs_link_id", "link_id"),
        Index("ix_affiliate_click_logs_affiliate_id", "affiliate_id"),
        Index("ix_affiliate_click_logs_ip_address", "ip_address"),
        Index("ix_affiliate_click_logs_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    link_id = Column(Integer, ForeignKey("affiliate_links.id", ondelete="CASCADE"), nullable=False, index=True)
    affiliate_id = Column(Integer, ForeignKey("affiliate_profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    referer_url = Column(String(500), nullable=True)

    converted = Column(Boolean, default=False)
    converted_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())