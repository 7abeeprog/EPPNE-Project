# app/domains/invoicing/router.py
"""
روتر (Router) قطاع الفواتير – يوفر واجهة برمجة تطبيقات (API) لإدارة الفواتير.
يدعم: إنشاء الفواتير، جلبها، تحديث الحالة، الدفع، الإلغاء، والإحصائيات.
"""
from typing import Optional, List, cast
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import datetime

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, require_sector
from app.domains.identity.models import User
from app.domains.invoicing.service import InvoicingService
from app.domains.invoicing.schemas import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    InvoiceListResponse,
    InvoiceStatsResponse,
    InvoiceFilter,
)
from app.domains.invoicing.models import InvoiceStatus, InvoiceType
from app.core.rate_limiter import rate_limit
from app.core.logging_conf import logger

router = APIRouter(prefix="/invoicing", tags=["Invoicing"])


# ============================================================
# 1. إنشاء فاتورة جديدة
# ============================================================
@router.post(
    "/invoices",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء فاتورة جديدة",
    description="إنشاء فاتورة جديدة للمستخدم أو للنظام.",
)
@rate_limit(max_requests=20, window_seconds=60)
async def create_invoice(
    data: InvoiceCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """
    إنشاء فاتورة جديدة.
    """
    service = InvoicingService(db)

    try:
        invoice = await service.create_invoice(
            entity_id=data.tenant_id,
            user_id=data.user_id or 0,
            amount=data.amount,
            description=data.description or "فاتورة خدمة",
            due_date=data.due_date,
            invoice_type=data.invoice_type.value,
            reference_id=data.reference_id,
            idempotency_key=data.idempotency_key,
        )

        logger.info(f"Invoice created: {invoice.invoice_number} by user {current_user.id}")

        return InvoiceResponse.model_validate(invoice)

    except Exception as e:
        logger.error(f"Failed to create invoice: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# 2. جلب فاتورة بواسطة المعرف
# ============================================================
@router.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceResponse,
    summary="جلب فاتورة",
    description="جلب تفاصيل فاتورة محددة بواسطة المعرف.",
)
async def get_invoice(
    invoice_id: int = Path(..., ge=1, description="معرف الفاتورة"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """
    جلب تفاصيل فاتورة محددة.
    """
    service = InvoicingService(db)

    try:
        tenant_id = None if getattr(current_user, "system_role", "USER") in ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"] else cast(int, current_user.tenant_id)
        invoice = await service.get_invoice(invoice_id, tenant_id)

        return InvoiceResponse.model_validate(invoice)

    except Exception as e:
        logger.warning(f"Failed to get invoice {invoice_id}: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================
# 3. قائمة الفواتير مع التصفية
# ============================================================
@router.get(
    "/invoices",
    response_model=InvoiceListResponse,
    summary="قائمة الفواتير",
    description="جلب قائمة الفواتير مع خيارات التصفية والترحيل.",
)
async def list_invoices(
    tenant_id: Optional[int] = Query(None, description="تصفية حسب المستأجر"),
    user_id: Optional[int] = Query(None, description="تصفية حسب المستخدم"),
    status: Optional[InvoiceStatus] = Query(None, description="تصفية حسب الحالة"),
    invoice_type: Optional[InvoiceType] = Query(None, description="تصفية حسب النوع"),
    skip: int = Query(0, ge=0, description="عدد السجلات المتجاوزة"),
    limit: int = Query(50, ge=1, le=200, description="عدد السجلات لكل صفحة"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceListResponse:
    """
    جلب قائمة الفواتير مع خيارات التصفية.
    """
    service = InvoicingService(db)

    if tenant_id is None:
        if getattr(current_user, "system_role", "USER") in ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]:
            tenant_id = None
        else:
            tenant_id = cast(int, current_user.tenant_id)
    else:
        if getattr(current_user, "system_role", "USER") not in ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]:
            if tenant_id != cast(int, current_user.tenant_id):
                raise HTTPException(status_code=403, detail="Access denied to this tenant")

    if tenant_id is None:
        from sqlalchemy import select
        query = select(Invoice)
        if user_id:
            query = query.where(Invoice.user_id == user_id)
        if status:
            query = query.where(Invoice.status == status)
        if invoice_type:
            query = query.where(Invoice.invoice_type == invoice_type)
        query = query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        invoices = list(result.scalars().all())
    else:
        invoices = await service.list_invoices(
            tenant_id=tenant_id,
            user_id=user_id,
            status=status,
            invoice_type=invoice_type.value if invoice_type else None,
            skip=skip,
            limit=limit,
        )

    items = [InvoiceResponse.model_validate(inv) for inv in invoices]
    total = len(items)

    return InvoiceListResponse(items=items, total=total, skip=skip, limit=limit)


# ============================================================
# 4. تحديث حالة الفاتورة
# ============================================================
@router.patch(
    "/invoices/{invoice_id}/status",
    response_model=InvoiceResponse,
    summary="تحديث حالة الفاتورة",
    description="تحديث حالة الفاتورة (دفع، إلغاء، إلخ).",
)
@rate_limit(max_requests=10, window_seconds=60)
async def update_invoice_status(
    invoice_id: int = Path(..., ge=1),
    status: InvoiceStatus = Query(..., description="الحالة الجديدة"),
    notes: Optional[str] = Query(None, description="ملاحظات إضافية"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """
    تحديث حالة الفاتورة.
    """
    service = InvoicingService(db)

    try:
        invoice = await service.update_invoice_status(
            invoice_id=invoice_id,
            status=status.value,
            user_id=cast(int, current_user.id),
            notes=notes,
        )

        logger.info(f"Invoice {invoice.invoice_number} status updated to {status.value} by user {current_user.id}")

        return InvoiceResponse.model_validate(invoice)

    except Exception as e:
        logger.error(f"Failed to update invoice status: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# 5. تحديد الفاتورة كمدفوعة
# ============================================================
@router.post(
    "/invoices/{invoice_id}/pay",
    response_model=InvoiceResponse,
    summary="تحديد الفاتورة كمدفوعة",
    description="تحديد الفاتورة كمدفوعة (تغيير الحالة إلى PAID).",
)
@rate_limit(max_requests=10, window_seconds=60)
async def mark_invoice_as_paid(
    invoice_id: int = Path(..., ge=1),
    payment_tx_hash: Optional[str] = Query(None, description="هاش معاملة الدفع"),
    notes: Optional[str] = Query(None, description="ملاحظات إضافية"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """
    تحديد الفاتورة كمدفوعة.
    """
    service = InvoicingService(db)

    try:
        invoice = await service.mark_as_paid(
            invoice_id=invoice_id,
            user_id=cast(int, current_user.id),
            payment_tx_hash=payment_tx_hash,
            notes=notes,
        )

        logger.info(f"Invoice {invoice.invoice_number} marked as paid by user {current_user.id}")

        return InvoiceResponse.model_validate(invoice)

    except Exception as e:
        logger.error(f"Failed to mark invoice as paid: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# 6. إلغاء الفاتورة
# ============================================================
@router.post(
    "/invoices/{invoice_id}/cancel",
    response_model=InvoiceResponse,
    summary="إلغاء الفاتورة",
    description="إلغاء الفاتورة (تغيير الحالة إلى CANCELLED).",
)
@rate_limit(max_requests=10, window_seconds=60)
async def cancel_invoice(
    invoice_id: int = Path(..., ge=1),
    reason: Optional[str] = Query(None, description="سبب الإلغاء"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """
    إلغاء الفاتورة.
    """
    service = InvoicingService(db)

    try:
        invoice = await service.cancel_invoice(
            invoice_id=invoice_id,
            user_id=cast(int, current_user.id),
            reason=reason,
        )

        logger.info(f"Invoice {invoice.invoice_number} cancelled by user {current_user.id}")

        return InvoiceResponse.model_validate(invoice)

    except Exception as e:
        logger.error(f"Failed to cancel invoice: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# 7. إحصائيات الفواتير
# ============================================================
@router.get(
    "/stats",
    response_model=InvoiceStatsResponse,
    summary="إحصائيات الفواتير",
    description="جلب إحصائيات الفواتير للمستأجر الحالي.",
)
async def get_invoice_stats(
    tenant_id: Optional[int] = Query(None, description="معرف المستأجر (للسوبر أدمن)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceStatsResponse:
    """
    جلب إحصائيات الفواتير.
    """
    service = InvoicingService(db)

    if tenant_id is None:
        tenant_id = cast(int, current_user.tenant_id)
    else:
        if getattr(current_user, "system_role", "USER") not in ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]:
            if tenant_id != cast(int, current_user.tenant_id):
                raise HTTPException(status_code=403, detail="Access denied to this tenant")

    try:
        stats = await service.get_invoice_stats(tenant_id)
        return InvoiceStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Failed to get invoice stats: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# 8. (إداري) معالجة الفواتير المتأخرة
# ============================================================
@router.post(
    "/admin/process-overdue",
    summary="معالجة الفواتير المتأخرة",
    description="معالجة الفواتير التي تجاوزت تاريخ الاستحقاق (يُستخدم من Celery).",
    dependencies=[Depends(get_current_superuser)],
)
async def process_overdue_invoices(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    معالجة الفواتير المتأخرة (تغيير حالتها إلى OVERDUE وإرسال تنبيهات).
    """
    service = InvoicingService(db)

    try:
        count = await service.process_overdue_invoices()
        return {"message": f"Processed {count} overdue invoices", "count": count}

    except Exception as e:
        logger.error(f"Failed to process overdue invoices: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))