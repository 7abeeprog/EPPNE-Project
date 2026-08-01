# app/domains/translation/models.py (الإصدار النهائي المتكامل - مع ترقية JSONB)
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text, Boolean, Index, text  # ✅ تم إضافة text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base


class TranslationCache(Base):
    __tablename__ = "translation_cache"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    text_hash = Column(String(64), unique=True, index=True, nullable=False)
    original_text = Column(Text, nullable=False)
    source_lang = Column(String(10), nullable=False, index=True)

    translations = Column(JSONB, nullable=False, default=dict)

    hit_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_translation_cache_tenant", "tenant_id"),
        Index("ix_translation_cache_created_at", "created_at"),
    )


class TranslationRequestLog(Base):
    __tablename__ = "translation_request_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    source_lang = Column(String(10), nullable=False)
    target_lang = Column(String(10), nullable=False)
    text_length = Column(Integer)
    used_cache = Column(Boolean, default=False)

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    idempotency_key = Column(String(64), nullable=True, index=True)

    cost_mrusdt = Column(String(20), default="0")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_translation_log_tenant", "tenant_id"),
        Index("ix_translation_log_created_at", "created_at"),
        Index("ix_translation_log_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


class SupportedLanguage(Base):
    __tablename__ = "supported_languages"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    native_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_supported_language_created_at", "created_at"),
    )