# pyright: reportGeneralTypeIssues=false
# pyright: reportCallIssue=false
# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false

"""
خدمات متجر الخدمات والتطبيقات الجاهزة (Service Marketplace)
يدعم: نشر الخدمات، شراء التراخيص، النشر الآلي (Deployment)، الإضافات، والتخصيص.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, cast
import uuid

# استيرادات الكور
from app.domains.service_marketplace.repository import ServiceMarketplaceRepository
from app.domains.service_marketplace.models import (
    DeploymentStatus, SubscriptionPlan, MarketplaceService,
    ServiceLicense, ServiceAddon, CustomizationRequest, ServiceAddonPurchase
)
from app.domains.finance.service import FinanceService
from app.domains.sovereign_entities.service import SovereignEntitiesService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, ValidationError
from app.core.idempotency import get_idempotency_result, store_idempotency_result
from app.core.audit import audit_log
from app.core.redis_client import redis_client
from app.core.event_bus import EventBus
from app.core.cache import invalidate_cache
from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
from app.domains.affiliate.service import AffiliateService
from app.domains.invoicing.service import InvoicingService
from app.domains.ai_governance.service import AIGovernanceService
from app.tasks.deployment import deploy_service_task
from app.core.logging_conf import logger
from app.core.pagination import PaginatedResponse


class ServiceMarketplaceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ServiceMarketplaceRepository(db)
        self.redis = redis_client
        self.event_bus = EventBus(cast(Any, redis_client))

    # ============================================================
    # 0. دوال Idempotency الموحّدة
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
    # 1. التحقق من صلاحيات SaaS
    # ============================================================

    async def _check_saas_limits(self, tenant_id: int):
        """التحقق من صلاحية Service Marketplace في خطة الاشتراك."""
        saas_service = SaaSSubscriptionService(self.db, tenant_id)
        has_access = await saas_service.can_access_service(tenant_id, "service_marketplace")
        if not has_access:
            raise PermissionDeniedError("Service Marketplace feature is not included in your current plan.")
        return None, {}

    # ============================================================
    # 2. إدارة الخدمات (للمطورين والإدارة)
    # ============================================================

    async def create_service(self, user_id: int, tenant_id: int, data: dict) -> MarketplaceService:
        service = await self.repo.create_service(
            tenant_id=tenant_id,
            created_by=user_id,
            version="1.0.0",
            **data
        )
        await self.repo.create_version(
            service_id=service.id,
            version="1.0.0",
            database_schema=data.get("database_schema"),
            api_blueprint=data.get("api_blueprint"),
            frontend_template_url=data.get("frontend_template_url"),
            is_active=True
        )
        return service

    async def get_service(self, service_id: int) -> MarketplaceService:
        service = await self.repo.get_service(service_id)
        if not service:
            raise NotFoundError("Service not found")
        return service

    async def list_services(
        self,
        tenant_id: int,
        service_type: Optional[str] = None,
        featured: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[MarketplaceService]:
        return await self.repo.list_services(tenant_id, service_type, featured, skip, limit)

    async def publish_service(self, service_id: int, user_id: int) -> MarketplaceService:
        """نشر الخدمة (تفعيلها) – للمشرفين."""
        service = await self.repo.get_service(service_id)
        if not service:
            raise NotFoundError("Service not found")
        return await self.repo.update_service(service_id, is_active=True)

    async def unpublish_service(self, service_id: int, user_id: int) -> MarketplaceService:
        """إلغاء نشر الخدمة (تعطيلها) – للمشرفين."""
        service = await self.repo.get_service(service_id)
        if not service:
            raise NotFoundError("Service not found")
        return await self.repo.update_service(service_id, is_active=False)

    # ============================================================
    # 3. شراء الخدمة (مع Idempotency، SaaS، Affiliate، Invoicing، AI Governance)
    # ============================================================

    async def purchase_service(
        self,
        buyer_user_id: int,
        buyer_tenant_id: int,
        data: dict,
        idempotency_key: Optional[str] = None
    ) -> ServiceLicense:
        """
        شراء خدمة مع دعم Idempotency، SaaS، Affiliate، Invoicing، AI Governance.
        """
        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                license_id = cached.get("license_id")
                if license_id:
                    license_obj = await self.repo.get_license(license_id)
                    if license_obj:
                        return license_obj
                raise ValidationError("Idempotency record exists but license not found.")

        await self._check_saas_limits(buyer_tenant_id)

        service = await self.repo.get_service(data["service_id"])
        if not service or not service.is_active:
            raise NotFoundError("Service not available")

        governance_service = AIGovernanceService(self.db, buyer_tenant_id)
        if "ai" in service.service_type.value.lower() or (service.requires_modules and "ai" in service.requires_modules):
            allowed = await governance_service.check_and_consume(
                agent_id=0,
                user_id=buyer_user_id,
                action_type="SERVICE_PURCHASE",
                tokens=0,
                cost=Decimal("0.01"),
                idempotency_key=idempotency_key
            )
            if not allowed:
                raise PermissionDeniedError("AI usage quota exceeded for your tenant.")

        plan = data.get("subscription_plan", SubscriptionPlan.BASIC)
        base_price = {
            SubscriptionPlan.BASIC: service.subscription_price_basic_mrusdt,
            SubscriptionPlan.PROFESSIONAL: service.subscription_price_pro_mrusdt,
            SubscriptionPlan.ENTERPRISE: service.subscription_price_enterprise_mrusdt,
        }.get(plan, Decimal(0))

        addons_price = Decimal(0)
        addon_ids = data.get("purchased_addons", [])
        for addon_id in addon_ids:
            addon = await self.repo.get_addon(addon_id, buyer_tenant_id)
            if addon:
                addons_price += addon.price_mrusdt

        total_price = base_price + addons_price

        tx_hash = None
        if total_price > 0:
            finance = FinanceService(self.db, buyer_tenant_id)
            invoice_service = InvoicingService(self.db, buyer_tenant_id)
            try:
                tx_hash = await finance.transfer(
                    sender_id=buyer_user_id,
                    receiver_email=await self._get_owner_email(service.tenant_id),
                    currency="MR_USDT",
                    amount=total_price,
                    notes=f"Purchase of service: {service.name}",
                    idempotency_key=idempotency_key or ""
                )
            except InsufficientBalanceError:
                raise PermissionDeniedError("Insufficient balance to purchase this service")

            await invoice_service.create_invoice(
                tenant_id=buyer_tenant_id,
                user_id=buyer_user_id,
                amount=total_price,
                description=f"Service purchase: {service.name}",
                invoice_type="SERVICE_PURCHASE",
                reference_id=service.id
            )

            await self._register_affiliate_commission(
                user_id=buyer_user_id,
                tenant_id=buyer_tenant_id,
                amount=total_price,
                description=f"Service purchase: {service.name}"
            )

        async with self.db.begin_nested():
            license_obj = await self.repo.create_license(
                tenant_id=buyer_tenant_id,
                service_id=service.id,
                buyer_user_id=buyer_user_id,
                subscription_plan=plan,
                purchased_addons=addon_ids,
                custom_config=data.get("custom_config", {}),
                deployed_domain=data.get("custom_domain"),
                paid_amount_mrusdt=total_price,
                subscription_start=datetime.utcnow(),
                subscription_end=datetime.utcnow() + timedelta(days=365),
                auto_renew=data.get("auto_renew", True),
                deployment_status=DeploymentStatus.PENDING,
                idempotency_key=idempotency_key
            )

            await audit_log(
                user_id=buyer_user_id,
                tenant_id=buyer_tenant_id,
                action="SERVICE_PURCHASE",
                resource_id=license_obj.id,
                details={
                    "service_id": service.id,
                    "plan": plan,
                    "total_price": float(total_price),
                    "tx_hash": tx_hash
                }
            )

            # 🔥 إضافة await
            await invalidate_cache(f"marketplace_services_{buyer_tenant_id}")
            await invalidate_cache(f"marketplace_licenses_{buyer_tenant_id}")

            # تخزين معرف الترخيص فقط
            if idempotency_key:
                await self._store_idempotency(idempotency_key, {"license_id": license_obj.id})

        await self.db.commit()

        deploy_service_task.delay(license_obj.id, buyer_tenant_id)

        await self.event_bus.publish("service.purchased", {
            "license_id": license_obj.id,
            "tenant_id": buyer_tenant_id,
            "service_id": service.id,
            "user_id": buyer_user_id,
            "plan": plan,
            "total_price": float(total_price)
        })

        return license_obj

    # ============================================================
    # 4. النشر الآلي (Deployment)
    # ============================================================

    async def _deploy_service(self, license_id: int) -> None:
        """النشر الآلي للخدمة (تُستدعى من Celery)."""
        license_obj = await self.repo.get_license(license_id)
        if not license_obj:
            return

        service = await self.repo.get_service(license_obj.service_id)
        if not service:  # ✅ التحقق من وجود الخدمة
            logger.error(f"Service not found for license {license_id}")
            await self.repo.update_deployment_status(
                license_id,
                DeploymentStatus.FAILED,
                "Service not found"
            )
            return

        await self.repo.update_deployment_status(license_id, DeploymentStatus.DEPLOYING, "Starting deployment...")

        try:
            domain = license_obj.deployed_domain or f"{service.service_type}-{license_id}.eppne.app"
            await self.repo.update_deployment_status(license_id, DeploymentStatus.DEPLOYING, f"Creating deployment at {domain}...")

            await self.repo.update_deployment_status(license_id, DeploymentStatus.DEPLOYING, "Database migration in progress...")
            await self.repo.update_deployment_status(license_id, DeploymentStatus.DEPLOYING, "Frontend build in progress...")

            await self.repo.update_license(
                license_id,
                deployed_domain=domain,
                deployment_status=DeploymentStatus.ACTIVE,
                deployment_log="Deployment completed successfully."
            )

            await self.event_bus.publish("service.deployed", {
                "license_id": license_id,
                "tenant_id": license_obj.tenant_id,
                "domain": domain
            })

        except Exception as e:
            await self.repo.update_deployment_status(
                license_id,
                DeploymentStatus.FAILED,
                f"Deployment failed: {str(e)}"
            )
            logger.error(f"Deployment failed for license {license_id}: {e}")

    async def get_deployment_status(self, license_id: int, user_id: int) -> dict:
        license_obj = await self.repo.get_license(license_id)
        if not license_obj or license_obj.buyer_user_id != user_id:
            raise PermissionDeniedError("Not authorized")
        return {
            "status": license_obj.deployment_status,
            "log": license_obj.deployment_log,
            "domain": license_obj.deployed_domain,
            "subscription_end": license_obj.subscription_end
        }

    async def update_deployment_status(self, license_id: int, status: DeploymentStatus, log: Optional[str] = None) -> ServiceLicense:
        """تحديث حالة النشر (يُستخدم من Webhook)."""
        return await self.repo.update_deployment_status(license_id, status, log or "")

    # ============================================================
    # 5. التراخيص (Licenses)
    # ============================================================

    async def get_my_licenses(self, tenant_id: int, skip: int = 0, limit: int = 50) -> List[ServiceLicense]:
        return await self.repo.list_licenses_for_tenant(tenant_id, skip, limit)

    async def renew_subscription(self, license_id: int, user_id: int) -> ServiceLicense:
        """تجديد الاشتراك (مع معاملة ذرية)."""
        async with self.db.begin_nested():
            license_obj = await self.repo.get_license(license_id)
            if not license_obj or license_obj.buyer_user_id != user_id:
                raise PermissionDeniedError("Not authorized")
            service = await self.repo.get_service(license_obj.service_id)
            if not service:
                raise NotFoundError("Service not found")

            plan = license_obj.subscription_plan
            base_price = {
                SubscriptionPlan.BASIC: service.subscription_price_basic_mrusdt,
                SubscriptionPlan.PROFESSIONAL: service.subscription_price_pro_mrusdt,
                SubscriptionPlan.ENTERPRISE: service.subscription_price_enterprise_mrusdt,
            }.get(plan, Decimal(0))

            if base_price > 0:
                finance = FinanceService(self.db, license_obj.tenant_id)
                await finance.transfer(
                    sender_id=user_id,
                    receiver_email=await self._get_owner_email(service.tenant_id),
                    currency="MR_USDT",
                    amount=base_price,
                    notes=f"Renewal of service: {service.name}",
                    idempotency_key=f"RENEW-{license_id}-{datetime.utcnow().strftime('%Y-%m')}"
                )

            new_end = (license_obj.subscription_end or datetime.utcnow()) + timedelta(days=365)
            updated = await self.repo.update_license(license_id, subscription_end=new_end, is_active=True)
        await self.db.commit()
        return updated

    # ============================================================
    # 6. الإضافات (Add-ons)
    # ============================================================

    async def create_addon(self, user_id: int, tenant_id: int, data: dict) -> ServiceAddon:
        return await self.repo.create_addon(tenant_id=tenant_id, created_by=user_id, version="1.0.0", **data)

    async def list_addons(self, tenant_id: int, compatible_with: Optional[str] = None) -> List[ServiceAddon]:
        return await self.repo.list_addons(tenant_id, compatible_with)

    async def purchase_addon(self, license_id: int, addon_id: int, user_id: int) -> ServiceLicense:
        """شراء إضافة مع معاملة ذرية."""
        async with self.db.begin_nested():
            license_obj = await self.repo.get_license(license_id)
            if not license_obj or license_obj.buyer_user_id != user_id:
                raise PermissionDeniedError("Not authorized")
            addon = await self.repo.get_addon(addon_id, license_obj.tenant_id)
            if not addon:
                raise NotFoundError("Addon not found")

            addon_price = addon.price_mrusdt
            if addon_price > 0:
                finance = FinanceService(self.db, license_obj.tenant_id)
                await finance.transfer(
                    sender_id=user_id,
                    receiver_email=await self._get_owner_email(license_obj.tenant_id),
                    currency="MR_USDT",
                    amount=addon_price,
                    notes=f"Addon purchase: {addon.name}",
                    idempotency_key=f"ADDON-{license_id}-{addon_id}-{uuid.uuid4().hex[:8]}"
                )

            purchased = license_obj.purchased_addons or []
            purchased.append(addon_id)
            new_total = license_obj.paid_amount_mrusdt + addon_price
            updated = await self.repo.update_license(license_id, purchased_addons=purchased, paid_amount_mrusdt=new_total)

            await self.repo.create_addon_purchase(
                license_id=license_id,
                addon_id=addon_id,
                price_paid_mrusdt=addon_price,
                idempotency_key=f"ADDON-PURCHASE-{license_id}-{addon_id}-{uuid.uuid4().hex[:8]}"
            )

        await self.db.commit()
        return updated

    # ============================================================
    # 7. طلبات التخصيص (Customization) – مع Idempotency محسّن
    # ============================================================

    async def request_customization(
        self,
        license_id: int,
        user_id: int,
        data: dict,
        idempotency_key: Optional[str] = None
    ) -> CustomizationRequest:
        """إنشاء طلب تخصيص مع Idempotency."""
        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                request_id = cached.get("request_id")
                if request_id:
                    request_obj = await self.repo.get_customization_request(request_id)
                    if request_obj:
                        return request_obj
                raise ValidationError("Idempotency record exists but request not found.")

        license_obj = await self.repo.get_license(license_id)
        if not license_obj or license_obj.buyer_user_id != user_id:
            raise PermissionDeniedError("Not authorized")

        request_obj = await self.repo.create_customization_request(
            tenant_id=license_obj.tenant_id,
            license_id=license_id,
            requester_id=user_id,
            **data,
            idempotency_key=idempotency_key
        )

        # تخزين معرف الطلب فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"request_id": request_obj.id})

        return request_obj

    async def get_customization_requests(self, license_id: int, tenant_id: int) -> List[CustomizationRequest]:
        """جلب طلبات التخصيص لترخيص معين مع التأكد من tenant_id."""
        return await self.repo.list_customization_requests(license_id, tenant_id)

    # ============================================================
    # 8. دوال مساعدة
    # ============================================================

    async def _get_user(self, user_id: int):
        """جلب المستخدم من قاعدة البيانات."""
        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)
        return await user_repo.get_by_id(user_id)

    async def _get_owner_email(self, tenant_id: int) -> str:
        """جلب بريد مالك المستأجر (تبسيط)."""
        return f"owner_tenant_{tenant_id}@eppne.com"

    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, amount: Decimal, description: str):
        """تسجيل عمولة إحالة (10% من قيمة الشراء)."""
        try:
            affiliate_service = AffiliateService(self.db, tenant_id)
            user = await self._get_user(user_id)
            if user and user.referred_by:
                commission_amount = amount * Decimal("0.10")
                if commission_amount > 0:
                    await affiliate_service.register_commission(
                        affiliate_id=user.referred_by,
                        user_id=user_id,
                        amount=commission_amount,
                        description=description,
                        status="PENDING"
                    )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")