# app/domains/privacy/models.py
from __future__ import annotations

from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text, Boolean, JSON, 
    Index, Enum as SQLEnum, text
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class ConsentType(str, enum.Enum):
    DATA_PROCESSING = "DATA_PROCESSING"
    AI_TRAINING = "AI_TRAINING"
    MARKETING = "MARKETING"
    THIRD_PARTY = "THIRD_PARTY"

class ErasureStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    PARTIAL_ON_CHAIN = "PARTIAL_ON_CHAIN"
    REJECTED = "REJECTED"

class PrivacySetting(Base):
    __tablename__ = "privacy_settings"
    __table_args__ = (
        # 🟢 فهرس مركب لتسريع البحث عن إعدادات مستخدم معين مع نوع الرؤية
        Index("ix_privacy_user_visibility", "user_id", "profile_visibility"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    profile_visibility = Column(String(50), default="PUBLIC")  # PUBLIC, FRIENDS_ONLY, PRIVATE
    search_engine_indexing = Column(Boolean, default=True)
    allow_ai_training = Column(Boolean, default=False)
    allow_targeted_ads = Column(Boolean, default=True)
    share_live_location = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DataConsentLog(Base):
    __tablename__ = "data_consent_logs"
    __table_args__ = (
        # 🟢 فهارس لتسريع تقارير الموافقات حسب النوع والتاريخ
        Index("ix_consent_user_type", "user_id", "consent_type"),
        Index("ix_consent_created", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # 🔥 تم التحسين: استخدام SQLEnum بدلاً من String لضمان سلامة البيانات (Security-First)
    consent_type = Column(SQLEnum(ConsentType), nullable=False)
    is_granted = Column(Boolean, nullable=False)

    # 🔥 تم التحسين: يجب أن يكون IP مشفراً (سيتم تطبيق التشفير في طبقة الـ Service)
    ip_address = Column(String(255), nullable=True)  # سيتم تخزينه كـ Hash (تطبيق في Service)
    user_agent = Column(String(255), nullable=True)
    consent_tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DataErasureRequest(Base):
    __tablename__ = "data_erasure_requests"
    __table_args__ = (
        # 🟢 فهارس لتسريع استعلامات المستخدم وحالة الطلب
        Index("ix_erasure_user_status", "user_id", "status"),
        Index("ix_erasure_processed", "processed_at"),
        # 🔥 تحسين الأداء (Performance): فهرس جزئي (Partial Index) لصفوف PENDING فقط
        # هذا يسرع بشكل كبير استعلامات الـ Admin لجلب الطلبات المعلقة
      # 🔥 تم التحسين: استخدام text لضمان عدم وجود أخطاء في الـ Pylance وتحسين توافق قاعدة البيانات
        Index("ix_erasure_pending", "status", postgresql_where=text("status = 'PENDING'")),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    target_module = Column(String(100), nullable=False)  # identity, finance, academy, etc.
    reason = Column(Text, nullable=True)

    status = Column(SQLEnum(ErasureStatus), default=ErasureStatus.PENDING)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    admin_notes = Column(Text, nullable=True)

    erasure_receipt_tx = Column(String(100), unique=True, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TombstoneRecord(Base):
    """
    ⚠️ تحذير أمني (Security-First):
    هذا الجدول هو سجل "الشواهد القبرية" للبيانات المحذوفة.
    **يجب أن يكون Read-Only بالنسبة للواجهة الأمامية (Frontend).**
    عمليات الإدراج (INSERT) والتحديث (UPDATE) هنا مسموح بها فقط من خلال 
    "خدمات النظام الخلفية" (Backend Workers / Admin Services) الموثوقة.
    """
    __tablename__ = "tombstone_records"
    __table_args__ = (
        # فهارس لتسريع البحث عن السجلات المحذوفة
        Index("ix_tombstone_table_record", "table_name", "record_id"),
        Index("ix_tombstone_erasure", "erasure_request_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String(100), nullable=False, index=True)
    record_id = Column(Integer, nullable=False, index=True)
    erasure_request_id = Column(Integer, ForeignKey("data_erasure_requests.id"), nullable=True)

    deleted_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    original_tx_hash = Column(String(100), nullable=True)

    ipfs_unpin_status = Column(Boolean, default=False)
    blockchain_burn_status = Column(SQLEnum(ErasureStatus), default=ErasureStatus.PENDING)  # 🔥 تم تحسين الأداء ليكون Enum # 🔥 يجب أن تكون غير متزامنة (Async)

    created_at = Column(DateTime(timezone=True), server_default=func.now())