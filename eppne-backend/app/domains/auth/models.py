# app/domains/auth/models.py
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Boolean, Text, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
import hashlib

from app.core.database import Base

class RefreshToken(Base):
    __tablename__ = "auth_refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_token_user_id", "user_id"),
        Index("ix_refresh_token_tenant_id", "tenant_id"),
        Index("ix_refresh_token_revoked", "revoked"),
        Index("ix_refresh_token_expires_at", "expires_at"),
        Index("ix_refresh_token_user_expires", "user_id", "expires_at"),
        Index("ix_refresh_token_tenant_user", "tenant_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    token_hash = Column(String(64), nullable=False, unique=True, index=True)

    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    device_name = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="refresh_tokens")

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at  # type: ignore

    def revoke(self) -> None:
        self.revoked = True
        self.revoked_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<RefreshToken(user_id={self.user_id}, tenant_id={self.tenant_id}, revoked={self.revoked})>"