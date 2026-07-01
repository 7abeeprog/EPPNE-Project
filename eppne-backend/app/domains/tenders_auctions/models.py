# app/domains/social/models.py (الإصدار النهائي المتكامل مع إضافة tenders_auctions)
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, JSON, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum

# ========== الأنواع المساعدة للتواصل الاجتماعي ==========
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
    page_id = Column(Integer, nullable=True)
    group_id = Column(Integer, nullable=True)

    content = Column(Text, nullable=True)
    post_type = Column(SQLEnum(PostType), default=PostType.TEXT)
    media_urls = Column(JSON, default=list)

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
    )


class PostComment(Base):
    __tablename__ = "social_post_comments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    post_id = Column(Integer, ForeignKey("social_posts.id"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    parent_comment_id = Column(Integer, ForeignKey("social_post_comments.id"), nullable=True)

    content = Column(Text, nullable=False)
    likes_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)


class PostLike(Base):
    __tablename__ = "social_post_likes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    post_id = Column(Integer, ForeignKey("social_posts.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_social_like_unique", "post_id", "user_id", unique=True),
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


class SocialGroup(Base):
    __tablename__ = "social_groups"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    privacy = Column(SQLEnum(GroupPrivacy), default=GroupPrivacy.PUBLIC)

    linked_project_id = Column(Integer, nullable=True)
    dao_contract_address = Column(String(42), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)


class GroupMember(Base):
    __tablename__ = "social_group_members"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    group_id = Column(Integer, ForeignKey("social_groups.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(50), default="MEMBER")
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_group_member_unique", "group_id", "user_id", unique=True),
    )


# ========== 3. العقود الاجتماعية الذكية (مع Multi-Tenancy + Idempotency) ==========
class SocialContractTemplate(Base):
    __tablename__ = "social_contract_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    template_schema = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SocialSmartContract(Base):
    __tablename__ = "social_smart_contracts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("social_contract_templates.id"), nullable=True)

    contract_type = Column(String(50), index=True)
    title = Column(String(255), nullable=False)
    terms_and_conditions = Column(JSON, nullable=False)

    status = Column(String(50), default="DRAFT")
    smart_contract_address = Column(String(42), nullable=True)
    blockchain_tx_hash = Column(String(100), unique=True, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)


class ContractSignature(Base):
    __tablename__ = "social_contract_signatures"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    contract_id = Column(Integer, ForeignKey("social_smart_contracts.id"), nullable=False, index=True)
    signer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    digital_signature_hash = Column(String(512), nullable=False)
    signed_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_contract_signature_unique", "contract_id", "signer_id", unique=True),
    )


# ========== 4. الفعاليات الاجتماعية (مع Multi-Tenancy) ==========
class SocialEvent(Base):
    __tablename__ = "social_events"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("social_groups.id"), nullable=True, index=True)
    page_id = Column(Integer, nullable=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(String(50), index=True)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    location_details = Column(JSON, nullable=True)

    requires_approval = Column(Boolean, default=True)
    approval_status = Column(SQLEnum(EventApprovalStatus), default=EventApprovalStatus.PENDING)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)


class EventAttendee(Base):
    __tablename__ = "social_event_attendees"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    event_id = Column(Integer, ForeignKey("social_events.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(50), default="GOING")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_event_attendee_unique", "event_id", "user_id", unique=True),
    )


# ========== 5. الذكاء الاصطناعي للتعارف والتوافق (مع Multi-Tenancy) ==========
class AIMatchProfile(Base):
    __tablename__ = "ai_match_profiles"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    seek_type = Column(JSON, nullable=False)
    ai_preferences = Column(JSON, nullable=False)

    is_discoverable = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UserConnection(Base):
    __tablename__ = "user_connections"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    user_a_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user_b_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    connection_type = Column(SQLEnum(ConnectionType), nullable=False)
    match_score = Column(Numeric(5, 2), nullable=True)
    status = Column(String(50), default="PENDING")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_user_connection_pair", "user_a_id", "user_b_id", unique=True),
        CheckConstraint("user_a_id != user_b_id", name="check_no_self_connection"),
    )


# ========== 6. الأنظمة الجديدة (التذكيرات، الهدايا، SaaS للمجموعات) ==========

# 6.1 نظام التذكير (Reminders)
class UserOccasion(Base):
    __tablename__ = "user_occasions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

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
    )


class OccasionReminder(Base):
    __tablename__ = "occasion_reminders"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    occasion_id = Column(Integer, ForeignKey("user_occasions.id"), nullable=False, index=True)
    friend_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    reminder_type = Column(String(50), default="SYSTEM")
    reminder_date = Column(DateTime(timezone=True), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="PENDING")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_reminder_occasion", "occasion_id"),
        Index("ix_reminder_tenant", "tenant_id"),
    )


# 6.2 نظام الهدايا (Gifts)
class DigitalGift(Base):
    __tablename__ = "digital_gifts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    occasion_id = Column(Integer, ForeignKey("user_occasions.id"), nullable=True)

    gift_type = Column(String(50), nullable=False)
    gift_value_mrusdt = Column(Numeric(30, 8), default=0)
    gift_message = Column(Text, nullable=True)
    gift_metadata = Column(JSON, default=dict)

    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    is_redeemed = Column(Boolean, default=False)
    redeemed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_digital_gift_sender", "sender_id"),
        Index("ix_digital_gift_receiver", "receiver_id"),
        Index("ix_digital_gift_tenant", "tenant_id"),
    )


class PhysicalGiftRequest(Base):
    __tablename__ = "physical_gift_requests"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    occasion_id = Column(Integer, ForeignKey("user_occasions.id"), nullable=True)

    product_id = Column(Integer, nullable=True)
    product_name = Column(String(255), nullable=False)
    product_description = Column(Text, nullable=True)
    product_price_mrusdt = Column(Numeric(30, 8), nullable=False)

    shipping_address = Column(JSON, nullable=False)
    shipping_status = Column(String(50), default="PENDING")

    payment_tx_hash = Column(String(100), nullable=True)
    order_tracking_number = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_physical_gift_sender", "sender_id"),
        Index("ix_physical_gift_receiver", "receiver_id"),
        Index("ix_physical_gift_tenant", "tenant_id"),
    )


class GiftReminder(Base):
    __tablename__ = "gift_reminders"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    occasion_id = Column(Integer, ForeignKey("user_occasions.id"), nullable=False, index=True)
    friend_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    reminder_sent_at = Column(DateTime(timezone=True), server_default=func.now())
    is_acknowledged = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_gift_reminder_occasion", "occasion_id"),
        Index("ix_gift_reminder_tenant", "tenant_id"),
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
    )


class GroupSubscriptionPlan(Base):
    __tablename__ = "group_subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price_monthly_mrusdt = Column(Numeric(30, 8), default=0)
    price_yearly_mrusdt = Column(Numeric(30, 8), default=0)

    included_features = Column(JSON, default=list)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_subscription_plan_tenant", "tenant_id"),
    )


class GroupSubscription(Base):
    __tablename__ = "group_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    group_id = Column(Integer, ForeignKey("social_groups.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("group_subscription_plans.id"), nullable=False, index=True)

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
    )


# ===================== الإضافة الجديدة: المناقصات والمزادات (Tenders & Auctions) =====================

# ========== الأنواع المساعدة للمناقصات والمزادات ==========
class TenderStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    SUBMISSION_CLOSED = "SUBMISSION_CLOSED"
    EVALUATION = "EVALUATION"
    AWARDED = "AWARDED"
    CANCELLED = "CANCELLED"

class BidStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    EVALUATION = "EVALUATION"
    REJECTED = "REJECTED"
    ACCEPTED = "ACCEPTED"
    WITHDRAWN = "WITHDRAWN"

class AuctionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    SOLD = "SOLD"
    CANCELLED = "CANCELLED"


# ========== 1. المناقصات (Tenders) ==========
class SovereignTender(Base):
    __tablename__ = "sovereign_tenders"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    scope_of_work = Column(JSON, nullable=False)

    estimated_budget_mrusdt = Column(Numeric(30, 8), nullable=False)
    min_bid_mrusdt = Column(Numeric(30, 8), nullable=True)
    max_bid_mrusdt = Column(Numeric(30, 8), nullable=True)

    submission_start = Column(DateTime(timezone=True), nullable=False)
    submission_deadline = Column(DateTime(timezone=True), nullable=False)

    status = Column(SQLEnum(TenderStatus), default=TenderStatus.DRAFT)

    # ربط بالقطاعات الأخرى
    project_id = Column(Integer, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        CheckConstraint("submission_deadline > submission_start", name="check_tender_dates"),
        Index("ix_tender_tenant_status", "tenant_id", "status"),
    )


# ========== 2. العطاءات (Tender Bids) مع Multi-Tenancy + Idempotency ==========
class TenderBid(Base):
    __tablename__ = "tender_bids"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    tender_id = Column(Integer, ForeignKey("sovereign_tenders.id"), nullable=False, index=True)
    bidder_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    technical_envelope = Column(JSON, nullable=False)
    encrypted_financial_envelope = Column(Text, nullable=False)

    technical_score = Column(Numeric(5, 2), nullable=True)
    financial_amount_mrusdt = Column(Numeric(30, 8), nullable=True)

    status = Column(SQLEnum(BidStatus), default=BidStatus.SUBMITTED)
    bid_tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_tender_bid_tenant", "tenant_id"),
        Index("ix_tender_bid_unique", "tender_id", "bidder_id", unique=True),
    )


# ========== 3. المزادات (Auctions) مع Multi-Tenancy ==========
class SovereignAuction(Base):
    __tablename__ = "sovereign_auctions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # الأصل المعروض (عقار، سلعة، خدمة، إلخ)
    asset_type = Column(String(50), nullable=False)
    asset_id = Column(Integer, nullable=True)

    start_price_mrusdt = Column(Numeric(30, 8), nullable=False)
    min_increment_mrusdt = Column(Numeric(30, 8), default=0)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    status = Column(SQLEnum(AuctionStatus), default=AuctionStatus.DRAFT)

    # ربط بالمزادات الحيوية والعقود
    winning_bid_id = Column(Integer, nullable=True)
    smart_contract_address = Column(String(42), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="check_auction_dates"),
        Index("ix_auction_tenant", "tenant_id"),
        Index("ix_auction_status_times", "status", "start_time", "end_time"),
    )


# ========== 4. المزايدات الحية (Live Bids) مع Multi-Tenancy + Idempotency ==========
class LiveBid(Base):
    __tablename__ = "live_bids"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    auction_id = Column(Integer, ForeignKey("sovereign_auctions.id"), nullable=False, index=True)
    bidder_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    bid_amount_mrusdt = Column(Numeric(30, 8), nullable=False)
    bid_tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("bid_amount_mrusdt > 0", name="check_bid_positive"),
        Index("ix_live_bid_tenant_auction", "tenant_id", "auction_id"),
        Index("ix_live_bid_auction_amount", "auction_id", "bid_amount_mrusdt"),
    )