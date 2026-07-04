# app/domains/manufacturing/service.py (الإصدار النهائي مع جميع الإضافات)
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import datetime, timedelta
import uuid
import bleach
from typing import Optional, Dict, Any, List

from app.domains.manufacturing.repository import ManufacturingRepository
from app.domains.finance.service import FinanceService
from app.domains.ai_agents.service import AIAgentsService
from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
from app.domains.affiliate.service import AffiliateService
from app.domains.invoicing.service import InvoicingService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, IdempotencyError
from app.core.idempotency import check_idempotency, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging_conf import logger
from app.domains.ai_governance.service import AIGovernanceService  # 🔥 جديد
from app.domains.manufacturing.models import (
    ManufacturingFacility, ProductionLine, ProductBlueprint, ProductionBatch,
    SmartProductItem, RawMaterialBatch, MaterialConsumptionLog,
    ProductDigitalTwin, QualityCertificate, PredictiveMaintenanceLog, SparePart,
    ProductionStatus, TrackingStatus
)

class ManufacturingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ManufacturingRepository(db)
        self.finance = FinanceService(db)
        self.ai_service = AIAgentsService(db)
        self.saas_service = SaaSSubscriptionService(db)
        self.affiliate_service = AffiliateService(db)
        self.invoicing_service = InvoicingService(db)
        self.event_bus = EventBus(redis_client)
        self.redis = redis_client

    # ========== التحقق من صلاحيات SaaS ==========
    async def _check_saas_limits(self, tenant_id: int, feature: str = "manufacturing"):
        subscription = await self.saas_service.get_active_subscription(tenant_id)
        if not subscription:
            raise PermissionDeniedError("No active subscription found.")
        features = subscription.features or {}
        if not features.get(feature, False):
            raise PermissionDeniedError("Manufacturing feature is not included in your current plan.")
        return subscription, features

    # ========== إنشاء منشأة (مع SaaS + Affiliate + Audit) ==========
    async def create_facility(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> ManufacturingFacility:
        await self._check_saas_limits(tenant_id, "manufacturing")

        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)

        facility = await self.repo.create_facility(
            tenant_id=tenant_id,
            manager_id=user_id,
            name=sanitized_name,
            facility_type=data["facility_type"],
            location_gps=data.get("location_gps"),
            real_estate_unit_id=data.get("real_estate_unit_id")
        )

        await self._register_affiliate_commission(user_id, tenant_id, "FACILITY_CREATED")

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="FACILITY_CREATED",
            resource_id=facility.id,
            details={"name": facility.name, "type": facility.facility_type.value}
        )

        await self.event_bus.publish("manufacturing.facility.created", {
            "facility_id": facility.id,
            "tenant_id": tenant_id,
            "manager_id": user_id,
            "name": facility.name
        })

        return facility

    # ========== بدء الإنتاج (مع Idempotency + AI + AI Governance + Invoicing + Audit + Event) ==========
    async def start_production(
        self,
        user_id: int,
        tenant_id: int,
        batch_id: int,
        idempotency_key: str = None
    ) -> Dict[str, Any]:
        # 1. التحقق من SaaS
        await self._check_saas_limits(tenant_id, "manufacturing")

        # 2. التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # 3. جلب الدفعة مع التحقق من العزل
        batch = await self.repo.get_batch(batch_id, tenant_id)
        if not batch:
            raise NotFoundError("Batch not found")
        if batch.status != ProductionStatus.PLANNED:
            raise ValueError("Batch already started or completed")

        # 4. جلب النموذج (Blueprint)
        blueprint = await self.repo.get_blueprint(batch.product_blueprint_id)

        # 🔥 5. التحقق من حوكمة الذكاء الاصطناعي (AI Governance)
        governance = AIGovernanceService(self.db)
        await governance.check_and_consume(
            tenant_id=tenant_id,
            agent_id=4,  # MANUFACTURING_AI
            user_id=user_id,
            tokens=150,
            cost=Decimal("0.015")
        )

        # 6. استدعاء وكيل الذكاء الاصطناعي (MANUFACTURING_AI)
        try:
            ai_result = await self.ai_service.execute_agent_action(
                agent_id=4,
                tenant_id=tenant_id,
                action_type="ANALYZE_SENSOR",
                payload={
                    "batch_id": batch.id,
                    "target_quantity": batch.target_quantity,
                    "blueprint": blueprint.sku,
                    "line_id": batch.line_id
                },
                executor_user_id=user_id
            )
            logger.info(f"AI Manufacturing optimization: {ai_result}")
        except Exception as e:
            logger.warning(f"AI analysis failed, proceeding without: {e}")

        # 7. إنشاء فاتورة (Invoicing) لتكاليف الإنتاج
        estimated_cost = Decimal(batch.target_quantity) * Decimal("0.50")
        await self.invoicing_service.create_invoice(
            entity_id=tenant_id,
            user_id=user_id,
            amount=estimated_cost,
            description=f"Production cost for batch {batch.batch_number}",
            due_date=datetime.utcnow() + timedelta(days=30)
        )

        # 8. توليد المنتجات
        items = []
        for i in range(batch.target_quantity):
            serial = f"{blueprint.sku}-{batch.batch_number}-{uuid.uuid4().hex[:6].upper()}"
            barcode = f"QR-{serial}"
            nft_id = f"NFT-{serial}" if blueprint.has_digital_twin else None
            item = SmartProductItem(
                tenant_id=tenant_id,
                batch_id=batch.id,
                serial_number=serial,
                smart_barcode=barcode,
                digital_twin_nft_id=nft_id,
                status=TrackingStatus.IN_FACTORY,
                item_metadata={"production_order": i + 1}
            )
            items.append(item)

        await self.repo.bulk_create_items(items)
        await self.repo.update_batch_status(
            batch.id,
            ProductionStatus.QC_TESTING,
            produced_quantity=len(items),
            notes="Production completed, awaiting QC"
        )

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="PRODUCTION_STARTED",
            resource_id=batch.id,
            details={"batch_number": batch.batch_number, "quantity": len(items)}
        )

        await self.event_bus.publish("manufacturing.batch.completed", {
            "batch_id": batch.id,
            "tenant_id": tenant_id,
            "batch_number": batch.batch_number,
            "quantity": len(items)
        })

        result = {
            "message": f"Production completed for batch {batch.batch_number}",
            "batch_number": batch.batch_number,
            "items_generated": len(items),
            "status": "QC_TESTING"
        }

        if idempotency_key:
            await store_idempotency_result(idempotency_key, result)

        return result

    # ========== إنشاء نموذج منتج (Blueprint) مع تعقيم ==========
    async def create_blueprint(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> ProductBlueprint:
        await self._check_saas_limits(tenant_id, "manufacturing")

        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)
        sanitized_sku = bleach.clean(data.get("sku", ""), tags=[], strip=True)

        blueprint = await self.repo.create_blueprint(
            tenant_id=tenant_id,
            facility_id=data["facility_id"],
            name=sanitized_name,
            sku=sanitized_sku,
            product_category=data["product_category"],
            description=data.get("description"),
            bill_of_materials=data.get("bill_of_materials", {}),
            base_price_mrusdt=data["base_price_mrusdt"],
            is_perishable=data.get("is_perishable", False),
            shelf_life_days=data.get("shelf_life_days"),
            warranty_months=data.get("warranty_months"),
            has_digital_twin=data.get("has_digital_twin", True)
        )

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="BLUEPRINT_CREATED",
            resource_id=blueprint.id,
            details={"sku": blueprint.sku, "name": blueprint.name}
        )

        return blueprint

    # ========== إنشاء قطعة غيار (مع تعقيم) ==========
    async def create_spare_part(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> SparePart:
        await self._check_saas_limits(tenant_id, "manufacturing")

        sanitized_part_name = bleach.clean(data.get("part_name", ""), tags=[], strip=True)

        part = await self.repo.create_spare_part(
            tenant_id=tenant_id,
            part_name=sanitized_part_name,
            part_number=data["part_number"],
            compatible_machines=data.get("compatible_machines", []),
            stock_quantity=data.get("stock_quantity", 0),
            min_stock_threshold=data.get("min_stock_threshold", 5),
            unit_price_mrusdt=data["unit_price_mrusdt"],
            supplier_id=data.get("supplier_id")
        )

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="SPARE_PART_CREATED",
            resource_id=part.id,
            details={"part_name": part.part_name, "part_number": part.part_number}
        )

        return part

    # ========== استهلاك المواد الخام (مع Idempotency) ==========
    async def consume_raw_material(
        self,
        user_id: int,
        tenant_id: int,
        batch_id: int,
        raw_material_batch_id: int,
        quantity: Decimal,
        idempotency_key: str = None
    ) -> MaterialConsumptionLog:
        await self._check_saas_limits(tenant_id, "manufacturing")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        batch = await self.repo.get_batch(batch_id, tenant_id)
        if not batch:
            raise NotFoundError("Batch not found")

        raw_batch = await self.repo.get_raw_material_batch(raw_material_batch_id, tenant_id)
        if not raw_batch:
            raise NotFoundError("Raw material batch not found")

        if raw_batch.quantity_kg < quantity:
            raise InsufficientBalanceError(f"Insufficient raw material. Available: {raw_batch.quantity_kg}kg")

        new_qty = raw_batch.quantity_kg - quantity
        await self.repo.update_raw_material_batch(raw_material_batch_id, quantity_kg=new_qty)

        log = await self.repo.consume_material(
            tenant_id=tenant_id,
            batch_id=batch_id,
            raw_material_batch_id=raw_material_batch_id,
            quantity_used_kg=quantity,
            recorded_by=user_id,
            idempotency_key=idempotency_key
        )

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="MATERIAL_CONSUMED",
            resource_id=log.id,
            details={"batch_id": batch_id, "quantity": float(quantity)}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, log)

        return log

    # ========== الصيانة التنبؤية (مع AI Governance) ==========
    async def analyze_and_schedule_maintenance(
        self,
        user_id: int,
        tenant_id: int,
        production_line_id: int,
        sensor_data: Dict[str, Any]
    ) -> PredictiveMaintenanceLog:
        await self._check_saas_limits(tenant_id, "manufacturing")

        line = await self.repo.get_production_line(production_line_id, tenant_id)
        if not line:
            raise NotFoundError("Production line not found")

        governance = AIGovernanceService(self.db)
        await governance.check_and_consume(
            tenant_id=tenant_id,
            agent_id=4,
            user_id=user_id,
            tokens=200,
            cost=Decimal("0.02")
        )

        try:
            ai_result = await self.ai_service.execute_agent_action(
                agent_id=4,
                tenant_id=tenant_id,
                action_type="ANALYZE_SENSOR",
                payload={
                    "line_id": production_line_id,
                    "sensor_data": sensor_data
                },
                executor_user_id=user_id
            )
            ai_prediction = ai_result.get("result", {})
        except Exception as e:
            logger.warning(f"AI analysis failed, using fallback: {e}")
            ai_prediction = {
                "failure_probability": 0.65,
                "expected_remaining_hours": 150,
                "suggested_component": "bearing_assembly"
            }

        log = await self.repo.create_predictive_log(
            tenant_id=tenant_id,
            production_line_id=production_line_id,
            sensor_data=sensor_data,
            ai_prediction=ai_prediction,
            recommended_action=ai_prediction.get("recommended_action", "Schedule maintenance")
        )

        if ai_prediction.get("failure_probability", 0) > 0.8:
            log = await self.repo.schedule_maintenance(
                log.id,
                datetime.utcnow() + timedelta(days=2)
            )
            await self.event_bus.publish("manufacturing.maintenance.urgent", {
                "log_id": log.id,
                "tenant_id": tenant_id,
                "line_id": production_line_id,
                "scheduled_at": log.maintenance_scheduled_at
            })

        await self.invoicing_service.create_invoice(
            entity_id=tenant_id,
            user_id=user_id,
            amount=Decimal("25.00"),
            description=f"Predictive maintenance analysis for line {production_line_id}",
            due_date=datetime.utcnow() + timedelta(days=30)
        )

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="MAINTENANCE_ANALYZED",
            resource_id=log.id,
            details={"line_id": production_line_id, "probability": ai_prediction.get("failure_probability")}
        )

        return log

    # ========== دوال مساعدة ==========
    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, action_type: str):
        try:
            from app.domains.identity.repository import UserRepository
            user_repo = UserRepository(self.db)
            user = await user_repo.get_by_id(user_id)
            if user and user.referred_by:
                commission = Decimal("10.00") if action_type == "FACILITY_CREATED" else Decimal("5.00")
                await self.affiliate_service.register_commission(
                    affiliate_id=user.referred_by,
                    user_id=user_id,
                    amount=commission,
                    description=f"Affiliate commission for {action_type}",
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")