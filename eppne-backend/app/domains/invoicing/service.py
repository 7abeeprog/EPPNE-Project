# app/domains/invoicing/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from typing import Optional, List, Dict, Any, cast
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from app.domains.invoicing.repository import InvoicingRepository
from app.domains.invoicing.models import Invoice, InvoiceStatus, InvoiceType
from app.domains.invoicing.schemas import InvoiceResponse
from app.domains.finance.service import FinanceService
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError, InsufficientBalanceError
from app.core.logging_conf import logger
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.audit import audit_log
from app.core.idempotency import get_idempotency_result, store_idempotency_result
from app.core.pagination import PaginatedResponse


class InvoicingService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = InvoicingRepository(db)
        self.finance = FinanceService(db, tenant_id)
        self.event_bus = EventBus(redis_client)

    # ============================================================
    # دوال Idempotency الموحّدة (مع tenant_id)
    # ============================================================

    async def _validate_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        if idempotency_key:
            cache_key = f"idempotency:{self.tenant_id}:{idempotency_key}"
            cached = await get_idempotency_result(cache_key)
            if cached is not None:
                return cached
        return None

    async def _store_idempotency(self, idempotency_key: str, result: Dict[str, Any]):
        if idempotency_key:
            cache_key = f"idempotency:{self.tenant_id}:{idempotency_key}"
            await store_idempotency_result(cache_key, result)

    # ============================================================
    # 1. إنشاء فاتورة جديدة (مع tenant_id)
    # ============================================================

    async def create_invoice(
        self,
        entity_id: int,
        user_id: int,
        amount: Decimal,
        description: str,
        due_date: Optional[datetime] = None,
        invoice_type: str = "SERVICE",
        reference_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
    ) -> Invoice:
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                invoice_id = cached.get("invoice_id")
                if invoice_id:
                    invoice = await self.repo.get_invoice(invoice_id, self.tenant_id)
                    if invoice:
                        return invoice
                raise ValidationError("Idempotency record exists but invoice not found.")

        if due_date is None:
            due_date = datetime.utcnow() + timedelta(days=30)

        invoice_data = {
            "tenant_id": entity_id,
            "user_id": user_id,
            "amount": amount,
            "description": description,
            "due_date": due_date,
            "invoice_type": invoice_type,
            "reference_id": reference_id,
            "status": InvoiceStatus.PENDING,
            "invoice_number": await self._generate_invoice_number(entity_id),
            "idempotency_key": idempotency_key,
        }

        invoice = await self.repo.create_invoice(**invoice_data)

        await audit_log(
            user_id=user_id,
            tenant_id=entity_id,
            action="INVOICE_CREATED",
            resource_id=invoice.id,
            details={
                "amount": float(amount),
                "type": invoice_type,
                "due_date": due_date.isoformat(),
            },
        )

        await self.event_bus.publish("invoicing.invoice.created", {
            "invoice_id": invoice.id,
            "tenant_id": entity_id,
            "user_id": user_id,
            "amount": float(amount),
            "due_date": due_date.isoformat(),
        })

        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"invoice_id": invoice.id})

        return invoice

    async def _generate_invoice_number(self, tenant_id: int) -> str:
        prefix = "INV"
        count = await self.repo.count_invoices(tenant_id)
        seq = str(count + 1).zfill(6)
        return f"{prefix}-{tenant_id}-{seq}"

    # ============================================================
    # 2. جلب الفواتير (مع tenant_id)
    # ============================================================

    async def get_invoice(self, invoice_id: int, tenant_id: Optional[int] = None) -> Invoice:
        target_tenant = tenant_id or self.tenant_id
        invoice = await self.repo.get_invoice(invoice_id, target_tenant)
        if not invoice:
            raise NotFoundError(f"Invoice {invoice_id} not found")
        return invoice

    async def list_invoices(
        self,
        user_id: Optional[int] = None,
        status: Optional[InvoiceStatus] = None,
        invoice_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> PaginatedResponse[InvoiceResponse]:
        return await self.repo.list_invoices(
            tenant_id=self.tenant_id,
            user_id=user_id,
            status=status,
            invoice_type=invoice_type,
            reference_id=reference_id,
            skip=skip,
            limit=limit,
        )

    async def get_invoices_by_reference(
        self,
        reference_id: int,
        invoice_type: Optional[str] = None,
    ) -> List[Invoice]:
        return await self.repo.get_invoices_by_reference(
            tenant_id=self.tenant_id,
            reference_id=reference_id,
            invoice_type=invoice_type,
        )

    # ============================================================
    # 3. تحديث حالة الفاتورة (مع التكامل المالي)
    # ============================================================

    async def update_invoice_status(
        self,
        invoice_id: int,
        status: str,
        user_id: int,
        notes: Optional[str] = None,
    ) -> Invoice:
        invoice = await self.repo.get_invoice(invoice_id, self.tenant_id)
        if not invoice:
            raise NotFoundError(f"Invoice {invoice_id} not found")

        current_status = cast(InvoiceStatus, invoice.status)
        if current_status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED]:
            raise ValidationError(f"Cannot update invoice with status: {current_status.value}")

        try:
            new_status = InvoiceStatus(status)
        except ValueError:
            raise ValidationError(f"Invalid invoice status: {status}")

        payment_tx_hash = None
        if new_status == InvoiceStatus.PAID:
            try:
                tx = await self.finance.transfer(
                    sender_id=user_id,
                    receiver_email="system@eppne.com",
                    currency=invoice.currency,
                    amount=invoice.amount,
                    idempotency_key=f"INV-PAY-{invoice_id}-{uuid.uuid4().hex[:8]}",
                    notes=f"دفع الفاتورة {invoice.invoice_number}",
                )
                payment_tx_hash = tx.tx_hash
                logger.info(f"Invoice {invoice.invoice_number} paid via FinanceService, tx: {payment_tx_hash}")
            except InsufficientBalanceError as e:
                raise ValidationError(f"رصيد غير كافٍ لدفع الفاتورة: {str(e)}")
            except Exception as e:
                raise ValidationError(f"فشل عملية الدفع المالية: {str(e)}")

        updated = await self.repo.update_invoice(
            invoice_id,
            self.tenant_id,
            status=new_status,
            paid_at=datetime.utcnow() if new_status == InvoiceStatus.PAID else None,
            notes=notes,
        )

        await audit_log(
            user_id=user_id,
            tenant_id=self.tenant_id,
            action="INVOICE_STATUS_UPDATED",
            resource_id=invoice_id,
            details={
                "old_status": current_status.value,
                "new_status": new_status.value,
                "notes": notes,
                "payment_tx_hash": payment_tx_hash,
            },
        )

        await self.event_bus.publish("invoicing.invoice.status_changed", {
            "invoice_id": invoice_id,
            "tenant_id": self.tenant_id,
            "status": new_status.value,
            "user_id": user_id,
            "payment_tx_hash": payment_tx_hash,
        })

        return updated

    async def mark_as_paid(
        self,
        invoice_id: int,
        user_id: int,
        payment_tx_hash: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Invoice:
        invoice = await self.repo.get_invoice(invoice_id, self.tenant_id)
        if not invoice:
            raise NotFoundError(f"Invoice {invoice_id} not found")

        current_status = cast(InvoiceStatus, invoice.status)
        if current_status == InvoiceStatus.PAID:
            return invoice

        return await self.update_invoice_status(
            invoice_id=invoice_id,
            status=InvoiceStatus.PAID.value,
            user_id=user_id,
            notes=notes or f"Paid via tx: {payment_tx_hash or 'manual'}",
        )

    async def cancel_invoice(
        self,
        invoice_id: int,
        user_id: int,
        reason: Optional[str] = None,
    ) -> Invoice:
        return await self.update_invoice_status(
            invoice_id=invoice_id,
            status=InvoiceStatus.CANCELLED.value,
            user_id=user_id,
            notes=reason or "Cancelled by user",
        )

    # ============================================================
    # 4. إحصائيات الفواتير (مع tenant_id)
    # ============================================================

    async def get_invoice_stats(self) -> Dict[str, Any]:
        total_pending = await self.repo.sum_amount_by_status(self.tenant_id, InvoiceStatus.PENDING)
        total_paid = await self.repo.sum_amount_by_status(self.tenant_id, InvoiceStatus.PAID)
        total_overdue = await self.repo.sum_amount_by_status(self.tenant_id, InvoiceStatus.OVERDUE)
        total_cancelled = await self.repo.sum_amount_by_status(self.tenant_id, InvoiceStatus.CANCELLED)

        overdue_count = await self.repo.count_overdue_invoices(self.tenant_id)

        return {
            "tenant_id": self.tenant_id,
            "total_pending": float(total_pending),
            "total_paid": float(total_paid),
            "total_overdue": float(total_overdue),
            "total_cancelled": float(total_cancelled),
            "overdue_count": overdue_count,
            "currency": "MR_USDT",
            "updated_at": datetime.utcnow().isoformat(),
        }

    # ============================================================
    # 5. معالجة الفواتير المتأخرة (لمهمة Celery) – مع tenant_id
    # ============================================================

    async def process_overdue_invoices(self, tenant_id: Optional[int] = None) -> int:
        target_tenant = tenant_id or self.tenant_id
        overdue = await self.repo.get_overdue_invoices(target_tenant)
        count = 0

        for invoice in overdue:
            current_status = cast(InvoiceStatus, invoice.status)
            if current_status == InvoiceStatus.PENDING:
                invoice_id = cast(int, invoice.id)
                await self.repo.update_invoice(
                    invoice_id,
                    target_tenant,
                    status=InvoiceStatus.OVERDUE,
                    notes="Automatically marked as overdue",
                )
                await self.event_bus.publish("invoicing.invoice.overdue", {
                    "invoice_id": invoice_id,
                    "tenant_id": target_tenant,
                    "user_id": invoice.user_id,
                    "amount": float(cast(Decimal, invoice.amount)),
                    "due_date": invoice.due_date.isoformat(),
                })
                count += 1

        logger.info(f"Processed {count} overdue invoices for tenant {target_tenant}")
        return count