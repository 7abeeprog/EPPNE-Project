# app/domains/identity/models.py
from datetime import datetime
from sqlalchemy import (
    Column, BigInteger, String, Boolean, DateTime, Date,
    Enum as SQLEnum, Integer, ForeignKey, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.enums import SystemRole, SovereignRank, KYCStatus, MarriageStatus

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_username_lower", func.lower("username")),
        Index("ix_users_email_lower", func.lower("email")),
        Index("ix_users_public_id", "public_id"),
        Index("ix_users_tenant_id", "tenant_id"),
        Index("ix_users_created_at", "created_at"),
        Index("ix_users_last_login_at", "last_login_at"),
        CheckConstraint("char_length(username) >= 4", name="ck_username_min_length"),
        CheckConstraint("char_length(email) > 0", name="ck_email_not_empty"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    public_id = Column(String, unique=True, index=True, nullable=True)
    uid = Column(String(20), unique=True, index=True, nullable=True)
    did = Column(String, unique=True, nullable=True)

    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    name_ar = Column(String(100), nullable=True)
    name_en = Column(String, nullable=True)

    birth_date = Column(Date, nullable=True)
    death_date = Column(Date, nullable=True)
    marriage_status = Column(SQLEnum(MarriageStatus), default=MarriageStatus.SINGLE)

    father_id = Column(BigInteger, nullable=True)
    mother_id = Column(BigInteger, nullable=True)
    spouse_id = Column(BigInteger, nullable=True)

    sovereign_rank = Column(SQLEnum(SovereignRank), default=SovereignRank.CITIZEN_L1)
    system_role = Column(SQLEnum(SystemRole), default=SystemRole.USER, nullable=False)
    kyc_status = Column(SQLEnum(KYCStatus), default=KYCStatus.UNVERIFIED)
    reputation_score = Column(Integer, default=100)

    language_preference = Column(String, default="ar")
    profile_metadata = Column(JSONB, default=dict)
    preferences = Column(JSONB, default=dict)

    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)
    session_version = Column(Integer, default=1)

    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    last_login_user_agent = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=True)

    refresh_tokens = relationship(
        "app.domains.auth.models.RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    wallet = relationship(
        "app.domains.finance.models.Wallet",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    tenant = relationship(
        "app.domains.academy.models.Tenant",
        foreign_keys=[tenant_id],
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, tenant_id={self.tenant_id}, username={self.username})>"