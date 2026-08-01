# app/domains/communications/models.py
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text, Boolean, Enum as SQLEnum, Index, text
)
from sqlalchemy.dialects.postgresql import JSONB  # ✅ تم إضافة الاستيراد الصحيح
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
    data = Column(JSONB, default=dict)
    channel = Column(SQLEnum(NotificationChannel), default=NotificationChannel.IN_APP)
    priority = Column(SQLEnum(NotificationPriority), default=NotificationPriority.NORMAL)
    is_read = Column(Boolean, default=False)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    idempotency_key = Column(String(255), nullable=True, unique=True, index=True)

    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "is_read"),
        Index("ix_notifications_created", "created_at"),
        Index("ix_notifications_user_unread", "user_id", "is_read", postgresql_where=text("is_read = false")),
    )


class NotificationDevice(Base):
    __tablename__ = "notification_devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_token = Column(String(255), nullable=False)
    platform = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_device_token_unique", "device_token", unique=True),
        Index("ix_device_user_active", "user_id", "is_active"),
    )


# ========== 2. البريد الداخلي (Sovereign Mail) ==========
class MailThread(Base):
    __tablename__ = "mail_threads"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_mail_thread_tenant", "tenant_id"),
        Index("ix_mail_thread_created", "created_at"),
    )


class MailMessage(Base):
    __tablename__ = "mail_messages"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("mail_threads.id"), nullable=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    subject = Column(String(255), nullable=False)
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)

    is_certified = Column(Boolean, default=False)
    certified_tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)
    idempotency_key = Column(String(255), nullable=True, unique=True, index=True)

    __table_args__ = (
        Index("ix_mail_message_sender", "sender_id"),
        Index("ix_mail_message_recipient", "recipient_id"),
        Index("ix_mail_message_thread", "thread_id"),
        Index("ix_mail_message_created", "created_at"),
    )


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

    __table_args__ = (
        Index("ix_mailbox_owner_folder", "owner_id", "folder"),
        Index("ix_mailbox_message_owner", "message_id", "owner_id", unique=True),
        Index("ix_mailbox_owner_unread", "owner_id", "is_read", postgresql_where=text("is_read = false")),
    )


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

    __table_args__ = (
        Index("ix_mail_attachment_message", "message_id"),
    )


# ========== 3. قوالب البريد والإشعارات ==========
class CommunicationTemplate(Base):
    __tablename__ = "communication_templates"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    trigger_event = Column(String(100), nullable=False, index=True)
    subject_template = Column(String(255), nullable=False)
    body_template = Column(Text, nullable=False)
    channel = Column(SQLEnum(NotificationChannel), default=NotificationChannel.EMAIL)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_template_tenant_event", "tenant_id", "trigger_event"),
        Index("ix_template_active", "is_active"),
    )