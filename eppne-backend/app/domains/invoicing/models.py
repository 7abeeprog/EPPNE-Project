# app/domains/invoicing/models.py
"""
نماذج قاعدة البيانات لقطاع الفواتير (Invoicing).
يدعم: أنواع الفواتير، الحالات، الربط بالمراجع (Orders, Subscriptions).
"""
import enum
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, Text, Boolean,
    Numeric, DateTime, JSON, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.sql import func
from app.core.database import Base


class InvoiceStatus(str, enum.Enum):
    """حالات الفاتورة."""
    DRAFT = "DRAFT"          # مسودة (غير مرسلة)
    PENDING = "PENDING"      # معلقة (في انتظار الدفع)
    PAID = "PAID"            # مدفوعة
    OVERDUE = "OVERDUE"      # متأخرة (تجاوزت تاريخ الاستحقاق)
    CANCELLED = "CANCELLED"  # ملغية


class InvoiceType(str, enum.Enum):
    """أنواع الفواتير."""
    SERVICE = "SERVICE"              # خدمات عامة
    AI_USAGE = "AI_USAGE"            # استخدام الذكاء الاصطناعي
    SUBSCRIPTION = "SUBSCRIPTION"    # اشتراكات
    SAAS = "SAAS"                    # اشتراكات SaaS
    PRODUCT = "PRODUCT"              # منتجات (من التجارة)
    RENTAL = "RENTAL"                # إيجارات
    OTHER = "OTHER"                  # أخرى


class Invoice(Base):
    """جدول الفواتير الأساسي."""
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_tenant_id", "tenant_id"),
        Index("ix_invoices_user_id", "user_id"),
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_due_date", "due_date"),
        Index("ix_invoices_invoice_number", "invoice_number", unique=True),
        Index("ix_invoices_reference_id", "reference_id"),
        Index("ix_invoices_idempotency_key", "idempotency_key", unique=True),
        Index("ix_invoices_invoice_type", "invoice_type"),
        CheckConstraint("amount >= 0", name="check_amount_non_negative"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # رقم الفاتورة الفريد (قابل للقراءة من قبل المستخدم)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)

    # نوع الفاتورة وحالتها
    invoice_type = Column(SQLEnum(InvoiceType), nullable=False, default=InvoiceType.SERVICE)
    status = Column(SQLEnum(InvoiceStatus), nullable=False, default=InvoiceStatus.PENDING)

    # البيانات المالية
    amount = Column(Numeric(30, 8), nullable=False)
    currency = Column(String(10), nullable=False, default="MR_USDT")

    # البيانات الوصفية
    description = Column(Text, nullable=True)
    reference_id = Column(Integer, nullable=True)  # يمكن ربطه بـ order_id, subscription_id, etc.
    idempotency_key = Column(String(100), nullable=True, unique=True)

    # التواريخ
    issue_date = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(DateTime(timezone=True), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    # بيانات إضافية
    notes = Column(Text, nullable=True)
    invoice_metadata = Column(JSON, nullable=True) # تخزين بيانات إضافية (مثل تفاصيل الضرائب، عناوين)


    # تتبع التعديلات
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Invoice {self.invoice_number} | {self.status.value} | {self.amount} {self.currency}>"