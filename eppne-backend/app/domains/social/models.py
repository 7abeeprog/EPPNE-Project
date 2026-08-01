# app/domains/social/models.py (الإصدار النهائي المتكامل مع جميع التحسينات)
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, Enum as SQLEnum, Index, CheckConstraint, text
)
from sqlalchemy.dialects.postgresql import JSONB  # ✅ تم إضافة الاستيراد الصحيح
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class PostType(str, enum.Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    POLL = "POLL"
    DOCUMENT = "DOCUMENT"

class GroupPrivacy(str, enum.Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    SECRET = "SECRET"

class EventApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class ConnectionType(str, enum.Enum):
    FOLLOW = "FOLLOW"
    FRIEND = "FRIEND"
    COLLEAGUE = "COLLEAGUE"
    MENTOR = "MENTOR"

# ========== 1. المنشورات والتفاعلات (مع Multi-Tenancy + Idempotency) ==========
class Post(Base):
    __tablename__ = "social_posts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    page_id = Column(Integer, ForeignKey("social_pages.id", ondelete="SET NULL"), nullable=True)
    group_id = Column(Integer, ForeignKey("social_groups.id", ondelete="SET NULL"), nullable=True)

    content = Column(Text, nullable=True)
    post_type = Column(SQLEnum(PostType), default=PostType.TEXT)
    media_urls = Column(JSONB, default=list)

    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)

    share_reward_mr7 = Column(Numeric(15, 8), default=0)
    on_chain_post_tx = Column(String(100), nullable=True)

    green_tag_verified = Column(Boolean, default=False)

    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_social_posts_author", "author_id", "created_at"),
        Index("ix_social_posts_created_at", "created_at"),
        Index("ix_social_posts_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


class PostComment(Base):
    __tablename__ = "social_post_comments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    post_id = Column(Integer, ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    parent_comment_id = Column(Integer, ForeignKey("social_post_comments.id", ondelete="CASCADE"), nullable=True)

    content = Column(Text, nullable=False)
    likes_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_post_comment_created_at", "created_at"),
        Index("ix_post_comment_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


class PostLike(Base):
    __tablename__ = "social_post_likes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    post_id = Column(Integer, ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_social_like_unique", "post_id", "user_id", unique=True),
        Index("ix_social_like_created_at", "created_at"),
        Index("ix_social_like_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


# ========== 2. الصفحات والمجموعات (مع Multi-Tenancy كاملة) ==========
class SocialPage(Base):
    __tablename__ = "social_pages"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    about = Column(Text, nullable=True)

    is_verified = Column(Boolean, default=False)
    page_wallet_address = Column(String(42), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_social_page_created_at", "created_at"),
    )


class SocialGroup(Base):
    __tablename__ = "social_groups"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    privacy = Column(SQLEnum(GroupPrivacy), default=GroupPrivacy.PUBLIC)

    linked_project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    dao_contract_address = Column(String(42), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_social_group_created_at", "created_at"),
    )


class GroupMember(Base):
    __tablename__ = "social_group_members"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    group_id = Column(Integer, ForeignKey("social_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), default="MEMBER")
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_group_member_unique", "group_id", "user_id", unique=True),
        Index("ix_group_member_created_at", "joined_at"),
        Index("ix_group_member_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


# ========== 3. العقود الاجتماعية الذكية (مع Multi-Tenancy + Idempotency) ==========
class SocialContractTemplate(Base):
    __tablename__ = "social_contract_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    template_schema = Column(JSONB, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_social_contract_template_created_at", "created_at"),
    )


class SocialSmartContract(Base):
    __tablename__ = "social_smart_contracts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("social_contract_templates.id", ondelete="SET NULL"), nullable=True)

    contract_type = Column(String(50), index=True)
    title = Column(String(255), nullable=False)
    terms_and_conditions = Column(JSONB, nullable=False)

    status = Column(String(50), default="DRAFT")
    smart_contract_address = Column(String(42), nullable=True)
    blockchain_tx_hash = Column(String(100), unique=True, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_social_smart_contract_created_at", "created_at"),
        Index("ix_social_smart_contract_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


class ContractSignature(Base):
    __tablename__ = "social_contract_signatures"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    contract_id = Column(Integer, ForeignKey("social_smart_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    signer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    digital_signature_hash = Column(String(512), nullable=False)
    signed_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_contract_signature_unique", "contract_id", "signer_id", unique=True),
        Index("ix_contract_signature_created_at", "signed_at"),
        Index("ix_contract_signature_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


# ========== 4. الفعاليات الاجتماعية (مع Multi-Tenancy) ==========
class SocialEvent(Base):
    __tablename__ = "social_events"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("social_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    page_id = Column(Integer, ForeignKey("social_pages.id", ondelete="SET NULL"), nullable=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(String(50), index=True)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    location_details = Column(JSONB, nullable=True)

    requires_approval = Column(Boolean, default=True)
    approval_status = Column(SQLEnum(EventApprovalStatus), default=EventApprovalStatus.PENDING)
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_social_event_created_at", "created_at"),
    )


class EventAttendee(Base):
    __tablename__ = "social_event_attendees"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    event_id = Column(Integer, ForeignKey("social_events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="GOING")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_event_attendee_unique", "event_id", "user_id", unique=True),
        Index("ix_event_attendee_created_at", "created_at"),
        Index("ix_event_attendee_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


# ========== 5. الذكاء الاصطناعي للتعارف والتوافق (مع Multi-Tenancy) ==========
class AIMatchProfile(Base):
    __tablename__ = "ai_match_profiles"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    seek_type = Column(JSONB, nullable=False)
    ai_preferences = Column(JSONB, nullable=False)

    is_discoverable = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_ai_match_profile_created_at", "created_at"),
    )


class UserConnection(Base):
    __tablename__ = "user_connections"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    user_a_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user_b_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    connection_type = Column(SQLEnum(ConnectionType), nullable=False)
    match_score = Column(Numeric(5, 2), nullable=True)
    status = Column(String(50), default="PENDING")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_user_connection_pair", "user_a_id", "user_b_id", unique=True),
        Index("ix_user_connection_created_at", "created_at"),
        Index("ix_user_connection_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
        CheckConstraint("user_a_id != user_b_id", name="check_no_self_connection"),
    )


# ========== 6. الأنظمة الجديدة ==========

# 6.1 نظام التذكير (Reminders)
class UserOccasion(Base):
    __tablename__ = "user_occasions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    occasion_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    occasion_date = Column(DateTime(timezone=True), nullable=False)
    is_public = Column(Boolean, default=False)

    remind_days_before = Column(Integer, default=7)
    last_reminder_sent = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_occasion_user_date", "user_id", "occasion_date"),
        Index("ix_occasion_tenant", "tenant_id"),
        Index("ix_user_occasion_created_at", "created_at"),
    )


class OccasionReminder(Base):
    __tablename__ = "occasion_reminders"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    occasion_id = Column(Integer, ForeignKey("user_occasions.id", ondelete="CASCADE"), nullable=False, index=True)
    friend_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    reminder_type = Column(String(50), default="SYSTEM")
    reminder_date = Column(DateTime(timezone=True), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="PENDING")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_reminder_occasion", "occasion_id"),
        Index("ix_reminder_tenant", "tenant_id"),
        Index("ix_occasion_reminder_created_at", "created_at"),
    )


# 6.2 نظام الهدايا (Gifts)
class DigitalGift(Base):
    __tablename__ = "digital_gifts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    occasion_id = Column(Integer, ForeignKey("user_occasions.id", ondelete="SET NULL"), nullable=True)

    gift_type = Column(String(50), nullable=False)
    gift_value_mrusdt = Column(Numeric(30, 8), default=0)
    gift_message = Column(Text, nullable=True)
    gift_metadata = Column(JSONB, default=dict)

    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    is_redeemed = Column(Boolean, default=False)
    redeemed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_digital_gift_sender", "sender_id"),
        Index("ix_digital_gift_receiver", "receiver_id"),
        Index("ix_digital_gift_tenant", "tenant_id"),
        Index("ix_digital_gift_created_at", "created_at"),
        Index("ix_digital_gift_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


class PhysicalGiftRequest(Base):
    __tablename__ = "physical_gift_requests"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    occasion_id = Column(Integer, ForeignKey("user_occasions.id", ondelete="SET NULL"), nullable=True)

    product_id = Column(Integer, nullable=True)
    product_name = Column(String(255), nullable=False)
    product_description = Column(Text, nullable=True)
    product_price_mrusdt = Column(Numeric(30, 8), nullable=False)

    shipping_address = Column(JSONB, nullable=False)
    shipping_status = Column(String(50), default="PENDING")

    payment_tx_hash = Column(String(100), nullable=True)
    order_tracking_number = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_physical_gift_sender", "sender_id"),
        Index("ix_physical_gift_receiver", "receiver_id"),
        Index("ix_physical_gift_tenant", "tenant_id"),
        Index("ix_physical_gift_created_at", "created_at"),
        Index("ix_physical_gift_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


class GiftReminder(Base):
    __tablename__ = "gift_reminders"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    occasion_id = Column(Integer, ForeignKey("user_occasions.id", ondelete="CASCADE"), nullable=False, index=True)
    friend_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    reminder_sent_at = Column(DateTime(timezone=True), server_default=func.now())
    is_acknowledged = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_gift_reminder_occasion", "occasion_id"),
        Index("ix_gift_reminder_tenant", "tenant_id"),
        Index("ix_gift_reminder_created_at", "created_at"),
    )


# 6.3 نظام SaaS للمجموعات (Group Subscriptions)
class GroupFeature(Base):
    __tablename__ = "group_features"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    feature_name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_enabled_by_default = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_group_feature_tenant", "tenant_id"),
        Index("ix_group_feature_created_at", "created_at"),
    )


class GroupSubscriptionPlan(Base):
    __tablename__ = "group_subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price_monthly_mrusdt = Column(Numeric(30, 8), default=0)
    price_yearly_mrusdt = Column(Numeric(30, 8), default=0)

    included_features = Column(JSONB, default=list)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_subscription_plan_tenant", "tenant_id"),
        Index("ix_group_subscription_plan_created_at", "created_at"),
    )


class GroupSubscription(Base):
    __tablename__ = "group_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    group_id = Column(Integer, ForeignKey("social_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("group_subscription_plans.id", ondelete="RESTRICT"), nullable=False, index=True)

    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    auto_renew = Column(Boolean, default=True)

    status = Column(String(50), default="ACTIVE")
    payment_tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_group_subscription_group", "group_id"),
        Index("ix_group_subscription_tenant", "tenant_id"),
        Index("ix_group_subscription_created_at", "created_at"),
        Index("ix_group_subscription_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )