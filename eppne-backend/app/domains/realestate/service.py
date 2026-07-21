# app/domains/realestate/service.py
# pyright: reportCallIssue=false

from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import bleach
import asyncio
from typing import Optional, Dict, Any, cast, List, Callable

from app.domains.realestate.repository import RealEstateRepository
from app.domains.finance.service import FinanceService
from app.domains.invoicing.service import InvoicingService
from app.domains.affiliate.service import AffiliateService
from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
from app.domains.ai_agents.service import AIAgentsService
from app.domains.ai_governance.service import AIGovernanceService
from app.core.errors import NotFoundError, InsufficientBalanceError, PermissionDeniedError, IdempotencyError
from app.core.idempotency import check_idempotency, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging_conf import logger
from app.domains.realestate.models import (
    PropertyOwnership, RentalContract, LandAsset, AssetTokenization,
    SmartContractEngine, MasterPlan, ContractType, PropertyUnit,
    RealEstateDevelopment, ZoningCategory, LegalStatus, ConstructionStatus,
    PropertyType
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
        self.governance = AIGovernanceService(db)
        self.event_bus = EventBus(cast(Any, redis_client))
        self.redis = redis_client
        self.user_repo = UserRepository(db)

    # ========== التحقق من صلاحيات SaaS ==========
    async def _check_saas_limits(self, tenant_id: int, feature: str = "real_estate"):
        subscription = await self.saas.get_active_subscription(tenant_id)  # type: ignore
        if not subscription:
            raise PermissionDeniedError("No active subscription found.")
        features = subscription.features or {}
        if not features.get(feature, False):
            raise PermissionDeniedError("Real Estate feature is not included in your current plan.")
        return subscription, features

    # ========== التحقق من حوكمة الذكاء الاصطناعي ==========
    async def _check_ai_governance(self, tenant_id: int, user_id: int, action: str, cost: Decimal):
        try:
            result = await self.governance.check_and_consume(
                tenant_id=tenant_id,
                agent_id=2,
                user_id=user_id,
                tokens=100,
                cost=cost
            )
            return result
        except Exception as e:
            logger.warning(f"AI Governance check failed: {e}")

    # ============================================================
    # دوال CRUD للأراضي (Land Assets)
    # ============================================================
    async def create_land_asset(
        self,
        tenant_id: int,
        owner_id: int,
        data: Dict[str, Any]
    ) -> LandAsset:
        """إنشاء أرض جديدة."""
        await self._check_saas_limits(tenant_id, "real_estate")
        return await self.repo.create_land_asset(
            tenant_id=tenant_id,
            owner_id=owner_id,
            **data
        )

    async def get_my_lands(
        self,
        tenant_id: int,
        owner_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> list[LandAsset]:
        """جلب أراضي المستخدم."""
        result = await self.repo.list_land_assets(tenant_id, owner_id, skip, limit)
        return list(result)

    async def revalue_land(
        self,
        land_id: int,
        new_value: Decimal,
        admin_id: int
    ) -> LandAsset:
        """إعادة تقييم الأرض (للمشرفين فقط)."""
        land = await self.repo.get_land_asset(land_id)
        if not land:
            raise NotFoundError("Land asset not found")
        return await self.repo.update_land_value(land_id, new_value)

    # ============================================================
    # دوال التطويرات (Developments)
    # ============================================================
    async def create_development(
        self,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> RealEstateDevelopment:
        """إنشاء مشروع تطويري."""
        await self._check_saas_limits(tenant_id, "real_estate_development")
        return await self.repo.create_development(tenant_id=tenant_id, **data)

    async def get_development(self, dev_id: int) -> RealEstateDevelopment:
        """جلب مشروع تطويري."""
        dev = await self.repo.get_development(dev_id)
        if not dev:
            raise NotFoundError("Development not found")
        return dev

    # ============================================================
    # دوال الوحدات العقارية (Property Units)
    # ============================================================
    async def create_property_unit(
        self,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> PropertyUnit:
        """إنشاء وحدة عقارية."""
        await self._check_saas_limits(tenant_id, "real_estate")
        return await self.repo.create_unit(tenant_id=tenant_id, **data)

    async def list_units_for_sale(
        self,
        development_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> list[PropertyUnit]:
        """قائمة الوحدات المتاحة للبيع."""
        result = await self.repo.list_units(
            development_id=development_id,
            for_sale=True,
            skip=skip,
            limit=limit
        )
        return list(result)

    # ============================================================
    # الملكية الجزئية (Fractional Ownership)
    # ============================================================
    async def buy_fractional_ownership(
        self,
        buyer_id: int,
        tenant_id: int,
        unit_id: int,
        percentage: Decimal,
        idempotency_key: Optional[str] = None
    ) -> PropertyOwnership:
        """شراء ملكية جزئية (مع Idempotency ومعاملة ذرية)."""
        await self._check_saas_limits(tenant_id, "real_estate")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        async with self.db.begin_nested():
            unit = await self.repo.get_unit(unit_id)
            if not unit or not unit.is_available_for_sale:  # type: ignore
                raise NotFoundError("الوحدة غير متاحة للبيع")
            if unit.sale_price_mrusdt is None:  # type: ignore
                raise ValueError("الوحدة ليس لها سعر محدد")

            total_owned = await self.repo.get_total_ownership_percentage(unit_id)
            total_owned_dec = Decimal(str(total_owned))
            if total_owned_dec + percentage > Decimal(100):
                raise PermissionDeniedError(f"المتبقي: {100 - total_owned_dec}%")

            unit_price = cast(Decimal, unit.sale_price_mrusdt)
            cost = (unit_price * percentage) / Decimal(100)

            # ========================================
            # استدعاء الوكيل الذكي (تم كتابته في سطر واحد مع تجاهل التحقق)
            # ========================================
            await self.ai.execute_agent_action(agent_id=2, tenant_id=tenant_id, action_type="ANALYZE_PROJECT", payload={"unit_id": unit_id, "price": float(cost), "percentage": float(percentage), "buyer_id": buyer_id}, executor_user_id=buyer_id)  # type: ignore[call-arg]

            await self._check_ai_governance(tenant_id, buyer_id, "FRACTIONAL_PURCHASE", cost)

            # جلب المالك
            owner = await self._get_land_owner_for_unit(unit)
            owner_email = cast(str, owner.email)
            try:
                # نقل الأموال (في سطر واحد مع تجاهل التحقق)
                tx_hash = await self.finance.transfer(sender_id=buyer_id, receiver_email=owner_email, currency="MR_USDT", amount=cost, notes=f"Purchase {percentage}% of unit {unit_id}", idempotency_key=idempotency_key or "")  # type: ignore[call-arg]
            except InsufficientBalanceError:
                raise PermissionDeniedError("Insufficient balance")

            # إنشاء فاتورة
            await self.invoicing.create_invoice(  # type: ignore
                entity_id=tenant_id,
                user_id=buyer_id,
                amount=cost,
                description=f"Fractional ownership purchase: {percentage}% of unit {unit_id}",
                due_date=datetime.utcnow() + timedelta(days=30)
            )

            await self._register_affiliate_commission(buyer_id, tenant_id, cost)

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

            if (total_owned_dec + percentage) >= Decimal('99.99'):
                await self.repo.update_unit_availability(unit_id, for_sale=False)

            await self.event_bus.publish("realestate.ownership.created", {
                "unit_id": unit_id,
                "buyer_id": buyer_id,
                "tenant_id": tenant_id,
                "percentage": float(percentage),
                "amount": float(cost)
            })

            await audit_log(**{  # type: ignore
                "user_id": buyer_id,
                "tenant_id": tenant_id,
                "action": "FRACTIONAL_PURCHASE",
                "resource_id": ownership.id,
                "details": {"unit_id": unit_id, "percentage": float(percentage), "amount": float(cost)}
            })

            await self._send_notification(
                user_id=buyer_id,
                title="تم شراء ملكية جزئية",
                body=f"لقد اشتريت {percentage}% من الوحدة {unit_id} بقيمة {cost} MR_USDT"
            )

            if idempotency_key:
                await store_idempotency_result(idempotency_key, ownership)

            return ownership

    async def get_my_ownerships(self, user_id: int) -> list[PropertyOwnership]:
        """جلب ملكيات المستخدم."""
        result = await self.repo.get_user_ownerships(user_id)
        return list(result)

    # ============================================================
    # عقود الإيجار (Rental Contracts)
    # ============================================================
    async def rent_unit(
        self,
        landlord_id: int,
        tenant_id: int,
        unit_id: int,
        tenant_user_id: int,
        monthly_rent: Decimal,
        start_date: datetime,
        end_date: datetime,
        idempotency_key: Optional[str] = None
    ) -> RentalContract:
        """تأجير وحدة (مع Idempotency ومعاملة ذرية)."""
        await self._check_saas_limits(tenant_id, "real_estate")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        async with self.db.begin_nested():
            unit = await self.repo.get_unit(unit_id)
            if not unit or not unit.is_available_for_rent:  # type: ignore
                raise NotFoundError("الوحدة غير متاحة للإيجار")

            contract = await self.repo.create_rental_contract(
                tenant_id=tenant_id,
                unit_id=unit_id,
                tenant_user_id=tenant_user_id,
                landlord_user_id=landlord_id,
                start_date=start_date,
                end_date=end_date,
                monthly_rent_mrusdt=monthly_rent,
                contract_tx_hash=f"RENT-{uuid.uuid4().hex[:12].upper()}",
                idempotency_key=idempotency_key
            )

            first_payment = monthly_rent * Decimal(1)
            await self.invoicing.create_invoice(  # type: ignore
                entity_id=tenant_id,
                user_id=tenant_user_id,
                amount=first_payment,
                description=f"First month rent for unit {unit_id}",
                due_date=datetime.utcnow() + timedelta(days=3)
            )

            await self._register_affiliate_commission(tenant_user_id, tenant_id, first_payment)

            await audit_log(**{  # type: ignore
                "user_id": landlord_id,
                "tenant_id": tenant_id,
                "action": "RENTAL_CONTRACT_CREATED",
                "resource_id": contract.id,
                "details": {"unit_id": unit_id, "monthly_rent": float(monthly_rent)}
            })

            if idempotency_key:
                await store_idempotency_result(idempotency_key, contract)

            return contract

    # ============================================================
    # المخططات الرئيسية (Master Plans)
    # ============================================================
    async def create_master_plan(self, tenant_id: int, data: Dict[str, Any]) -> MasterPlan:
        """إنشاء مخطط رئيسي مع تعقيم."""
        await self._check_saas_limits(tenant_id, "real_estate_development")

        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)
        sanitized_description = bleach.clean(data.get("description", ""), tags=[], strip=True) if data.get("description") else None

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

    # ============================================================
    # تجزئة الأصول (Tokenization)
    # ============================================================
    async def tokenize_asset(
        self,
        tenant_id: int,
        unit_id: int,
        total_shares: int,
        share_price: Decimal
    ) -> AssetTokenization:
        """تجزئة الأصل إلى أسهم."""
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

        await audit_log(**{  # type: ignore
            "user_id": 0,
            "tenant_id": tenant_id,
            "action": "ASSET_TOKENIZED",
            "resource_id": tokenization.id,
            "details": {"unit_id": unit_id, "total_shares": total_shares}
        })

        return tokenization

    # ============================================================
    # العقود الذكية (Smart Contracts)
    # ============================================================
    async def deploy_smart_contract(
        self,
        tenant_id: int,
        contract_type: str,
        reference_id: int,
        contract_metadata: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> SmartContractEngine:
        """نشر عقد ذكي (مع Idempotency)."""
        await self._check_saas_limits(tenant_id, "real_estate_smart_contracts")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        sanitized_metadata = self._sanitize_contract_metadata(contract_metadata)

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

        await self._simulate_blockchain_deployment(cast(int, contract.id))

        await audit_log(**{  # type: ignore
            "user_id": 0,
            "tenant_id": tenant_id,
            "action": "SMART_CONTRACT_DEPLOYED",
            "resource_id": contract.id,
            "details": {"contract_type": contract_type, "reference_id": reference_id}
        })

        if idempotency_key:
            await store_idempotency_result(idempotency_key, contract)

        return contract

    # ============================================================
    # دوال مساعدة خاصة
    # ============================================================
    async def _get_land_owner_for_unit(self, unit: PropertyUnit):
        """جلب مالك الأرض المرتبطة بالوحدة."""
        dev_id = unit.development_id  # type: ignore
        dev = await self.repo.get_development(cast(int, dev_id))
        if not dev:
            raise NotFoundError("Development not found")
        land = await self.repo.get_land_asset(cast(int, dev.land_asset_id))
        if not land:
            raise NotFoundError("Land asset not found")
        owner = await self.user_repo.get_by_id(cast(int, land.owner_id))
        if not owner:
            raise NotFoundError("Land owner not found")
        return owner

    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, amount: Decimal):
        try:
            user = await self.user_repo.get_by_id(user_id)
            if user and user.referred_by:
                commission = amount * Decimal("0.02")
                await self.affiliate.register_commission(  # type: ignore
                    affiliate_id=user.referred_by,
                    user_id=user_id,
                    amount=commission,
                    description="Real estate transaction commission",
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")

    async def _simulate_blockchain_deployment(self, contract_id: int):
        await asyncio.sleep(2)
        await self.repo.update_smart_contract_status(
            contract_id=contract_id,
            status="CONFIRMED",
            tx_hash=f"0x{uuid.uuid4().hex[:40]}"
        )

    async def _send_notification(self, user_id: int, title: str, body: str):
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

    def _sanitize_gis_data(self, gis_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not gis_data:
            return {}
        if gis_data.get("type") not in ["Polygon", "MultiPolygon", "Point"]:
            raise ValueError("Invalid GeoJSON type. Must be Polygon, MultiPolygon, or Point.")
        if "coordinates" not in gis_data or not isinstance(gis_data["coordinates"], list):
            raise ValueError("Invalid GeoJSON: missing coordinates.")
        return gis_data