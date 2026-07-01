# app/domains/service_marketplace/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.domains.service_marketplace.models import (
    MarketplaceService, ServiceVersion, ServiceLicense, ServiceAddon, CustomizationRequest,
    ServiceAddonPurchase, DeploymentStatus
)
from app.core.errors import NotFoundError


class ServiceMarketplaceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # 1. Services (الخدمات)
    # ============================================================

    async def create_service(self, **kwargs) -> MarketplaceService:
        """إنشاء خدمة جديدة."""
        service = MarketplaceService(**kwargs)
        self.db.add(service)
        await self.db.commit()
        await self.db.refresh(service)
        return service

    async def get_service(self, service_id: int) -> Optional[MarketplaceService]:
        """جلب خدمة مع التأكد من عدم حذفها."""
        result = await self.db.execute(
            select(MarketplaceService).where(
                MarketplaceService.id == service_id,
                MarketplaceService.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def list_services(
        self,
        tenant_id: int,
        service_type: Optional[str] = None,
        is_featured: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[MarketplaceService]:
        """قائمة الخدمات مع فلترة حسب المستأجر والنوع."""
        query = select(MarketplaceService).where(
            MarketplaceService.tenant_id == tenant_id,
            MarketplaceService.is_active == True,
            MarketplaceService.is_deleted == False
        )
        if service_type:
            query = query.where(MarketplaceService.service_type == service_type)
        if is_featured is not None:
            query = query.where(MarketplaceService.is_featured == is_featured)
        query = query.order_by(MarketplaceService.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_service(self, service_id: int, **kwargs) -> MarketplaceService:
        """تحديث خدمة."""
        await self.db.execute(
            update(MarketplaceService)
            .where(MarketplaceService.id == service_id)
            .values(**kwargs)
        )
        await self.db.commit()
        return await self.get_service(service_id)

    async def delete_service(self, service_id: int, soft: bool = True) -> bool:
        """حذف خدمة (soft delete اختياري)."""
        if soft:
            await self.db.execute(
                update(MarketplaceService)
                .where(MarketplaceService.id == service_id)
                .values(is_deleted=True, deleted_at=func.now())
            )
        else:
            await self.db.execute(
                delete(MarketplaceService).where(MarketplaceService.id == service_id)
            )
        await self.db.commit()
        return True

    # ============================================================
    # 2. Service Versions (إصدارات الخدمة)
    # ============================================================

    async def create_version(self, **kwargs) -> ServiceVersion:
        """إنشاء إصدار جديد للخدمة."""
        version = ServiceVersion(**kwargs)
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        return version

    async def get_active_version(self, service_id: int) -> Optional[ServiceVersion]:
        """جلب الإصدار النشط للخدمة."""
        result = await self.db.execute(
            select(ServiceVersion)
            .where(ServiceVersion.service_id == service_id, ServiceVersion.is_active == True)
            .order_by(ServiceVersion.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def list_versions(self, service_id: int) -> List[ServiceVersion]:
        """قائمة جميع إصدارات الخدمة."""
        result = await self.db.execute(
            select(ServiceVersion)
            .where(ServiceVersion.service_id == service_id)
            .order_by(ServiceVersion.created_at.desc())
        )
        return result.scalars().all()

    # ============================================================
    # 3. Licenses (تراخيص الخدمة) – مع تحميل العلاقات لتجنب N+1
    # ============================================================

    async def create_license(self, **kwargs) -> ServiceLicense:
        """إنشاء ترخيص خدمة جديد (يتضمن idempotency_key)."""
        license = ServiceLicense(**kwargs)
        self.db.add(license)
        await self.db.commit()
        await self.db.refresh(license)
        return license

    async def get_license(self, license_id: int) -> Optional[ServiceLicense]:
        """جلب ترخيص معين."""
        result = await self.db.execute(
            select(ServiceLicense).where(ServiceLicense.id == license_id)
        )
        return result.scalar_one_or_none()

    async def get_license_by_tenant(self, tenant_id: int, service_id: int) -> Optional[ServiceLicense]:
        """جلب ترخيص لمستأجر معين."""
        result = await self.db.execute(
            select(ServiceLicense).where(
                ServiceLicense.tenant_id == tenant_id,
                ServiceLicense.service_id == service_id
            )
        )
        return result.scalar_one_or_none()

    async def get_license_by_idempotency(self, idempotency_key: str) -> Optional[ServiceLicense]:
        """جلب ترخيص باستخدام idempotency_key."""
        result = await self.db.execute(
            select(ServiceLicense).where(ServiceLicense.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def list_licenses_for_tenant(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[ServiceLicense]:
        """
        قائمة التراخيص للمستأجر مع تحميل العلاقات دفعة واحدة (لتجنب N+1).
        """
        result = await self.db.execute(
            select(ServiceLicense)
            .options(
                selectinload(ServiceLicense.service),
                selectinload(ServiceLicense.purchased_addons)
            )
            .where(ServiceLicense.tenant_id == tenant_id)
            .order_by(ServiceLicense.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def update_license(self, license_id: int, **kwargs) -> ServiceLicense:
        """تحديث ترخيص."""
        await self.db.execute(
            update(ServiceLicense)
            .where(ServiceLicense.id == license_id)
            .values(**kwargs)
        )
        await self.db.commit()
        return await self.get_license(license_id)

    async def update_deployment_status(
        self,
        license_id: int,
        status: DeploymentStatus,
        log: str = None
    ) -> ServiceLicense:
        """تحديث حالة النشر للترخيص."""
        values = {"deployment_status": status}
        if log:
            values["deployment_log"] = log
        await self.db.execute(
            update(ServiceLicense)
            .where(ServiceLicense.id == license_id)
            .values(**values)
        )
        await self.db.commit()
        return await self.get_license(license_id)

    # ============================================================
    # 4. Add-ons (الإضافات) – مع دعم tenant_id
    # ============================================================

    async def create_addon(self, **kwargs) -> ServiceAddon:
        """إنشاء إضافة جديدة (يتضمن tenant_id)."""
        addon = ServiceAddon(**kwargs)
        self.db.add(addon)
        await self.db.commit()
        await self.db.refresh(addon)
        return addon

    async def get_addon(self, addon_id: int, tenant_id: int) -> Optional[ServiceAddon]:
        """جلب إضافة مع التأكد من tenant_id."""
        result = await self.db.execute(
            select(ServiceAddon).where(
                ServiceAddon.id == addon_id,
                ServiceAddon.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def list_addons(
        self,
        tenant_id: int,
        compatible_with: Optional[str] = None
    ) -> List[ServiceAddon]:
        """قائمة الإضافات مع فلترة حسب التوافق."""
        query = select(ServiceAddon).where(
            ServiceAddon.tenant_id == tenant_id,
            ServiceAddon.is_active == True
        )
        if compatible_with:
            query = query.where(ServiceAddon.compatible_service_types.contains([compatible_with]))
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_addon(self, addon_id: int, tenant_id: int, **kwargs) -> Optional[ServiceAddon]:
        """تحديث إضافة مع التأكد من tenant_id."""
        addon = await self.get_addon(addon_id, tenant_id)
        if not addon:
            return None
        for key, value in kwargs.items():
            setattr(addon, key, value)
        await self.db.commit()
        await self.db.refresh(addon)
        return addon

    # ============================================================
    # 5. Customization Requests (طلبات التخصيص) – مع Idempotency
    # ============================================================

    async def create_customization_request(self, **kwargs) -> CustomizationRequest:
        """إنشاء طلب تخصيص جديد (يتضمن tenant_id و idempotency_key)."""
        req = CustomizationRequest(**kwargs)
        self.db.add(req)
        await self.db.commit()
        await self.db.refresh(req)
        return req

    async def get_customization_request_by_idempotency(
        self,
        idempotency_key: str
    ) -> Optional[CustomizationRequest]:
        """جلب طلب تخصيص باستخدام idempotency_key."""
        result = await self.db.execute(
            select(CustomizationRequest).where(CustomizationRequest.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def list_customization_requests(
        self,
        license_id: int,
        tenant_id: int
    ) -> List[CustomizationRequest]:
        """قائمة طلبات التخصيص للترخيص مع التأكد من tenant_id."""
        result = await self.db.execute(
            select(CustomizationRequest).where(
                CustomizationRequest.license_id == license_id,
                CustomizationRequest.tenant_id == tenant_id
            )
            .order_by(CustomizationRequest.created_at.desc())
        )
        return result.scalars().all()

    async def update_customization_request(
        self,
        request_id: int,
        tenant_id: int,
        **kwargs
    ) -> Optional[CustomizationRequest]:
        """تحديث طلب تخصيص مع التأكد من tenant_id."""
        result = await self.db.execute(
            select(CustomizationRequest).where(
                CustomizationRequest.id == request_id,
                CustomizationRequest.tenant_id == tenant_id
            )
        )
        req = result.scalar_one_or_none()
        if not req:
            return None
        for key, value in kwargs.items():
            setattr(req, key, value)
        await self.db.commit()
        await self.db.refresh(req)
        return req

    # ============================================================
    # 🆕 6. Add-on Purchases (شراء الإضافات) مع Idempotency
    # ============================================================

    async def create_addon_purchase(self, **kwargs) -> ServiceAddonPurchase:
        """إنشاء سجل شراء إضافة (يتضمن idempotency_key)."""
        purchase = ServiceAddonPurchase(**kwargs)
        self.db.add(purchase)
        await self.db.commit()
        await self.db.refresh(purchase)
        return purchase

    async def get_addon_purchase_by_idempotency(
        self,
        idempotency_key: str
    ) -> Optional[ServiceAddonPurchase]:
        """جلب سجل شراء إضافة باستخدام idempotency_key."""
        result = await self.db.execute(
            select(ServiceAddonPurchase).where(ServiceAddonPurchase.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def list_addon_purchases(
        self,
        license_id: int,
        tenant_id: int
    ) -> List[ServiceAddonPurchase]:
        """قائمة الإضافات المشتراة لترخيص معين مع التأكد من tenant_id."""
        # ربط مع ServiceLicense للتحقق من tenant_id
        result = await self.db.execute(
            select(ServiceAddonPurchase)
            .join(ServiceLicense, ServiceAddonPurchase.license_id == ServiceLicense.id)
            .where(
                ServiceAddonPurchase.license_id == license_id,
                ServiceLicense.tenant_id == tenant_id
            )
            .order_by(ServiceAddonPurchase.purchased_at.desc())
        )
        return result.scalars().all()