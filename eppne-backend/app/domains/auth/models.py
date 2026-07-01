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
    """
    نموذج رمز التحديث (Refresh Token) - OAuth2 متقدم.
    🔥 الأمان: يتم تخزين التوكين بشكل مشفر (SHA-256) لحمايته من التسريب.
    🔥 المعمارية: يستخدم `session_version` من جدول المستخدم لإبطال الجلسات عن بُعد.
    """
    __tablename__ = "auth_refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_token_user_id", "user_id"),
        Index("ix_refresh_token_revoked", "revoked"),
        Index("ix_refresh_token_expires_at", "expires_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 🔥 التخزين المشفر: يتم تخزين hash التوكين فقط، وليس التوكين نفسه
    token_hash = Column(String(64), nullable=False, unique=True, index=True)

    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # الجهاز والمتصفح (للتدقيق الأمني - Audit Log)
    device_name = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # العلاقات
    user = relationship("User", back_populates="refresh_tokens")

    @staticmethod
    def hash_token(token: str) -> str:
        """
        🔥 تشفير التوكين باستخدام SHA-256 (اتجاه واحد).
        هذا يضمن أنه حتى في حالة تسريب قاعدة البيانات، لا يمكن استعادة التوكين الأصلي.
        """
        return hashlib.sha256(token.encode()).hexdigest()

    def is_expired(self) -> bool:
        """التحقق من انتهاء صلاحية التوكين."""
        return datetime.now(timezone.utc) > self.expires_at

    def revoke(self) -> None:
        """إبطال التوكين."""
        self.revoked = True
        self.revoked_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<RefreshToken(user_id={self.user_id}, revoked={self.revoked})>"