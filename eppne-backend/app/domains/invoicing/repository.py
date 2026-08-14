# app/domains/invoicing/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from app.domains.invoicing.models import Invoice, InvoiceStatus, InvoiceType
from app.domains.invoicing.schemas import InvoiceResponse
from app.core.errors import NotFoundError
from app.core.pagination import PaginatedResponse


class InvoicingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # 1. العمليات الأساسية (CRUD) – مع tenant_id
    # ============================================================

    async def create_invoice(self, **kwargs) -> Invoice:
        # WARNING: هذا الـcommit() بيغطي كمان كتابات finance.transfer() جوه service methods
        # تانية (زي arbitration_syndicates.join_syndicate) بتنادي InvoicingService.create_invoice
        # بعد finance.transfer مباشرة (flush() بس، بلا commit مستقل خاص بيها) — لا تحوّل الـcommit()
        # ده لـflush() بدون فحص شامل لكل الـcallers أولًا.
        invoice = Invoice(**kwargs)
        self.db.add(invoice)
        await self.db.commit()
        await self.db.refresh(invoice)
        return invoice

    async def get_invoice(self, invoice_id: int, tenant_id: int) -> Optional[Invoice]:
        result = await self.db.execute(
            select(Invoice).where(
                and_(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_invoice_by_number(self, invoice_number: str, tenant_id: int) -> Optional[Invoice]:
        result = await self.db.execute(
            select(Invoice).where(
                and_(Invoice.invoice_number == invoice_number, Invoice.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()

    async def update_invoice(self, invoice_id: int, tenant_id: int, **kwargs) -> Invoice:
        invoice = await self.get_invoice(invoice_id, tenant_id)
        if not invoice:
            raise NotFoundError(f"Invoice {invoice_id} not found")

        # WARNING: هذا الـcommit() بيغطي كمان كتابة finance.transfer() جوه
        # service.update_invoice_status (اللي فيها flush() بس، بلا commit مستقل خاص بيها) —
        # لا تحوّل الـcommit() ده لـflush() بدون إضافة commit() صريح لـupdate_invoice_status أولًا.
        await self.db.execute(
            update(Invoice)
            .where(and_(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id))
            .values(**kwargs)
        )
        await self.db.commit()
        return await self.get_invoice(invoice_id, tenant_id)

    async def delete_invoice(self, invoice_id: int, tenant_id: int, hard: bool = False) -> bool:
        if hard:
            await self.db.execute(
                delete(Invoice)
                .where(and_(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id))
            )
            await self.db.commit()
            return True
        else:
            await self.update_invoice(invoice_id, tenant_id, status=InvoiceStatus.CANCELLED)
            return True

    # ============================================================
    # 2. قائمة الفواتير مع Pagination و tenant_id
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
    ) -> PaginatedResponse[InvoiceResponse]:
        query = select(Invoice).where(Invoice.tenant_id == tenant_id)

        if user_id is not None:
            query = query.where(Invoice.user_id == user_id)
        if status is not None:
            query = query.where(Invoice.status == status)
        if invoice_type is not None:
            query = query.where(Invoice.invoice_type == invoice_type)
        if reference_id is not None:
            query = query.where(Invoice.reference_id == reference_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = [InvoiceResponse.model_validate(inv) for inv in result.scalars().all()]

        return PaginatedResponse[InvoiceResponse](
            items=items,
            total=total,
            skip=skip,
            limit=limit
        )

    async def count_invoices(self, tenant_id: int) -> int:
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
        query = select(Invoice).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.reference_id == reference_id,
            )
        )
        if invoice_type:
            query = query.where(Invoice.invoice_type == invoice_type)

        result = await self.db.execute(query.order_by(Invoice.created_at.desc()))
        return list(result.scalars().all())

    # ============================================================
    # 3. إحصائيات المبالغ – مع tenant_id
    # ============================================================

    async def sum_amount_by_status(self, tenant_id: int, status: InvoiceStatus) -> Decimal:
        result = await self.db.execute(
            select(func.sum(Invoice.amount))
            .where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.status == status
                )
            )
        )
        return result.scalar() or Decimal(0)

    async def count_overdue_invoices(self, tenant_id: int) -> int:
        result = await self.db.execute(
            select(func.count())
            .where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.status == InvoiceStatus.OVERDUE
                )
            )
        )
        return result.scalar() or 0

    # ============================================================
    # 4. معالجة الفواتير المتأخرة – مع tenant_id اختياري
    # ============================================================

    async def get_overdue_invoices(self, tenant_id: Optional[int] = None) -> List[Invoice]:
        now = datetime.utcnow()
        query = select(Invoice).where(
            and_(
                Invoice.status == InvoiceStatus.PENDING,
                Invoice.due_date < now
            )
        )
        if tenant_id is not None:
            query = query.where(Invoice.tenant_id == tenant_id)

        result = await self.db.execute(query.order_by(Invoice.due_date))
        return list(result.scalars().all())

    # ============================================================
    # 5. التحقق من Idempotency – مع tenant_id
    # ============================================================

    async def get_invoice_by_idempotency_key(self, idempotency_key: str, tenant_id: int) -> Optional[Invoice]:
        result = await self.db.execute(
            select(Invoice).where(
                and_(
                    Invoice.idempotency_key == idempotency_key,
                    Invoice.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()