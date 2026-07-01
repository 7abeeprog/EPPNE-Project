"""
خدمات متجر الخدمات والتطبيقات الجاهزة (Service Marketplace)
يدعم: نشر الخدمات، شراء التراخيص، النشر الآلي (Deployment)، الإضافات، والتخصيص.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
import uuid

# استيرادات الكور
from app.domains.service_marketplace.repository import ServiceMarketplaceRepository
from app.domains.service_marketplace.models import (
    DeploymentStatus, SubscriptionPlan, MarketplaceService,
    ServiceLicense, ServiceAddon, CustomizationRequest
)
from app.domains.finance.service import FinanceService
from app.domains.sovereign_entities.service import SovereignEntitiesService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError

# 🔥 استيرادات جديدة
from app.core.idempotency import check_idempotency, store_idempotency_result
from app.core.audit import audit_log
from app.core.redis_client import redis_client
from app.core.event_bus import EventBus
from app.core.cache import cache_result, invalidate_cache
from app.domains.saas.service import SaaSSubscriptionService
from app.domains.affiliate.service import AffiliateService
from app.domains.invoicing.service import InvoicingService
from app.domains.ai_governance.service import AIGovernanceService
from app.tasks.deployment import deploy_service_task
from app.core.logging import logger


class ServiceMarketplaceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ServiceMarketplaceRepository(db)
        self.finance = FinanceService(db)
        self.entity_service = SovereignEntitiesService(db)
        self.redis = redis_client
        self.event_bus = EventBus(redis_client)

        # 🔥 الخدمات الجديدة
        self.saas_service = SaaSSubscriptionService(db)
        self.affiliate_service = AffiliateService(db)
        self.invoice_service = InvoicingService(db)
        self.governance_service = AIGovernanceService(db)

    # ============================================================
    # 0. التحقق من صلاحيات SaaS
    # ============================================================

    async def _check_saas_limits(self, tenant_id: int):
        """التحقق من صلاحية Service Marketplace في خطة الاشتراك."""
        subscription = await self.saas_service.get_active_subscription(tenant_id)
        if not subscription:
            raise PermissionDeniedError("No active subscription found for this entity.")
        features = subscription.features or {}
        if not features.get("service_marketplace", False):
            raise PermissionDeniedError("Service Marketplace feature is not included in your current plan.")
        return subscription, features

    # ============================================================
    # 1. إدارة الخدمات (للمطورين والإدارة)
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

    async def list_services(self, tenant_id: int, service_type: str = None, featured: bool = None) -> List[MarketplaceService]:
        return await self.repo.list_services(tenant_id, service_type, featured)

    # ============================================================
    # 2. شراء الخدمة (مع Idempotency، SaaS، Affiliate، Invoicing، AI Governance)
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
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # 2. التحقق من SaaS
        await self._check_saas_limits(buyer_tenant_id)

        # 3. جلب الخدمة
        service = await self.repo.get_service(data["service_id"])
        if not service or not service.is_active:
            raise NotFoundError("Service not available")

        # 4. التحقق من AI Governance (إذا كانت الخدمة تستخدم AI)
        if "ai" in service.service_type.value.lower() or (service.requires_modules and "ai" in service.requires_modules):
            allowed = await self.governance_service.check_and_consume(
                tenant_id=buyer_tenant_id,
                agent_id=None,  # لا يوجد وكيل محدد
                user_id=buyer_user_id,
                action_type="SERVICE_PURCHASE",
                tokens=0,
                cost=Decimal("0.01"),  # تكلفة رمزية للتحقق
                idempotency_key=idempotency_key
            )
            if not allowed:
                raise PermissionDeniedError("AI usage quota exceeded for your tenant.")

        # 5. حساب السعر
        plan = data.get("subscription_plan", SubscriptionPlan.BASIC)
        base_price = {
            SubscriptionPlan.BASIC: service.subscription_price_basic_mrusdt,
            SubscriptionPlan.PROFESSIONAL: service.subscription_price_pro_mrusdt,
            SubscriptionPlan.ENTERPRISE: service.subscription_price_enterprise_mrusdt,
        }.get(plan, 0)

        addons_price = Decimal(0)
        addon_ids = data.get("purchased_addons", [])
        for addon_id in addon_ids:
            addon = await self.repo.get_addon(addon_id, buyer_tenant_id)
            if addon:
                addons_price += addon.price_mrusdt

        total_price = base_price + addons_price

        # 6. تنفيذ التحويل المالي (مع Retry)
        tx_hash = None
        if total_price > 0:
            try:
                tx_hash = await self.finance.transfer_with_retry(
                    sender_id=buyer_user_id,
                    receiver_email=await self._get_owner_email(service.tenant_id),
                    currency="MR_USDT",
                    amount=total_price,
                    notes=f"Purchase of service: {service.name}",
                    idempotency_key=idempotency_key
                )
            except InsufficientBalanceError:
                raise PermissionDeniedError("Insufficient balance to purchase this service")

            # 7. إنشاء فاتورة (Invoicing)
            invoice = await self.invoice_service.create_invoice(
                tenant_id=buyer_tenant_id,
                user_id=buyer_user_id,
                amount=total_price,
                description=f"Service purchase: {service.name}",
                invoice_type="SERVICE_PURCHASE",
                reference_id=service.id
            )

            # 8. تسجيل عمولة إحالة (Affiliate)
            await self._register_affiliate_commission(
                user_id=buyer_user_id,
                amount=total_price,
                description=f"Service purchase: {service.name}"
            )

        # 9. إنشاء الترخيص
        license = await self.repo.create_license(
            tenant_id=buyer_tenant_id,
            service_id=service.id,
            buyer_user_id=buyer_user_id,
            subscription_plan=plan,
            purchased_addons=addon_ids,
            custom_config=data.get("custom_config", {}),
            deployed_domain=data.get("custom_domain"),  # تم تصحيح اللغم 1
            paid_amount_mrusdt=total_price,
            subscription_start=datetime.utcnow(),
            subscription_end=datetime.utcnow() + timedelta(days=365),
            auto_renew=data.get("auto_renew", True),
            deployment_status=DeploymentStatus.PENDING,
            idempotency_key=idempotency_key
        )

        # 10. تسجيل تدقيق (Audit Log)
        await audit_log(
            user_id=buyer_user_id,
            tenant_id=buyer_tenant_id,
            action="SERVICE_PURCHASE",
            resource_id=license.id,
            details={
                "service_id": service.id,
                "plan": plan,
                "total_price": float(total_price),
                "tx_hash": tx_hash
            }
        )

        # 11. إبطال الكاش
        await invalidate_cache(f"marketplace_services_{buyer_tenant_id}")
        await invalidate_cache(f"marketplace_licenses_{buyer_tenant_id}")

        # 12. تخزين نتيجة Idempotency
        if idempotency_key:
            await store_idempotency_result(idempotency_key, license)

        # 13. تشغيل النشر غير المتزامن (Celery)
        deploy_service_task.delay(license.id, buyer_tenant_id)

        # 14. نشر حدث
        await self.event_bus.publish("service.purchased", {
            "license_id": license.id,
            "tenant_id": buyer_tenant_id,
            "service_id": service.id,
            "user_id": buyer_user_id,
            "plan": plan,
            "total_price": float(total_price)
        })

        return license

    # ============================================================
    # 3. النشر الآلي (Deployment)
    # ============================================================

    async def _deploy_service(self, license_id: int) -> None:
        """النشر الآلي للخدمة (تُستدعى من Celery)."""
        license = await self.repo.get_license(license_id)
        if not license:
            return

        service = await self.repo.get_service(license.service_id)
        await self.repo.update_deployment_status(license_id, DeploymentStatus.DEPLOYING, "Starting deployment...")

        try:
            domain = license.deployed_domain or f"{service.service_type}-{license_id}.eppne.app"
            await self.repo.update_deployment_status(license_id, DeploymentStatus.DEPLOYING, f"Creating deployment at {domain}...")

            # محاكاة العمليات
            await self.repo.update_deployment_status(license_id, DeploymentStatus.DEPLOYING, "Database migration in progress...")
            await self.repo.update_deployment_status(license_id, DeploymentStatus.DEPLOYING, "Frontend build in progress...")

            # تم تصحيح اللغم 2: استخدام DeploymentStatus.ACTIVE
            await self.repo.update_license(
                license_id,
                deployed_domain=domain,
                deployment_status=DeploymentStatus.ACTIVE,
                deployment_log="Deployment completed successfully."
            )

            # نشر حدث نجاح النشر
            await self.event_bus.publish("service.deployed", {
                "license_id": license_id,
                "tenant_id": license.tenant_id,
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
        license = await self.repo.get_license(license_id)
        if not license or license.buyer_user_id != user_id:
            raise PermissionDeniedError("Not authorized")
        return {
            "status": license.deployment_status,
            "log": license.deployment_log,
            "domain": license.deployed_domain,
            "subscription_end": license.subscription_end
        }

    # ============================================================
    # 4. إدارة الإضافات
    # ============================================================

    async def create_addon(self, user_id: int, tenant_id: int, data: dict) -> ServiceAddon:
        return await self.repo.create_addon(tenant_id=tenant_id, created_by=user_id, version="1.0.0", **data)

    async def list_addons(self, tenant_id: int, compatible_with: str = None) -> List[ServiceAddon]:
        return await self.repo.list_addons(tenant_id, compatible_with)

    async def purchase_addon(self, license_id: int, addon_id: int, user_id: int) -> ServiceLicense:
        license = await self.repo.get_license(license_id)
        if not license or license.buyer_user_id != user_id:
            raise PermissionDeniedError("Not authorized")
        addon = await self.repo.get_addon(addon_id, license.tenant_id)
        if not addon:
            raise NotFoundError("Addon not found")

        if addon.price_mrusdt > 0:
            await self.finance.transfer(
                sender_id=user_id,
                receiver_email=await self._get_owner_email(license.tenant_id),
                currency="MR_USDT",
                amount=addon.price_mrusdt,
                notes=f"Addon purchase: {addon.name}"
            )

        purchased = license.purchased_addons or []
        purchased.append(addon_id)
        new_total = license.paid_amount_mrusdt + addon.price_mrusdt
        return await self.repo.update_license(license_id, purchased_addons=purchased, paid_amount_mrusdt=new_total)

    # ============================================================
    # 5. طلبات التخصيص
    # ============================================================

    async def request_customization(self, license_id: int, user_id: int, data: dict) -> CustomizationRequest:
        license = await self.repo.get_license(license_id)
        if not license or license.buyer_user_id != user_id:
            raise PermissionDeniedError("Not authorized")
        return await self.repo.create_customization_request(
            tenant_id=license.tenant_id,
            license_id=license_id,
            requester_id=user_id,
            **data
        )

    # ============================================================
    # 6. تجديد الاشتراك
    # ============================================================

    async def renew_subscription(self, license_id: int, user_id: int) -> ServiceLicense:
        license = await self.repo.get_license(license_id)
        if not license or license.buyer_user_id != user_id:
            raise PermissionDeniedError("Not authorized")
        service = await self.repo.get_service(license.service_id)

        plan = license.subscription_plan
        base_price = {
            SubscriptionPlan.BASIC: service.subscription_price_basic_mrusdt,
            SubscriptionPlan.PROFESSIONAL: service.subscription_price_pro_mrusdt,
            SubscriptionPlan.ENTERPRISE: service.subscription_price_enterprise_mrusdt,
        }.get(plan, 0)

        if base_price > 0:
            await self.finance.transfer(
                sender_id=user_id,
                receiver_email=await self._get_owner_email(service.tenant_id),
                currency="MR_USDT",
                amount=base_price,
                notes=f"Renewal of service: {service.name}"
            )

        new_end = (license.subscription_end or datetime.utcnow()) + timedelta(days=365)
        return await self.repo.update_license(license_id, subscription_end=new_end, is_active=True)

    # ============================================================
    # 7. تسجيل عمولة الإحالة
    # ============================================================

    async def _register_affiliate_commission(self, user_id: int, amount: Decimal, description: str):
        """تسجيل عمولة إحالة (10% من قيمة الشراء)."""
        user = await self._get_user(user_id)
        if user and user.referred_by:
            commission_amount = amount * Decimal("0.10")  # 10%
            if commission_amount > 0:
                await self.affiliate_service.register_commission(
                    affiliate_id=user.referred_by,
                    user_id=user_id,
                    amount=commission_amount,
                    description=description,
                    status="PENDING"
                )

    # ============================================================
    # 8. دوال مساعدة
    # ============================================================

    async def _get_user(self, user_id: int):
        """جلب المستخدم من قاعدة البيانات."""
        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)
        return await user_repo.get_user(user_id)

    async def _get_owner_email(self, tenant_id: int) -> str:
        """جلب بريد مالك المستأجر (تبسيط)."""
        # في الإنتاج، يتم جلب البريد الفعلي من جدول المستأجرين
        return f"owner_tenant_{tenant_id}@eppne.com"