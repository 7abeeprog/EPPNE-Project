"""
مسارات (Endpoints) متجر الخدمات والتطبيقات الجاهزة
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, cast

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser
from app.domains.identity.models import User
from app.domains.service_marketplace.service import ServiceMarketplaceService
from app.domains.service_marketplace.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/marketplace", tags=["Service Marketplace - One-Click Apps"])


# ========== 1. استعراض الخدمات (عام) ==========
@router.get("/services", response_model=List[MarketplaceServiceResponse])
async def list_services(
    service_type: Optional[str] = None,
    featured: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    services = await service.list_services(cast(int, tenant.id), service_type, featured, skip, limit)
    return services


@router.get("/services/{service_id}", response_model=MarketplaceServiceResponse)
async def get_service(
    service_id: int,
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    return await service.get_service(service_id)


# ========== 2. إدارة الخدمات (للمطورين / الإدارة) ==========
@router.post("/services", response_model=MarketplaceServiceResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_service(
    data: MarketplaceServiceCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    user_id = cast(int, current_user.id)
    new_service = await service.create_service(user_id, cast(int, tenant.id), data.model_dump())
    return new_service


@router.put("/services/{service_id}/publish", response_model=MarketplaceServiceResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def publish_service(
    service_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    user_id = cast(int, current_user.id)
    updated = await service.publish_service(service_id, user_id)
    return updated


@router.put("/services/{service_id}/unpublish", response_model=MarketplaceServiceResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def unpublish_service(
    service_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    user_id = cast(int, current_user.id)
    updated = await service.unpublish_service(service_id, user_id)
    return updated


# ========== 3. شراء الخدمة والنشر ==========
@router.post("/purchase", response_model=ServiceLicenseResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def purchase_service(
    data: ServiceLicensePurchase,
    background_tasks: BackgroundTasks,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    user_id = cast(int, current_user.id)
    license_obj = await service.purchase_service(user_id, cast(int, tenant.id), data.model_dump(), idempotency_key)
    return license_obj


@router.get("/licenses/me", response_model=List[ServiceLicenseResponse])
async def get_my_licenses(
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    licenses = await service.get_my_licenses(cast(int, tenant.id), skip, limit)
    return licenses


@router.get("/licenses/{license_id}/status")
async def get_deployment_status(
    license_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    user_id = cast(int, current_user.id)
    status = await service.get_deployment_status(license_id, user_id)
    return status


@router.post("/licenses/{license_id}/renew", response_model=ServiceLicenseResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def renew_license(
    license_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    user_id = cast(int, current_user.id)
    renewed = await service.renew_subscription(license_id, user_id)
    return renewed


# ========== 4. الإضافات (Add-ons) ==========
@router.get("/addons", response_model=List[ServiceAddonResponse])
async def list_addons(
    compatible_with: Optional[str] = None,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    addons = await service.list_addons(cast(int, tenant.id), compatible_with)
    return addons


@router.post("/addons", response_model=ServiceAddonResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_addon(
    data: ServiceAddonCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    user_id = cast(int, current_user.id)
    addon = await service.create_addon(user_id, cast(int, tenant.id), data.model_dump())
    return addon


@router.post("/licenses/{license_id}/addons/{addon_id}", response_model=ServiceLicenseResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def purchase_addon(
    license_id: int,
    addon_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    user_id = cast(int, current_user.id)
    updated_license = await service.purchase_addon(license_id, addon_id, user_id)
    return updated_license


# ========== 5. طلبات التخصيص ==========
@router.post("/licenses/{license_id}/customize", response_model=CustomizationRequestResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def request_customization(
    license_id: int,
    data: CustomizationRequestCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    user_id = cast(int, current_user.id)
    request_obj = await service.request_customization(license_id, user_id, data.model_dump(), idempotency_key)
    return request_obj


@router.get("/licenses/{license_id}/customizations", response_model=List[CustomizationRequestResponse])
async def get_customization_requests(
    license_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    requests = await service.get_customization_requests(license_id, cast(int, tenant.id))
    return requests


# ========== 6. تحديث حالة النشر (Webhook للنظام الداخلي) ==========
@router.post("/webhook/deployment/{license_id}")
async def deployment_webhook(
    license_id: int,
    data: DeploymentStatusUpdate,
    x_api_key: str = Header(..., description="Internal API Key for CI/CD"),
    db: AsyncSession = Depends(get_db)
):
    if x_api_key != "eppne_internal_secret":
        raise HTTPException(status_code=403, detail="Invalid API Key")

    service = ServiceMarketplaceService(db)
    await service.update_deployment_status(license_id, data.status, data.deployment_log)
    return {"message": "Deployment status updated"}