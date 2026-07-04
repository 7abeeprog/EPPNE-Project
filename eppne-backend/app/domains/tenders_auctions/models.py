from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, JSON, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.sql import func
import enum
from app.core.database import Base

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

# ========== 2. العطاءات (Tender Bids) ==========
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

# ========== 3. المزادات (Auctions) ==========
class SovereignAuction(Base):
    __tablename__ = "sovereign_auctions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    asset_type = Column(String(50), nullable=False)
    asset_id = Column(Integer, nullable=True)

    start_price_mrusdt = Column(Numeric(30, 8), nullable=False)
    min_increment_mrusdt = Column(Numeric(30, 8), default=0)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    status = Column(SQLEnum(AuctionStatus), default=AuctionStatus.DRAFT)

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

# ========== 4. المزايدات الحية (Live Bids) ==========
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