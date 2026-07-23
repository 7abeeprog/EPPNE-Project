# app/domains/invoicing/service.py
"""
خدمة الفواتير (Invoicing Service) – إدارة الفواتير الصادرة والواردة.
تدعم: إنشاء الفواتير، تحديث الحالة، الدفع، وإعادة المحاولة.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from typing import Optional, List, Dict, Any, cast
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from app.domains.invoicing.repository import InvoicingRepository
from app.domains.invoicing.models import Invoice, InvoiceStatus, InvoiceType
from app.domains.invoicing.schemas import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    InvoiceFilter,
)
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.core.logging_conf import logger
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.audit import audit_log
from app.core.idempotency import get_idempotency_result, store_idempotency_result


class InvoicingService:
    """
    خدمة الفواتير الأساسية والمتقدمة.
    يدعم إنشاء الفواتير، تحديث الحالة، الدفع، وإعادة المحاولة.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = InvoicingRepository(db)
        self.event_bus = EventBus(redis_client)  # type: ignore

    # ============================================================
    # دوال Idempotency الموحّدة
    # ============================================================

    async def _validate_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """التحقق من وجود نتيجة مخزنة مسبقاً لمفتاح Idempotency."""
        if idempotency_key:
            cached = await get_idempotency_result(idempotency_key)
            if cached is not None:
                return cached
        return None

    async def _store_idempotency(self, idempotency_key: str, result: Dict[str, Any]):
        """تخزين نتيجة العملية بعد النجاح."""
        if idempotency_key:
            await store_idempotency_result(idempotency_key, result)

    # ============================================================
    # 1. إنشاء فاتورة جديدة
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
        """
        إنشاء فاتورة جديدة.
        - entity_id: معرف المستأجر (tenant_id)
        - user_id: معرف المستخدم (قد يكون 0 للفواتير النظامية)
        - amount: المبلغ
        - description: وصف الفاتورة
        - due_date: تاريخ الاستحقاق (افتراضي 30 يوماً من الآن)
        - invoice_type: نوع الفاتورة (SERVICE, AI_USAGE, SUBSCRIPTION, إلخ)
        - reference_id: معرف مرجعي (مثل order_id, subscription_id)
        - idempotency_key: مفتاح عدم التكرار
        """
        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                invoice_id = cached.get("invoice_id")
                if invoice_id:
                    invoice = await self.repo.get_invoice(invoice_id)
                    if invoice:
                        return invoice
                raise ValidationError("Idempotency record exists but invoice not found.")

        # 2. إنشاء الفاتورة
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

        # 3. تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=entity_id,  # type: ignore
            action="INVOICE_CREATED",
            resource_id=invoice.id,  # type: ignore
            details={
                "amount": float(amount),
                "type": invoice_type,
                "due_date": due_date.isoformat(),
            },
        )

        # 4. نشر حدث
        await self.event_bus.publish("invoicing.invoice.created", {
            "invoice_id": invoice.id,
            "tenant_id": entity_id,
            "user_id": user_id,
            "amount": float(amount),
            "due_date": due_date.isoformat(),
        })

        # 5. تخزين Idempotency
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"invoice_id": invoice.id})

        return invoice

    async def _generate_invoice_number(self, tenant_id: int) -> str:
        """توليد رقم فاتورة فريد."""
        prefix = "INV"
        # جلب عدد الفواتير الحالية للمستأجر
        count = await self.repo.count_invoices(tenant_id)
        seq = str(count + 1).zfill(6)
        return f"{prefix}-{tenant_id}-{seq}"

    # ============================================================
    # 2. جلب الفواتير
    # ============================================================

    async def get_invoice(self, invoice_id: int, tenant_id: Optional[int] = None) -> Invoice:
        """جلب فاتورة بواسطة المعرف مع التحقق من المستأجر (اختياري)."""
        invoice = await self.repo.get_invoice(invoice_id)
        if not invoice:
            raise NotFoundError(f"Invoice {invoice_id} not found")
        # 🔥 استخدام cast لتحويل Column[int] إلى int للمقارنة
        if tenant_id is not None and cast(int, invoice.tenant_id) != tenant_id:
            raise PermissionDeniedError("You do not have access to this invoice")
        return invoice

    async def list_invoices(
        self,
        tenant_id: int,
        user_id: Optional[int] = None,
        status: Optional[InvoiceStatus] = None,
        invoice_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Invoice]:
        """قائمة الفواتير مع الفلترة."""
        return await self.repo.list_invoices(
            tenant_id=tenant_id,
            user_id=user_id,
            status=status,
            invoice_type=invoice_type,
            skip=skip,
            limit=limit,
        )

    async def get_invoices_by_reference(
        self,
        tenant_id: int,
        reference_id: int,
        invoice_type: Optional[str] = None,
    ) -> List[Invoice]:
        """جلب الفواتير المرتبطة بمرجع معين (مثل order_id)."""
        return await self.repo.get_invoices_by_reference(
            tenant_id=tenant_id,
            reference_id=reference_id,
            invoice_type=invoice_type,
        )

    # ============================================================
    # 3. تحديث حالة الفاتورة
    # ============================================================

    async def update_invoice_status(
        self,
        invoice_id: int,
        status: str,
        user_id: int,
        notes: Optional[str] = None,
    ) -> Invoice:
        """تحديث حالة الفاتورة (مثل الدفع أو الإلغاء)."""
        invoice = await self.repo.get_invoice(invoice_id)
        if not invoice:
            raise NotFoundError(f"Invoice {invoice_id} not found")

        # 🔥 استخدام cast لتحويل Column[Enum] إلى Enum
        current_status = cast(InvoiceStatus, invoice.status)
        if current_status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED]:
            raise ValidationError(f"Cannot update invoice with status: {current_status.value}")

        # تحويل الحالة إلى النوع الصحيح
        try:
            new_status = InvoiceStatus(status)
        except ValueError:
            raise ValidationError(f"Invalid invoice status: {status}")

        updated = await self.repo.update_invoice(
            invoice_id,
            status=new_status,
            paid_at=datetime.utcnow() if new_status == InvoiceStatus.PAID else None,
            notes=notes,
        )

        # تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=invoice.tenant_id,  # type: ignore
            action="INVOICE_STATUS_UPDATED",
            resource_id=invoice_id,  # type: ignore
            details={
                "old_status": current_status.value,
                "new_status": new_status.value,
                "notes": notes,
            },
        )

        # نشر حدث
        await self.event_bus.publish("invoicing.invoice.status_changed", {
            "invoice_id": invoice_id,
            "tenant_id": invoice.tenant_id,
            "status": new_status.value,
            "user_id": user_id,
        })

        return updated

    async def mark_as_paid(
        self,
        invoice_id: int,
        user_id: int,
        payment_tx_hash: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Invoice:
        """تحديد الفاتورة كمدفوعة."""
        invoice = await self.repo.get_invoice(invoice_id)
        if not invoice:
            raise NotFoundError(f"Invoice {invoice_id} not found")

        # 🔥 استخدام cast لتحويل Column[Enum] إلى Enum
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
        """إلغاء الفاتورة."""
        return await self.update_invoice_status(
            invoice_id=invoice_id,
            status=InvoiceStatus.CANCELLED.value,
            user_id=user_id,
            notes=reason or "Cancelled by user",
        )

    # ============================================================
    # 4. إحصائيات الفواتير
    # ============================================================

    async def get_invoice_stats(self, tenant_id: int) -> Dict[str, Any]:
        """جلب إحصائيات الفواتير للمستأجر."""
        total_pending = await self.repo.sum_amount_by_status(tenant_id, InvoiceStatus.PENDING)
        total_paid = await self.repo.sum_amount_by_status(tenant_id, InvoiceStatus.PAID)
        total_overdue = await self.repo.sum_amount_by_status(tenant_id, InvoiceStatus.OVERDUE)
        total_cancelled = await self.repo.sum_amount_by_status(tenant_id, InvoiceStatus.CANCELLED)

        # عدد الفواتير المتأخرة
        overdue_count = await self.repo.count_overdue_invoices(tenant_id)

        return {
            "tenant_id": tenant_id,
            "total_pending": float(total_pending),
            "total_paid": float(total_paid),
            "total_overdue": float(total_overdue),
            "total_cancelled": float(total_cancelled),
            "overdue_count": overdue_count,
            "currency": "MR_USDT",
            "updated_at": datetime.utcnow().isoformat(),
        }

    # ============================================================
    # 5. معالجة الفواتير المتأخرة (لمهمة Celery)
    # ============================================================

    async def process_overdue_invoices(self) -> int:
        """
        معالجة الفواتير المتأخرة (تغيير حالتها إلى OVERDUE وإرسال تنبيهات).
        تُستدعى من مهمة Celery المجدولة.
        """
        overdue = await self.repo.get_overdue_invoices()
        count = 0
        for invoice in overdue:
            # 🔥 استخدام cast لتحويل Column[Enum] إلى Enum
            current_status = cast(InvoiceStatus, invoice.status)
            if current_status == InvoiceStatus.PENDING:
                # 🔥 استخدام cast لتحويل Column[int] إلى int
                invoice_id = cast(int, invoice.id)
                await self.repo.update_invoice(
                    invoice_id,
                    status=InvoiceStatus.OVERDUE,
                    notes="Automatically marked as overdue",
                )
                # إرسال حدث للتنبيه
                await self.event_bus.publish("invoicing.invoice.overdue", {
                    "invoice_id": invoice_id,
                    "tenant_id": invoice.tenant_id,
                    "user_id": invoice.user_id,
                    "amount": float(cast(Decimal, invoice.amount)),
                    "due_date": invoice.due_date.isoformat(),
                })
                count += 1
        return count