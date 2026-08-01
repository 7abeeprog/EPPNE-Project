# app/domains/finance/models.py
from sqlalchemy import (
    Column, Integer, BigInteger, String, Numeric, Boolean, DateTime,
    ForeignKey, Index, text, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Wallet(Base):
    __tablename__ = "wallets"
    
    __table_args__ = (
        Index("ix_wallets_user_id", "user_id"),
        Index("ix_wallets_tenant_id", "tenant_id"),
        CheckConstraint(
            "(balances->>'MR_POUND')::numeric >= 0 AND "
            "(balances->>'MR_USDT')::numeric >= 0 AND "
            "(balances->>'MR7')::numeric >= 0 AND "
            "(balances->>'NBT')::numeric >= 0 AND "
            "(balances->>'MRX')::numeric >= 0",
            name="check_wallet_balances_non_negative"
        ),
        {"extend_existing": True}
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    wallet_address = Column(String(42), unique=True, index=True, nullable=True)
    is_custodial = Column(Boolean, default=True)
    balances = Column(JSONB, default=dict, nullable=False)
    is_frozen = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship(
        "app.domains.identity.models.User",
        back_populates="wallet",
        lazy="selectin"
    )


class Transaction(Base):
    __tablename__ = "transactions"
    
    __table_args__ = (
        Index("ix_transactions_sender_created", "sender_id", "created_at"),
        Index("ix_transactions_receiver_created", "receiver_id", "created_at"),
        Index("ix_transactions_currency_status", "currency", "status"),
        Index("ix_transactions_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
        Index("ix_transactions_created_status", "created_at", "status"),
        Index("ix_transactions_tx_type_created", "tx_type", "created_at"),
        CheckConstraint("amount > 0", name="check_transaction_amount_positive"),
        {"extend_existing": True}
    )

    id = Column(BigInteger, primary_key=True, index=True)
    tx_hash = Column(String(100), unique=True, index=True, nullable=False)
    idempotency_key = Column(String(255), unique=True, index=True, nullable=True)

    sender_id = Column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)
    receiver_id = Column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)

    from_wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=True, index=True)
    to_wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=True, index=True)

    amount = Column(Numeric(30, 8), nullable=False)
    currency = Column(String(20), nullable=False, index=True)
    exchange_rate_applied = Column(Numeric(30, 8), nullable=True)

    tx_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), default="PENDING", index=True)

    fee_amount = Column(Numeric(30, 8), default=0)
    notes = Column(String(500), nullable=True)

    blockchain_hash = Column(String(100), unique=True, nullable=True)
    smart_contract_ref = Column(String(42), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SystemState(Base):
    __tablename__ = "system_state"
    
    __table_args__ = (
        Index("ix_system_state_updated_at", "updated_at"),
        {"extend_existing": True}
    )

    id = Column(Integer, primary_key=True, index=True)
    crypto_mode = Column(String(20), default="FULL_CRYPTO", nullable=False)
    is_trading_active = Column(Boolean, default=True)
    exchange_rates = Column(JSONB, default=lambda: {
        "MR_POUND": 1.0,
        "MR_USDT": 50.0,
        "MR7": 5.0,
        "NBT": 250.0,
        "MRX": 500.0,
    }, nullable=False)
    
    max_supply = Column(JSONB, default=lambda: {
        "MR_POUND": 1_000_000_000,
        "MR_USDT": 100_000_000,
        "MR7": 10_000_000,
        "NBT": 1_000_000,
        "MRX": 100_000,
    }, nullable=False)
    total_supply = Column(JSONB, default=lambda: {
        "MR_POUND": 0,
        "MR_USDT": 0,
        "MR7": 0,
        "NBT": 0,
        "MRX": 0,
    }, nullable=False)

    updated_by_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_tenant_id", "tenant_id"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_audit_logs_tenant_user", "tenant_id", "user_id"),
        {"extend_existing": True}
    )

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    details = Column(JSONB, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)