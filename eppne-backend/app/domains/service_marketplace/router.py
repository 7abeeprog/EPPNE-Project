"""
مسارات (Endpoints) متجر الخدمات والتطبيقات الجاهزة
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Any

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser
from app.domains.identity.models import User
from app.domains.service_marketplace.service import ServiceMarketplaceService
from app.domains.service_marketplace.repository import ServiceMarketplaceRepository
from app.domains.service_marketplace.schemas import *

router = APIRouter(prefix="/marketplace", tags=["Service Marketplace - One-Click Apps"])


# ========== 1. استعراض الخدمات (عام) ==========
@router.get("/services", response_model=List[MarketplaceServiceResponse])
async def list_services(
    service_type: Optional[str] = None,
    featured: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: Any = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = ServiceMarketplaceRepository(db)
    services = await repo.list_services(tenant.id, service_type, featured, skip, limit)
    return services


@router.get("/services/{service_id}", response_model=MarketplaceServiceResponse)
async def get_service(service_id: int, db: AsyncSession = Depends(get_db)):
    service = await ServiceMarketplaceService(db).get_service(service_id)
    return service


# ========== 2. إدارة الخدمات (للمطورين / الإدارة) ==========
@router.post("/services", response_model=MarketplaceServiceResponse, status_code=201)
async def create_service(
    data: MarketplaceServiceCreate,
    tenant: Any = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    new_service = await service.create_service(current_user.id, tenant.id, data.model_dump())
    return new_service


@router.put("/services/{service_id}/publish")
async def publish_service(
    service_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    repo = ServiceMarketplaceRepository(db)
    await repo.update_service(service_id, is_active=True)
    return {"message": "Service published"}


@router.put("/services/{service_id}/unpublish")
async def unpublish_service(
    service_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    repo = ServiceMarketplaceRepository(db)
    await repo.update_service(service_id, is_active=False)
    return {"message": "Service unpublished"}


# ========== 3. شراء الخدمة والنشر ==========
@router.post("/purchase", response_model=ServiceLicenseResponse)
async def purchase_service(
    data: ServiceLicensePurchase,
    background_tasks: BackgroundTasks,
    tenant: Any = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    license = await service.purchase_service(current_user.id, tenant.id, data.model_dump())
    return license


@router.get("/licenses/me", response_model=List[ServiceLicenseResponse])
async def get_my_licenses(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = ServiceMarketplaceRepository(db)
    tenant = await get_current_tenant(db)  # جلب المستأجر الحالي ديناميكياً
    licenses = await repo.list_licenses_for_tenant(tenant.id, skip, limit)
    return licenses


@router.get("/licenses/{license_id}/status")
async def get_deployment_status(
    license_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    status = await service.get_deployment_status(license_id, current_user.id)
    return status


@router.post("/licenses/{license_id}/renew", response_model=ServiceLicenseResponse)
async def renew_license(
    license_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    renewed = await service.renew_subscription(license_id, current_user.id)
    return renewed


# ========== 4. الإضافات (Add-ons) ==========
@router.get("/addons", response_model=List[ServiceAddonResponse])
async def list_addons(
    compatible_with: Optional[str] = None,
    tenant: Any = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    addons = await service.list_addons(tenant.id, compatible_with)
    return addons


@router.post("/addons", response_model=ServiceAddonResponse, status_code=201)
async def create_addon(
    data: ServiceAddonCreate,
    tenant: Any = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    addon = await service.create_addon(current_user.id, tenant.id, data.model_dump())
    return addon


@router.post("/licenses/{license_id}/addons/{addon_id}", response_model=ServiceLicenseResponse)
async def purchase_addon(
    license_id: int,
    addon_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    updated_license = await service.purchase_addon(license_id, addon_id, current_user.id)
    return updated_license


# ========== 5. طلبات التخصيص ==========
@router.post("/licenses/{license_id}/customize", response_model=CustomizationRequestResponse)
async def request_customization(
    license_id: int,
    data: CustomizationRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ServiceMarketplaceService(db)
    request_obj = await service.request_customization(license_id, current_user.id, data.model_dump())
    return request_obj


@router.get("/licenses/{license_id}/customizations", response_model=List[CustomizationRequestResponse])
async def get_customization_requests(
    license_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = ServiceMarketplaceRepository(db)
    requests = await repo.list_customization_requests(license_id)
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
        
    repo = ServiceMarketplaceRepository(db)
    await repo.update_deployment_status(license_id, data.status, data.deployment_log)
    return {"message": "Deployment status updated"}