# app/domains/saas/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, cast
from datetime import datetime

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser
from app.domains.identity.models import User
from app.domains.saas.service import SaaSControlService
from app.domains.saas.schemas import *
from app.core.rate_limiter import rate_limit
import logging
from app.core.pagination import PaginatedResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/saas", tags=["Sovereign SaaS"])

# ==========================================
# 1. الخدمات (Services)
# ==========================================

@router.get(
    "/services",
    response_model=List[ServiceCatalogResponse],
    summary="جلب جميع الخدمات المتاحة",
)
@rate_limit(max_requests=30, window_seconds=60)
async def list_services(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSControlService(db)
    return await service.get_all_services()

@router.post(
    "/services",
    response_model=ServiceCatalogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء خدمة جديدة",
)
@rate_limit(max_requests=10, window_seconds=60)
async def create_service(
    data: ServiceCatalogCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSControlService(db)
    result = await service.create_service(data.model_dump())
    logger.info(f"Service created: {result.code} by user {current_user.id}")
    return result

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
    service = SaaSControlService(db)
    return await service.get_service_by_id(service_id)

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
    service = SaaSControlService(db)
    return await service.get_plans_by_service(service_id)

@router.post(
    "/plans",
    response_model=ServicePlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="إنشاء خطة تسعير جديدة",
)
@rate_limit(max_requests=10, window_seconds=60)
async def create_plan(
    data: ServicePlanCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSControlService(db)
    plan = await service.create_plan(data.model_dump())
    logger.info(f"Plan created: {plan.code} for service {plan.service_id} by user {current_user.id}")
    return plan

# ==========================================
# 3. اشتراكات المستأجر (Subscriptions)
# ==========================================

@router.get(
    "/subscriptions",
    response_model=PaginatedResponse[TenantSubscriptionResponse],
    summary="جلب اشتراكاتي",
)
async def get_my_subscriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSControlService(db)
    user_id = cast(int, current_user.id)
    return await service.get_tenant_subscriptions(current_user.tenant_id, skip, limit)

@router.post(
    "/subscriptions/{plan_id}",
    response_model=TenantSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="الاشتراك في خطة جديدة",
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
)
async def get_subscription_status(
    subscription_id: int = Path(..., description="معرف الاشتراك"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSControlService(db)
    return await service.get_subscription_status(subscription_id, current_user.tenant_id)

# ==========================================
# 4. صلاحيات الوصول (Access Control)
# ==========================================

@router.get(
    "/access",
    response_model=List[ServiceAccessStatus],
    summary="حالة الوصول للخدمات",
)
async def get_services_access(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSControlService(db)
    return await service.get_services_access(current_user.tenant_id)

@router.get(
    "/access/{service_code}",
    response_model=CheckAccessResponse,
    summary="التحقق من صلاحية خدمة محددة",
)
async def check_service_access(
    service_code: str = Path(..., description="كود الخدمة"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSControlService(db)
    return await service.check_service_access(current_user.tenant_id, service_code)

# ==========================================
# 5. الفواتير (Invoices)
# ==========================================

@router.get(
    "/invoices",
    response_model=PaginatedResponse[InvoiceResponse],
    summary="جلب فواتيري",
)
async def get_my_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="حالة الفاتورة"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSControlService(db)
    return await service.get_tenant_invoices(current_user.tenant_id, skip, limit)

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
    service = SaaSControlService(db)
    return await service.get_invoice(invoice_id, current_user.tenant_id)

@router.post(
    "/invoices/{invoice_id}/pay",
    response_model=InvoiceResponse,
    summary="دفع فاتورة",
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
)
async def list_feature_flags(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSControlService(db)
    flags = await service.list_feature_flags(current_user.tenant_id)
    return flags

@router.post(
    "/feature-flags/{service_code}/{feature_key}",
    summary="تفعيل/تعطيل ميزة",
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
)
async def get_tenant_subscriptions_admin(
    tenant_id: int = Path(..., description="معرف المستأجر"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSControlService(db)
    return await service.get_tenant_subscriptions_admin(tenant_id, skip, limit)

@router.get(
    "/admin/dashboard",
    summary="لوحة تحكم SaaS",
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
)
@rate_limit(max_requests=5, window_seconds=300)
async def trigger_renewals(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSControlService(db)
    results = await service.trigger_renewals()
    return {"message": "تم تشغيل مهمة تجديد الاشتراكات بنجاح", "results": results}