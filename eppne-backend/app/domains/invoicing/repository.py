# app/domains/invoicing/repository.py
"""
طبقة الوصول إلى البيانات (Repository) لقطاع الفواتير.
تدعم: العمليات الأساسية (CRUD)، التصفية، الإحصائيات، والمعاملات الذرية.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from app.domains.invoicing.models import Invoice, InvoiceStatus, InvoiceType
from app.core.errors import NotFoundError


class InvoicingRepository:
    """مستودع عمليات الفواتير."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # 1. العمليات الأساسية (CRUD)
    # ============================================================

    async def create_invoice(self, **kwargs) -> Invoice:
        """إنشاء فاتورة جديدة."""
        invoice = Invoice(**kwargs)
        self.db.add(invoice)
        await self.db.commit()
        await self.db.refresh(invoice)
        return invoice

    async def get_invoice(self, invoice_id: int) -> Optional[Invoice]:
        """جلب فاتورة بواسطة المعرف."""
        result = await self.db.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        return result.scalar_one_or_none()

    async def get_invoice_by_number(self, invoice_number: str) -> Optional[Invoice]:
        """جلب فاتورة بواسطة رقم الفاتورة."""
        result = await self.db.execute(
            select(Invoice).where(Invoice.invoice_number == invoice_number)
        )
        return result.scalar_one_or_none()

    async def update_invoice(self, invoice_id: int, **kwargs) -> Invoice:
        """تحديث فاتورة موجودة."""
        await self.db.execute(
            update(Invoice)
            .where(Invoice.id == invoice_id)
            .values(**kwargs)
        )
        await self.db.commit()
        invoice = await self.get_invoice(invoice_id)
        if not invoice:
            raise NotFoundError(f"Invoice {invoice_id} not found")
        return invoice

    async def delete_invoice(self, invoice_id: int, hard: bool = False) -> bool:
        """حذف فاتورة (افتراضياً حذف ناعم عن طريق تغيير الحالة إلى CANCELLED)."""
        if hard:
            await self.db.execute(
                delete(Invoice).where(Invoice.id == invoice_id)
            )
            await self.db.commit()
            return True
        else:
            await self.update_invoice(invoice_id, status=InvoiceStatus.CANCELLED)
            return True

    # ============================================================
    # 2. قائمة الفواتير مع التصفية
    # ============================================================

    async def list_invoices(
        self,
        tenant_id: int,
        user_id: Optional[int] = None,
        status: Optional[InvoiceStatus] = None,
        invoice_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Invoice]:
        """جلب قائمة الفواتير مع خيارات التصفية."""
        query = select(Invoice).where(Invoice.tenant_id == tenant_id)

        if user_id is not None:
            query = query.where(Invoice.user_id == user_id)
        if status is not None:
            query = query.where(Invoice.status == status)
        if invoice_type is not None:
            query = query.where(Invoice.invoice_type == invoice_type)
        if reference_id is not None:
            query = query.where(Invoice.reference_id == reference_id)

        query = query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_invoices(self, tenant_id: int) -> int:
        """حساب عدد الفواتير للمستأجر (لتوليد الأرقام التسلسلية)."""
        result = await self.db.execute(
            select(func.count()).where(Invoice.tenant_id == tenant_id)
        )
        return result.scalar() or 0

    async def get_invoices_by_reference(
        self,
        tenant_id: int,
        reference_id: int,
        invoice_type: Optional[str] = None,
    ) -> List[Invoice]:
        """جلب الفواتير المرتبطة بمرجع معين."""
        query = select(Invoice).where(
            Invoice.tenant_id == tenant_id,
            Invoice.reference_id == reference_id,
        )
        if invoice_type:
            query = query.where(Invoice.invoice_type == invoice_type)

        result = await self.db.execute(query.order_by(Invoice.created_at.desc()))
        return list(result.scalars().all())

    # ============================================================
    # 3. إحصائيات المبالغ
    # ============================================================

    async def sum_amount_by_status(self, tenant_id: int, status: InvoiceStatus) -> Decimal:
        """جمع مبالغ الفواتير حسب الحالة."""
        result = await self.db.execute(
            select(func.sum(Invoice.amount))
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.status == status
            )
        )
        return result.scalar() or Decimal(0)

    async def count_overdue_invoices(self, tenant_id: int) -> int:
        """حساب عدد الفواتير المتأخرة (OVERDUE)."""
        result = await self.db.execute(
            select(func.count())
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.status == InvoiceStatus.OVERDUE
            )
        )
        return result.scalar() or 0

    # ============================================================
    # 4. معالجة الفواتير المتأخرة (لمهام Celery)
    # ============================================================

    async def get_overdue_invoices(self) -> List[Invoice]:
        """جلب الفواتير التي تجاوزت تاريخ الاستحقاق وحالتها PENDING."""
        now = datetime.utcnow()
        result = await self.db.execute(
            select(Invoice)
            .where(
                Invoice.status == InvoiceStatus.PENDING,
                Invoice.due_date < now
            )
            .order_by(Invoice.due_date)
        )
        return list(result.scalars().all())

    # ============================================================
    # 5. التحقق من Idempotency
    # ============================================================

    async def get_invoice_by_idempotency_key(self, idempotency_key: str) -> Optional[Invoice]:
        """جلب فاتورة بواسطة مفتاح Idempotency."""
        result = await self.db.execute(
            select(Invoice).where(Invoice.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()