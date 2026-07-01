# app/domains/saas/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timedelta

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, require_subscription
from app.domains.identity.models import User
from app.domains.saas.service import SaaSControlService
from app.domains.saas.repository import SaaSRepository
from app.domains.saas.schemas import *
from app.core.rate_limiter import rate_limit
from app.core.logging import logger

router = APIRouter(prefix="/saas", tags=["Sovereign SaaS"])


# ==========================================
# 1. الخدمات (Services)
# ==========================================

@router.get(
    "/services",
    response_model=List[ServiceCatalogResponse],
    summary="جلب جميع الخدمات المتاحة",
    description="عرض كتالوج الخدمات المتاحة على المنصة (للمشرفين فقط)."
)
@rate_limit(max_requests=30, window_seconds=60)
async def list_services(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    repo = SaaSRepository(db)
    services = await repo.get_all_services()
    return services


@router.post(
    "/services",
    response_model=ServiceCatalogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء خدمة جديدة",
    description="إضافة خدمة جديدة إلى كتالوج المنصة (للمشرفين فقط)."
)
@rate_limit(max_requests=10, window_seconds=60)
async def create_service(
    data: ServiceCatalogCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    repo = SaaSRepository(db)
    service = await repo.create_service(**data.model_dump())
    logger.info(f"Service created: {service.code} by user {current_user.id}")
    return service


@router.get(
    "/services/{service_id}",
    response_model=ServiceCatalogResponse,
    summary="جلب تفاصيل خدمة",
)
async def get_service(
    service_id: int = Path(..., description="معرف الخدمة"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SaaSRepository(db)
    service = await repo.get_service_by_id(service_id)
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الخدمة غير موجودة")
    return service


# ==========================================
# 2. خطط التسعير (Plans)
# ==========================================

@router.get(
    "/services/{service_id}/plans",
    response_model=List[ServicePlanResponse],
    summary="جلب خطط خدمة معينة",
)
async def list_service_plans(
    service_id: int = Path(..., description="معرف الخدمة"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SaaSRepository(db)
    plans = await repo.get_plans_by_service(service_id)
    return plans


@router.post(
    "/plans",
    response_model=ServicePlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء خطة تسعير جديدة",
    description="إضافة خطة جديدة لخدمة معينة (للمشرفين فقط)."
)
@rate_limit(max_requests=10, window_seconds=60)
async def create_plan(
    data: ServicePlanCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    repo = SaaSRepository(db)
    plan = await repo.create_plan(**data.model_dump())
    logger.info(f"Plan created: {plan.code} for service {plan.service_id} by user {current_user.id}")
    return plan


# ==========================================
# 3. اشتراكات المستأجر (Subscriptions)
# ==========================================

@router.get(
    "/subscriptions",
    response_model=PaginatedResponse[TenantSubscriptionResponse],
    summary="جلب اشتراكاتي",
    description="عرض جميع اشتراكات المستأجر الحالي مع Pagination."
)
async def get_my_subscriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SaaSRepository(db)
    return await repo.get_tenant_subscriptions(current_user.tenant_id, skip, limit)


@router.post(
    "/subscriptions/{plan_id}",
    response_model=TenantSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="الاشتراك في خطة جديدة",
    description="تفعيل اشتراك جديد لمستأجر في خطة محددة."
)
@rate_limit(max_requests=5, window_seconds=60)
async def subscribe_to_plan(
    plan_id: int = Path(..., description="معرف الخطة"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSControlService(db)
    subscription = await service.create_subscription(
        tenant_id=current_user.tenant_id,
        plan_id=plan_id,
        start_date=datetime.utcnow(),
    )
    return subscription


@router.put(
    "/subscriptions/{subscription_id}/cancel",
    response_model=TenantSubscriptionResponse,
    summary="إلغاء الاشتراك",
    description="إلغاء الاشتراك الحالي (سيتم إيقاف التجديد التلقائي)."
)
async def cancel_subscription(
    subscription_id: int = Path(..., description="معرف الاشتراك"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSControlService(db)
    subscription = await service.cancel_subscription(
        subscription_id=subscription_id,
        tenant_id=current_user.tenant_id,
    )
    return subscription


@router.get(
    "/subscriptions/{subscription_id}/status",
    summary="حالة الاشتراك",
    description="عرض حالة الاشتراك الحالية."
)
async def get_subscription_status(
    subscription_id: int = Path(..., description="معرف الاشتراك"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SaaSRepository(db)
    subscription = await repo.get_subscription(subscription_id)
    if not subscription or subscription.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الاشتراك غير موجود")

    return {
        "id": subscription.id,
        "status": subscription.status,
        "plan": subscription.plan.name if subscription.plan else None,
        "grace_period_end_date": subscription.grace_period_end_date,
        "next_billing_date": subscription.next_billing_date,
        "is_active": subscription.status in ["ACTIVE", "TRIAL"],
    }


# ==========================================
# 4. صلاحيات الوصول (Access Control)
# ==========================================

@router.get(
    "/access",
    response_model=List[ServiceAccessStatus],
    summary="حالة الوصول للخدمات",
    description="عرض جميع الخدمات مع حالة الوصول للمستأجر الحالي."
)
async def get_services_access(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SaaSRepository(db)
    services_with_access = await repo.get_services_with_access(current_user.tenant_id)
    return services_with_access


@router.get(
    "/access/{service_code}",
    response_model=CheckAccessResponse,
    summary="التحقق من صلاحية خدمة محددة",
)
async def check_service_access(
    service_code: str = Path(..., description="كود الخدمة (مثال: academy)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSControlService(db)
    accessible = await service.can_access_service(current_user.tenant_id, service_code)
    reason = None
    if not accessible:
        reason = "الخدمة غير متاحة. يرجى الاشتراك في الخطة المناسبة."

    return {"service_code": service_code, "accessible": accessible, "reason": reason}


# ==========================================
# 5. الفواتير (Invoices)
# ==========================================

@router.get(
    "/invoices",
    response_model=PaginatedResponse[InvoiceResponse],
    summary="جلب فواتيري",
    description="عرض جميع فواتير المستأجر الحالي."
)
async def get_my_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="حالة الفاتورة"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SaaSRepository(db)
    return await repo.get_tenant_invoices(current_user.tenant_id, skip, limit)


@router.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceResponse,
    summary="جلب تفاصيل فاتورة",
)
async def get_invoice(
    invoice_id: int = Path(..., description="معرف الفاتورة"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SaaSRepository(db)
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice or invoice.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الفاتورة غير موجودة")
    return invoice


@router.post(
    "/invoices/{invoice_id}/pay",
    response_model=InvoiceResponse,
    summary="دفع فاتورة",
    description="دفع فاتورة مستحقة باستخدام المحفظة السيادية."
)
@rate_limit(max_requests=5, window_seconds=60)
async def pay_invoice(
    invoice_id: int = Path(..., description="معرف الفاتورة"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSControlService(db)
    invoice = await service.pay_invoice(
        invoice_id=invoice_id,
        tenant_id=current_user.tenant_id,
    )
    return invoice


# ==========================================
# 6. رايات الميزات (Feature Flags) - للمشرفين
# ==========================================

@router.get(
    "/feature-flags",
    summary="جلب جميع رايات الميزات للمستأجر",
    description="عرض رايات الميزات المفعلة والمعطلة للمستأجر الحالي (للمشرفين فقط)."
)
async def list_feature_flags(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    repo = SaaSRepository(db)
    result = await db.execute(
        select(TenantFeatureFlag).where(TenantFeatureFlag.tenant_id == current_user.tenant_id)
    )
    flags = result.scalars().all()
    return flags


@router.post(
    "/feature-flags/{service_code}/{feature_key}",
    summary="تفعيل/تعطيل ميزة",
    description="تغيير حالة راية ميزة محددة (للمشرفين فقط)."
)
@rate_limit(max_requests=10, window_seconds=60)
async def toggle_feature_flag(
    service_code: str = Path(..., description="كود الخدمة"),
    feature_key: str = Path(..., description="مفتاح الميزة"),
    enabled: bool = Query(..., description="True للتفعيل، False للتعطيل"),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSControlService(db)
    flag = await service.toggle_feature_flag(
        tenant_id=current_user.tenant_id,
        service_code=service_code,
        feature_key=feature_key,
        enabled=enabled,
    )
    return {"message": f"تم {'تفعيل' if enabled else 'تعطيل'} الميزة '{feature_key}' بنجاح", "flag": flag}


# ==========================================
# 7. إحصائيات وإدارة النظام (للمشرفين)
# ==========================================

@router.get(
    "/admin/tenant/{tenant_id}/subscriptions",
    summary="جلب اشتراكات مستأجر محدد",
    description="عرض جميع اشتراكات مستأجر معين (للمشرفين فقط)."
)
async def get_tenant_subscriptions_admin(
    tenant_id: int = Path(..., description="معرف المستأجر"),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    repo = SaaSRepository(db)
    return await repo.get_tenant_subscriptions(tenant_id)


@router.get(
    "/admin/dashboard",
    summary="لوحة تحكم SaaS",
    description="إحصائيات الخدمات والاشتراكات والفوترة (للمشرفين فقط)."
)
@rate_limit(max_requests=10, window_seconds=60)
async def get_saas_dashboard(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSControlService(db)
    stats = await service.get_dashboard_stats()
    return stats


@router.post(
    "/admin/trigger-renewals",
    summary="تشغيل تجديد الاشتراكات يدوياً",
    description="تشغيل مهمة تجديد الاشتراكات التلقائية يدوياً (للمشرفين فقط)."
)
@rate_limit(max_requests=5, window_seconds=300)
async def trigger_renewals(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    from app.tasks.saas_tasks import process_auto_renewals_task
    process_auto_renewals_task.delay()
    return {"message": "تم تشغيل مهمة تجديد الاشتراكات بنجاح"}