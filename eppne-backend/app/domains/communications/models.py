from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text, Boolean, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class NotificationChannel(str, enum.Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"
    WEBSOCKET = "WEBSOCKET"
    IN_APP = "IN_APP"

class NotificationPriority(str, enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class MailFolder(str, enum.Enum):
    INBOX = "INBOX"
    SENT = "SENT"
    DRAFTS = "DRAFTS"
    TRASH = "TRASH"
    ARCHIVE = "ARCHIVE"

# ========== 1. الإشعارات (Push, In-App) ==========
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    data = Column(JSON, default=dict)          # بيانات إضافية (مثل معرف الطلب، نوع الحدث)
    channel = Column(SQLEnum(NotificationChannel), default=NotificationChannel.IN_APP)
    priority = Column(SQLEnum(NotificationPriority), default=NotificationPriority.NORMAL)
    is_read = Column(Boolean, default=False)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    idempotency_key = Column(String(255), nullable=True, unique=True, index=True)  # ✅ إضافة حقل Idempotency

    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "is_read"),
        Index("ix_notifications_created", "created_at"),
    )


class NotificationDevice(Base):
    __tablename__ = "notification_devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_token = Column(String(255), nullable=False)   # FCM token, Expo token, etc.
    platform = Column(String(50), nullable=False)       # ios, android, web
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_device_token_unique", "device_token", unique=True),
    )


# ========== 2. البريد الداخلي (Sovereign Mail) ==========
class MailThread(Base):
    __tablename__ = "mail_threads"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MailMessage(Base):
    __tablename__ = "mail_messages"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("mail_threads.id"), nullable=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    subject = Column(String(255), nullable=False)
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)

    is_certified = Column(Boolean, default=False)          # بريد موثق بتوقيع رقمي
    certified_tx_hash = Column(String(100), nullable=True) # توثيق على السلسلة

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)
    idempotency_key = Column(String(255), nullable=True, unique=True, index=True)  # ✅ إضافة حقل Idempotency


class MailboxItem(Base):
    __tablename__ = "mailbox_items"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("mail_messages.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    folder = Column(SQLEnum(MailFolder), default=MailFolder.INBOX)
    is_read = Column(Boolean, default=False)
    is_starred = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MailAttachment(Base):
    __tablename__ = "mail_attachments"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("mail_messages.id"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(1024), nullable=False)
    file_size_bytes = Column(Integer, default=0)
    mime_type = Column(String(100), nullable=True)
    ipfs_hash = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ========== 3. قوالب البريد والإشعارات ==========
class CommunicationTemplate(Base):
    __tablename__ = "communication_templates"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    trigger_event = Column(String(100), nullable=False, index=True)  # USER_WELCOME, INVOICE_DUE, ORDER_SHIPPED
    subject_template = Column(String(255), nullable=False)
    body_template = Column(Text, nullable=False)
    channel = Column(SQLEnum(NotificationChannel), default=NotificationChannel.EMAIL)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())