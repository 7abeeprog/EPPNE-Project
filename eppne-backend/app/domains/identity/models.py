# app/domains/identity/models.py
from datetime import datetime
from sqlalchemy import (
    Column, BigInteger, String, Boolean, DateTime, Date, JSON, 
    Enum as SQLEnum, Integer, ForeignKey, Index
)
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
    )

    id = Column(BigInteger, primary_key=True, index=True)
    public_id = Column(String, unique=True, index=True, nullable=True)
    uid = Column(String(20), unique=True, index=True, nullable=True)
    did = Column(String, unique=True, nullable=True)

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
    profile_metadata = Column(JSON, default=dict)
    preferences = Column(JSON, default=dict)

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
    # ✅ العلاقات
    refresh_tokens = relationship(
        "app.domains.auth.models.RefreshToken", # ← المسار الدقيق
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # ✅ تحديث العلاقة مع المحفظة (تغيير اسم الكلاس إلى IdentityWallet)
    wallet = relationship(
        "IdentityWallet",          # ← تغيير الاسم هنا
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"


# ✅ تغيير اسم الكلاس من Wallet إلى IdentityWallet
class IdentityWallet(Base):
    """
    ✅ محفظة المستخدم (تم فصلها عن User)
    - تضمن Atomic Transactions منفصلة عن جدول المستخدم
    - تمنع Deadlocks عند تنفيذ عمليات مالية متزامنة
    """
    __tablename__ = "identity_wallets"   # ← تغيير اسم الجدول لتجنب التضارب
    __table_args__ = (
        Index("ix_identity_wallets_user_id", "user_id", unique=True),  # تحديث اسم الفهرس
        Index("ix_identity_wallets_address", "wallet_address"),
        Index("ix_identity_wallets_is_frozen", "is_frozen"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    wallet_address = Column(String(42), unique=True, index=True, nullable=True)
    is_custodial = Column(Boolean, default=True)
    is_frozen = Column(Boolean, default=False)

    balances = Column(JSON, default=lambda: {
        "MR_POUND": 0,
        "MR_USDT": 0,
        "MR7": 0,
        "NBT": 0,
        "MRX": 0
    }, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # العلاقة مع المستخدم (يبقى back_populates="wallet" كما هو)
    user = relationship("User", back_populates="wallet")

    def __repr__(self) -> str:
        return f"<IdentityWallet(user_id={self.user_id}, balances={self.balances})>"