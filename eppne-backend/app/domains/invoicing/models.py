# app/domains/invoicing/models.py
"""
نماذج قاعدة البيانات لقطاع الفواتير (Invoicing).
يدعم: أنواع الفواتير، الحالات، الربط بالمراجع (Orders, Subscriptions, وأي مرجع عام).
"""
import enum
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, Text, Boolean,
    Numeric, DateTime, Enum as SQLEnum, Index, CheckConstraint, text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base


class InvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class InvoiceType(str, enum.Enum):
    SERVICE = "SERVICE"
    AI_USAGE = "AI_USAGE"
    SUBSCRIPTION = "SUBSCRIPTION"
    SAAS = "SAAS"
    PRODUCT = "PRODUCT"
    RENTAL = "RENTAL"
    OTHER = "OTHER"


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_tenant_id", "tenant_id"),
        Index("ix_invoices_user_id", "user_id"),
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_due_date", "due_date"),
        Index("ix_invoices_invoice_number", "invoice_number", unique=True),
        Index("ix_invoices_order_id", "order_id"),
        Index("ix_invoices_subscription_id", "subscription_id"),
        Index("ix_invoices_reference_id", "reference_id"),
        Index("ix_invoices_invoice_type", "invoice_type"),
        Index("ix_invoices_created_at", "created_at"),
        Index("ix_invoices_updated_at", "updated_at"),
        Index("ix_invoices_tenant_status_due", "tenant_id", "status", "due_date"),
        Index("ix_invoices_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
        CheckConstraint("amount >= 0", name="check_amount_non_negative"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    invoice_number = Column(String(50), unique=True, nullable=False, index=True)

    invoice_type = Column(SQLEnum(InvoiceType), nullable=False, default=InvoiceType.SERVICE)
    status = Column(SQLEnum(InvoiceStatus), nullable=False, default=InvoiceStatus.PENDING)

    amount = Column(Numeric(30, 8), nullable=False)
    currency = Column(String(10), nullable=False, default="MR_USDT")

    description = Column(Text, nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    subscription_id = Column(Integer, ForeignKey("saas_tenant_subscriptions.id", ondelete="SET NULL"), nullable=True)
    
    reference_id = Column(Integer, nullable=True, index=True)

    idempotency_key = Column(String(100), nullable=True, unique=True)

    issue_date = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(DateTime(timezone=True), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    notes = Column(Text, nullable=True)
    invoice_metadata = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Invoice {self.invoice_number} | {self.status.value} | {self.amount} {self.currency}>"