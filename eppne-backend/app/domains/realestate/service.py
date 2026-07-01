# app/domains/realestate/service.py (الإصدار النهائي المتكامل مع جميع الإضافات)
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import bleach
import asyncio

from app.domains.realestate.repository import RealEstateRepository
from app.domains.finance.service import FinanceService
from app.domains.invoicing.service import InvoicingService
from app.domains.affiliate.service import AffiliateService
from app.domains.saas.service import SaaSSubscriptionService
from app.domains.ai_agents.service import AIAgentsService
from app.domains.ai_governance.service import AIGovernanceService  # 🔥 جديد
from app.core.errors import NotFoundError, InsufficientBalanceError, PermissionDeniedError, IdempotencyError
from app.core.idempotency import check_idempotency, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging import logger
from app.domains.realestate.models import (
    PropertyOwnership, RentalContract, LandAsset, AssetTokenization,
    SmartContractEngine, MasterPlan, ContractType
)
from app.domains.identity.repository import UserRepository


class RealEstateService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RealEstateRepository(db)
        self.finance = FinanceService(db)
        self.invoicing = InvoicingService(db)
        self.affiliate = AffiliateService(db)
        self.saas = SaaSSubscriptionService(db)
        self.ai = AIAgentsService(db)
        self.governance = AIGovernanceService(db)  # 🔥 جديد
        self.event_bus = EventBus(redis_client)
        self.redis = redis_client

    # ========== التحقق من صلاحيات SaaS ==========
    async def _check_saas_limits(self, tenant_id: int, feature: str = "real_estate"):
        subscription = await self.saas.get_active_subscription(tenant_id)
        if not subscription:
            raise PermissionDeniedError("No active subscription found.")
        features = subscription.features or {}
        if not features.get(feature, False):
            raise PermissionDeniedError("Real Estate feature is not included in your current plan.")
        return subscription, features

    # ========== التحقق من حوكمة الذكاء الاصطناعي ==========
    async def _check_ai_governance(self, tenant_id: int, user_id: int, action: str, cost: Decimal):
        """التحقق من صلاحية المستخدم عبر نظام حوكمة الذكاء الاصطناعي."""
        try:
            result = await self.governance.check_and_consume(
                tenant_id=tenant_id,
                agent_id=2,  # وكيل REAL_ESTATE_ANALYST
                user_id=user_id,
                tokens=100,
                cost=cost
            )
            return result
        except Exception as e:
            logger.warning(f"AI Governance check failed: {e}")
            # لا نمنع العملية، فقط نسجل التحذير

    # ========== شراء ملكية جزئية (مع Idempotency, Audit, Invoicing, Affiliate, AI, Governance, Notifications) ==========
    async def buy_fractional_ownership(
        self,
        buyer_id: int,
        tenant_id: int,
        unit_id: int,
        percentage: Decimal,
        idempotency_key: str = None
    ) -> PropertyOwnership:
        # 1. التحقق من SaaS
        await self._check_saas_limits(tenant_id, "real_estate")

        # 2. التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # 3. جلب الوحدة والتحقق من صلاحيتها
        unit = await self.repo.get_unit(unit_id)
        if not unit or not unit.is_available_for_sale:
            raise NotFoundError("الوحدة غير متاحة للبيع")
        if unit.sale_price_mrusdt is None:
            raise ValueError("الوحدة ليس لها سعر محدد")

        # 4. التحقق من النسبة المتبقية
        total_owned = await self.repo.get_total_ownership_percentage(unit_id)
        if total_owned + percentage > 100:
            raise PermissionDeniedError(f"المتبقي: {100 - total_owned}%")

        # 5. حساب التكلفة
        cost = (unit.sale_price_mrusdt * percentage) / Decimal(100)

        # 6. استدعاء الذكاء الاصطناعي لتقييم الصفقة
        try:
            ai_evaluation = await self.ai.execute_agent_action(
                agent_id=2,
                tenant_id=tenant_id,
                action_type="ANALYZE_PROJECT",
                payload={
                    "unit_id": unit_id,
                    "price": float(cost),
                    "percentage": float(percentage),
                    "buyer_id": buyer_id
                },
                executor_user_id=buyer_id
            )
            logger.info(f"AI Real Estate evaluation: {ai_evaluation}")
        except Exception as e:
            logger.warning(f"AI evaluation failed, proceeding without: {e}")

        # 🔥 6.1 التحقق من حوكمة الذكاء الاصطناعي
        await self._check_ai_governance(tenant_id, buyer_id, "FRACTIONAL_PURCHASE", cost)

        # 7. جلب المالك وتحويل الأموال
        owner = await self._get_land_owner_for_unit(unit)
        try:
            tx_hash = await self.finance.transfer(
                sender_id=buyer_id,
                receiver_email=owner.email,
                currency="MR_USDT",
                amount=cost,
                notes=f"Purchase {percentage}% of unit {unit_id}",
                idempotency_key=idempotency_key
            )
        except InsufficientBalanceError:
            raise PermissionDeniedError("Insufficient balance")

        # 8. إنشاء فاتورة (Invoicing)
        invoice = await self.invoicing.create_invoice(
            entity_id=tenant_id,
            user_id=buyer_id,
            amount=cost,
            description=f"Fractional ownership purchase: {percentage}% of unit {unit_id}",
            due_date=datetime.utcnow() + timedelta(days=30)
        )

        # 9. تسجيل الإحالة (Affiliate)
        await self._register_affiliate_commission(buyer_id, tenant_id, cost)

        # 10. إنشاء سجل الملكية
        deed_nft = f"EPPNE-DEED-{unit_id}-{buyer_id}-{uuid.uuid4().hex[:8].upper()}"
        ownership = await self.repo.create_ownership(
            tenant_id=tenant_id,
            unit_id=unit_id,
            owner_user_id=buyer_id,
            ownership_percentage=percentage,
            acquisition_date=datetime.utcnow(),
            deed_nft_token_id=deed_nft,
            purchase_tx_hash=tx_hash,
            idempotency_key=idempotency_key
        )

        # 11. تحديث توفر الوحدة
        if (total_owned + percentage) >= Decimal('99.99'):
            await self.repo.update_unit_availability(unit_id, for_sale=False)

        # 12. نشر حدث للأتمتة
        await self.event_bus.publish("realestate.ownership.created", {
            "unit_id": unit_id,
            "buyer_id": buyer_id,
            "tenant_id": tenant_id,
            "percentage": float(percentage),
            "amount": float(cost)
        })

        # 13. تسجيل التدقيق (Audit)
        await audit_log(
            user_id=buyer_id,
            tenant_id=tenant_id,
            action="FRACTIONAL_PURCHASE",
            resource_id=ownership.id,
            details={"unit_id": unit_id, "percentage": float(percentage), "amount": float(cost)}
        )

        # 14. إرسال إشعار للمستخدم (Communications)
        await self._send_notification(
            user_id=buyer_id,
            title="تم شراء ملكية جزئية",
            body=f"لقد اشتريت {percentage}% من الوحدة {unit_id} بقيمة {cost} MR_USDT"
        )

        # 15. تخزين نتيجة Idempotency
        if idempotency_key:
            await store_idempotency_result(idempotency_key, ownership)

        return ownership

    # ========== تأجير وحدة (مع Idempotency, Audit, Invoicing, Affiliate) ==========
    async def rent_unit(
        self,
        landlord_id: int,
        tenant_id: int,
        unit_id: int,
        monthly_rent: Decimal,
        start_date: datetime,
        end_date: datetime,
        idempotency_key: str = None
    ) -> RentalContract:
        await self._check_saas_limits(tenant_id, "real_estate")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        unit = await self.repo.get_unit(unit_id)
        if not unit or not unit.is_available_for_rent:
            raise NotFoundError("الوحدة غير متاحة للإيجار")

        contract = await self.repo.create_rental_contract(
            tenant_id=tenant_id,
            unit_id=unit_id,
            tenant_user_id=tenant_id,
            landlord_user_id=landlord_id,
            start_date=start_date,
            end_date=end_date,
            monthly_rent_mrusdt=monthly_rent,
            contract_tx_hash=f"RENT-{uuid.uuid4().hex[:12].upper()}",
            idempotency_key=idempotency_key
        )

        first_payment = monthly_rent * Decimal(1)
        await self.invoicing.create_invoice(
            entity_id=tenant_id,
            user_id=tenant_id,
            amount=first_payment,
            description=f"First month rent for unit {unit_id}",
            due_date=datetime.utcnow() + timedelta(days=3)
        )

        await self._register_affiliate_commission(tenant_id, tenant_id, first_payment)

        await audit_log(
            user_id=landlord_id,
            tenant_id=tenant_id,
            action="RENTAL_CONTRACT_CREATED",
            resource_id=contract.id,
            details={"unit_id": unit_id, "monthly_rent": float(monthly_rent)}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, contract)

        return contract

    # ========== إنشاء مخطط رئيسي (Master Plan) ==========
    async def create_master_plan(self, tenant_id: int, data: dict) -> MasterPlan:
        await self._check_saas_limits(tenant_id, "real_estate_development")
        
        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)
        sanitized_description = bleach.clean(data.get("description", ""), tags=[], strip=True) if data.get("description") else None

        # تعقيم بيانات GIS
        gis_data = self._sanitize_gis_data(data.get("gis_data"))

        return await self.repo.create_master_plan(
            tenant_id=tenant_id,
            land_asset_id=data["land_asset_id"],
            name=sanitized_name,
            description=sanitized_description,
            gis_data=gis_data,
            bim_model_hash=data.get("bim_model_hash"),
            total_units_planned=data.get("total_units_planned", 0),
            total_area_sqm=data["total_area_sqm"]
        )

    # ========== تجزئة الأصول (Tokenization) ==========
    async def tokenize_asset(self, tenant_id: int, unit_id: int, total_shares: int, share_price: Decimal) -> AssetTokenization:
        await self._check_saas_limits(tenant_id, "real_estate_tokenization")

        existing = await self.repo.get_tokenization_by_unit(unit_id, tenant_id)
        if existing:
            raise PermissionDeniedError("Asset already tokenized")

        tokenization = await self.repo.create_tokenization(
            tenant_id=tenant_id,
            unit_id=unit_id,
            total_shares=total_shares,
            share_price_mrusdt=share_price,
            minimum_investment_shares=1,
            token_symbol=f"EPPNE-RE-{unit_id}-{uuid.uuid4().hex[:4].upper()}"
        )

        await audit_log(
            user_id=0,
            tenant_id=tenant_id,
            action="ASSET_TOKENIZED",
            resource_id=tokenization.id,
            details={"unit_id": unit_id, "total_shares": total_shares}
        )

        return tokenization

    # ========== نشر عقد ذكي (مع Idempotency, محاكاة البلوكشين) ==========
    async def deploy_smart_contract(
        self,
        tenant_id: int,
        contract_type: str,
        reference_id: int,
        contract_metadata: dict,
        idempotency_key: str = None
    ) -> SmartContractEngine:
        # 1. التحقق من SaaS
        await self._check_saas_limits(tenant_id, "real_estate_smart_contracts")

        # 2. التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # 3. تعقيم المدخلات
        sanitized_metadata = self._sanitize_contract_metadata(contract_metadata)

        # 4. إنشاء العقد الذكي
        contract = await self.repo.create_smart_contract(
            tenant_id=tenant_id,
            contract_type=contract_type,
            reference_id=reference_id,
            contract_metadata=sanitized_metadata,
            blockchain_tx_hash=f"TX-RE-{uuid.uuid4().hex[:16].upper()}",
            execution_status="PENDING",
            executed_at=None,
            idempotency_key=idempotency_key
        )

        # 5. محاكاة النشر على البلوكشين
        await self._simulate_blockchain_deployment(contract.id)

        # 6. تسجيل التدقيق
        await audit_log(
            user_id=0,
            tenant_id=tenant_id,
            action="SMART_CONTRACT_DEPLOYED",
            resource_id=contract.id,
            details={"contract_type": contract_type, "reference_id": reference_id}
        )

        # 7. تخزين نتيجة Idempotency
        if idempotency_key:
            await store_idempotency_result(idempotency_key, contract)

        return contract

    # ========== دوال مساعدة ==========
    async def _get_land_owner_for_unit(self, unit):
        from app.domains.identity.repository import UserRepository
        
        if not unit.development_id:
            raise ValueError("الوحدة غير مرتبطة بمشروع تطوير.")
        
        dev = await self.repo.get_development(unit.development_id)
        land = await self.repo.get_land_asset(dev.land_asset_id)
        
        user_repo = UserRepository(self.db)
        owner = await user_repo.get_by_id(land.owner_id)
        if not owner:
            raise NotFoundError("مالك الأرض الأصلي غير موجود.")
        return owner

    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, amount: Decimal):
        try:
            user_repo = UserRepository(self.db)
            user = await user_repo.get_by_id(user_id)
            if user and user.referred_by:
                commission = amount * Decimal("0.02")
                await self.affiliate.register_commission(
                    affiliate_id=user.referred_by,
                    user_id=user_id,
                    amount=commission,
                    description="Real estate transaction commission",
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")

    async def _simulate_blockchain_deployment(self, contract_id: int):
        """محاكاة نشر العقد الذكي على البلوكشين."""
        await asyncio.sleep(2)  # محاكاة زمن المعالجة
        await self.repo.update_smart_contract_status(
            contract_id=contract_id,
            status="CONFIRMED",
            tx_hash=f"0x{uuid.uuid4().hex[:40]}"
        )

    async def _send_notification(self, user_id: int, title: str, body: str):
        """إرسال إشعار للمستخدم عبر قطاع الاتصالات."""
        try:
            from app.domains.communications.service import CommunicationsService
            comm_service = CommunicationsService(self.db)
            await comm_service.send_notification(
                user_id=user_id,
                title=title,
                body=body,
                channel="IN_APP"
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    def _sanitize_contract_metadata(self, metadata: dict) -> dict:
        """تعقيم بيانات العقد الذكي لمنع الهجمات."""
        if not isinstance(metadata, dict):
            return {}
        
        sanitized = {}
        for key, value in metadata.items():
            if isinstance(value, str):
                sanitized[key] = bleach.clean(value, tags=[], strip=True)
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_contract_metadata(value)
            else:
                sanitized[key] = value
        return sanitized

    def _sanitize_gis_data(self, gis_data: dict) -> dict:
        """تعقيم بيانات GIS للتحقق من الصيغة الصحيحة."""
        if not gis_data:
            return {}
        
        if gis_data.get("type") not in ["Polygon", "MultiPolygon", "Point"]:
            raise ValueError("Invalid GeoJSON type. Must be Polygon, MultiPolygon, or Point.")
        
        if "coordinates" not in gis_data or not isinstance(gis_data["coordinates"], list):
            raise ValueError("Invalid GeoJSON: missing coordinates.")
        
        return gis_data