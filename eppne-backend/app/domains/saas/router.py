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
# 1. الخدمات (Services) – للمشرفين
# ==========================================

@router.get("/services", response_model=List[ServiceCatalogResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_services(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SaaSControlService(db, tenant_id)
    return await service.get_all_services()


@router.post("/services", response_model=ServiceCatalogResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_service(
    data: ServiceCatalogCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SaaSControlService(db, tenant_id)
    result = await service.create_service(data.model_dump())
    logger.info(f"Service created: {result.code} by user {current_user.id}")
    return result


@router.get("/services/{service_id}", response_model=ServiceCatalogResponse)
async def get_service(
    service_id: int = Path(..., description="معرف الخدمة"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SaaSControlService(db, tenant_id)
    return await service.get_service_by_id(service_id)


# ==========================================
# 2. خطط التسعير (Plans)
# ==========================================

@router.get("/services/{service_id}/plans", response_model=List[ServicePlanResponse])
async def list_service_plans(
    service_id: int = Path(..., description="معرف الخدمة"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SaaSControlService(db, tenant_id)
    return await service.get_plans_by_service(service_id)


@router.post("/plans", response_model=ServicePlanResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_plan(
    data: ServicePlanCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SaaSControlService(db, tenant_id)
    plan = await service.create_plan(data.model_dump())
    logger.info(f"Plan created: {plan.code} for service {plan.service_id} by user {current_user.id}")
    return plan


# ==========================================
# 3. اشتراكات المستأجر (Subscriptions)
# ==========================================

@router.get("/subscriptions", response_model=PaginatedResponse[TenantSubscriptionResponse])
async def get_my_subscriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SaaSControlService(db, tenant_id)
    return await service.get_tenant_subscriptions(skip, limit)


@router.post("/subscriptions/{plan_id}", response_model=TenantSubscriptionResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, window_seconds=60)
async def subscribe_to_plan(
    plan_id: int = Path(..., description="معرف الخطة"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SaaSControlService(db, tenant_id)
    subscription = await service.create_subscription(plan_id=plan_id)
    return subscription


@router.put("/subscriptions/{subscription_id}/cancel", response_model=TenantSubscriptionResponse)
async def cancel_subscription(
    subscription_id: int = Path(..., description="معرف الاشتراك"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SaaSControlService(db, tenant_id)
    subscription = await service.cancel_subscription(subscription_id)
    return subscription


@router.get("/subscriptions/{subscription_id}/status")
async def get_subscription_status(
    subscription_id: int = Path(..., description="معرف الاشتراك"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SaaSControlService(db, tenant_id)
    return await service.get_subscription_status(subscription_id)


# ==========================================
# 4. صلاحيات الوصول (Access Control)
# ==========================================

@router.get("/access", response_model=List[ServiceAccessStatus])
async def get_services_access(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SaaSControlService(db, tenant_id)
    return await service.get_services_access()


@router.get("/access/{service_code}", response_model=CheckAccessResponse)
async def check_service_access(
    service_code: str = Path(..., description="كود الخدمة"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SaaSControlService(db, tenant_id)
    return await service.check_service_access(service_code)


# ==========================================
# 5. الفواتير (Invoices)
# ==========================================

@router.get("/invoices", response_model=PaginatedResponse[InvoiceResponse])
async def get_my_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="حالة الفاتورة"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SaaSControlService(db, tenant_id)
    return await service.get_tenant_invoices(skip, limit)


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int = Path(..., description="معرف الفاتورة"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SaaSControlService(db, tenant_id)
    return await service.get_invoice(invoice_id)


@router.post("/invoices/{invoice_id}/pay", response_model=InvoiceResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def pay_invoice(
    invoice_id: int = Path(..., description="معرف الفاتورة"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SaaSControlService(db, tenant_id)
    invoice = await service.pay_invoice(invoice_id)
    return invoice


# ==========================================
# 6. رايات الميزات (Feature Flags) – للمشرفين
# ==========================================

@router.get("/feature-flags")
async def list_feature_flags(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SaaSControlService(db, tenant_id)
    flags = await service.list_feature_flags()
    return flags


@router.post("/feature-flags/{service_code}/{feature_key}")
@rate_limit(max_requests=10, window_seconds=60)
async def toggle_feature_flag(
    service_code: str = Path(..., description="كود الخدمة"),
    feature_key: str = Path(..., description="مفتاح الميزة"),
    enabled: bool = Query(..., description="True للتفعيل، False للتعطيل"),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SaaSControlService(db, tenant_id)
    flag = await service.toggle_feature_flag(service_code, feature_key, enabled)
    return {"message": f"تم {'تفعيل' if enabled else 'تعطيل'} الميزة '{feature_key}' بنجاح", "flag": flag}


# ==========================================
# 7. إحصائيات وإدارة النظام (للمشرفين)
# ==========================================

@router.get("/admin/tenant/{tenant_id}/subscriptions")
async def get_tenant_subscriptions_admin(
    tenant_id: int = Path(..., description="معرف المستأجر"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSControlService(db, tenant_id)
    return await service.get_tenant_subscriptions_admin(tenant_id, skip, limit)


@router.get("/admin/dashboard")
@rate_limit(max_requests=10, window_seconds=60)
async def get_saas_dashboard(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = SaaSControlService(db, tenant_id)
    stats = await service.get_dashboard_stats()
    return stats


@router.post("/admin/trigger-renewals")
@rate_limit(max_requests=5, window_seconds=300)
async def trigger_renewals(
    tenant_id: Optional[int] = Query(None, description="معرف المستأجر (اختياري)"),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    # نمرر tenant_id=0 مؤقتاً، ثم نمرر target_tenant
    service = SaaSControlService(db, 0)
    results = await service.trigger_renewals(tenant_id)
    return {"message": "تم تشغيل مهمة تجديد الاشتراكات بنجاح", "results": results}