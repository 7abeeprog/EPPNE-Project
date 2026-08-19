# app/domains/manufacturing/service.py (الإصدار النهائي مع حل جميع المشاكل)
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import datetime, timedelta
import uuid
import bleach
from typing import Optional, Dict, Any, List, cast

from app.domains.manufacturing.repository import ManufacturingRepository
from app.domains.finance.service import FinanceService
from app.domains.ai_agents.service import AIAgentsService
from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
from app.domains.affiliate.service import AffiliateService
from app.domains.invoicing.service import InvoicingService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, ValidationError
from app.core.idempotency import get_idempotency_result, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging_conf import logger
from app.domains.ai_governance.service import AIGovernanceService
from app.domains.manufacturing.models import (
    ManufacturingFacility, ProductionLine, ProductBlueprint, ProductionBatch,
    SmartProductItem, RawMaterialBatch, MaterialConsumptionLog,
    ProductDigitalTwin, QualityCertificate, PredictiveMaintenanceLog, SparePart,
    ProductionStatus, TrackingStatus
)
from app.domains.identity.models import User


class ManufacturingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ManufacturingRepository(db)
        self.event_bus = EventBus(cast(Any, redis_client))
        self.redis = redis_client

    # ============================================================
    # دوال مساعدة
    # ============================================================

    async def _check_saas_limits(self, tenant_id: int, feature: str = "manufacturing"):
        saas_service = SaaSSubscriptionService(self.db, tenant_id)
        subscription = await saas_service.get_active_subscription(tenant_id)  # type: ignore
        if not subscription:
            raise PermissionDeniedError("No active subscription found.")
        if not subscription.plan:
            raise PermissionDeniedError("No valid subscription plan found.")
        features = subscription.plan.features or []
        if feature not in features:
            raise PermissionDeniedError("Manufacturing feature is not included in your current plan.")
        return subscription, features

    async def _get_user(self, user_id: int, tenant_id: int) -> Optional[User]:
        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)
        return await user_repo.get_by_id(user_id, tenant_id)

    async def _get_user_email(self, user_id: int, tenant_id: int) -> str:
        user = await self._get_user(user_id, tenant_id)
        return user.email if user else f"user_{user_id}@eppne.com"  # type: ignore

    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, action_type: str):
        affiliate_service = AffiliateService(self.db, tenant_id)
        try:
            user = await self._get_user(user_id, tenant_id)
            if user and user.referred_by:  # type: ignore
                commission = Decimal("10.00") if action_type == "FACILITY_CREATED" else Decimal("5.00")
                await affiliate_service.register_commission(  # type: ignore
                    affiliate_id=user.referred_by,  # type: ignore
                    user_id=user_id,
                    amount=commission,
                    description=f"Affiliate commission for {action_type}",
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")

    # ============================================================
    # دوال Idempotency الموحّدة
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
    # 1. المنشآت (Facilities)
    # ============================================================

    async def create_facility(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> ManufacturingFacility:
        await self._check_saas_limits(tenant_id, "manufacturing")
        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)

        async with self.db.begin_nested():
            facility = await self.repo.create_facility(
                tenant_id=tenant_id,
                manager_id=user_id,
                name=sanitized_name,
                facility_type=data["facility_type"],
                location_gps=data.get("location_gps"),
                real_estate_unit_id=data.get("real_estate_unit_id")
            )

        await self.db.commit()

        await self._register_affiliate_commission(user_id, tenant_id, "FACILITY_CREATED")

        await audit_log(**{  # type: ignore
            "user_id": user_id,
            "tenant_id": tenant_id,
            "action": "FACILITY_CREATED",
            "resource_id": facility.id,
            "details": {"name": facility.name, "type": facility.facility_type.value if hasattr(facility.facility_type, 'value') else str(facility.facility_type)}
        })

        await self.event_bus.publish("manufacturing.facility.created", {
            "facility_id": facility.id,
            "tenant_id": tenant_id,
            "manager_id": user_id,
            "name": facility.name
        })

        return facility

    async def list_facilities(self, tenant_id: int, skip: int = 0, limit: int = 50) -> List[ManufacturingFacility]:
        return await self.repo.list_facilities(tenant_id, skip, limit)

    async def get_facility(self, facility_id: int, tenant_id: int) -> Optional[ManufacturingFacility]:
        facility = await self.repo.get_facility(facility_id, tenant_id)
        if not facility:
            raise NotFoundError("Facility not found")
        return facility

    # ============================================================
    # 2. خطوط الإنتاج (Production Lines)
    # ============================================================

    async def add_production_line(
        self,
        user_id: int,
        tenant_id: int,
        facility_id: int,
        data: Dict[str, Any]
    ) -> ProductionLine:
        await self._check_saas_limits(tenant_id, "manufacturing")

        facility = await self.repo.get_facility(facility_id, tenant_id)
        if not facility:
            raise NotFoundError("Facility not found")

        async with self.db.begin_nested():
            line = await self.repo.create_production_line(
                facility_id=facility_id,
                **data
            )

        await self.db.commit()

        await audit_log(**{  # type: ignore
            "user_id": user_id,
            "tenant_id": tenant_id,
            "action": "PRODUCTION_LINE_ADDED",
            "resource_id": line.id,
            "details": {"name": line.name, "facility_id": facility_id}
        })

        return line

    # ============================================================
    # 3. النماذج (Blueprints)
    # ============================================================

    async def create_blueprint(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> ProductBlueprint:
        await self._check_saas_limits(tenant_id, "manufacturing")

        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)
        sanitized_sku = bleach.clean(data.get("sku", ""), tags=[], strip=True)

        facility = await self.repo.get_facility(data["facility_id"], tenant_id)
        if not facility:
            raise NotFoundError("Facility not found")

        async with self.db.begin_nested():
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

        await self.db.commit()

        await audit_log(**{  # type: ignore
            "user_id": user_id,
            "tenant_id": tenant_id,
            "action": "BLUEPRINT_CREATED",
            "resource_id": blueprint.id,
            "details": {"sku": blueprint.sku, "name": blueprint.name}
        })

        return blueprint

    async def get_blueprint(self, blueprint_id: int, tenant_id: int) -> Optional[ProductBlueprint]:
        return await self.repo.get_blueprint(blueprint_id, tenant_id)

    # ============================================================
    # 4. دفعات الإنتاج (Production Batches)
    # ============================================================

    async def create_batch(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> ProductionBatch:
        await self._check_saas_limits(tenant_id, "manufacturing")

        blueprint = await self.repo.get_blueprint(data["product_blueprint_id"], tenant_id)
        if not blueprint:
            raise NotFoundError("Blueprint not found")

        line = await self.repo.get_production_line(data["line_id"], tenant_id)
        if not line:
            raise NotFoundError("Production line not found")

        async with self.db.begin_nested():
            batch = await self.repo.create_batch(
                tenant_id=tenant_id,
                **data
            )

        await self.db.commit()

        await audit_log(**{  # type: ignore
            "user_id": user_id,
            "tenant_id": tenant_id,
            "action": "PRODUCTION_BATCH_CREATED",
            "resource_id": batch.id,
            "details": {"batch_number": batch.batch_number, "blueprint_id": data["product_blueprint_id"]}
        })

        return batch

    async def get_batch(self, batch_id: int, tenant_id: int) -> Optional[ProductionBatch]:
        return await self.repo.get_batch(batch_id, tenant_id)

    # ============================================================
    # 5. بدء الإنتاج (Start Production) – مع Idempotency محسّن
    # ============================================================

    async def start_production(
        self,
        user_id: int,
        tenant_id: int,
        batch_id: int,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        await self._check_saas_limits(tenant_id, "manufacturing")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                return cached

        batch = await self.repo.get_batch(batch_id, tenant_id)
        if not batch:
            raise NotFoundError("Batch not found")
        if batch.status != ProductionStatus.PLANNED:  # type: ignore
            raise ValueError("Batch already started or completed")

        blueprint = await self.repo.get_blueprint(batch.product_blueprint_id, tenant_id)  # type: ignore
        if not blueprint:
            raise NotFoundError("Blueprint not found")

        governance = AIGovernanceService(self.db, tenant_id)
        await governance.check_and_consume(
            agent_id=4,
            user_id=user_id,
            action_type="MANUFACTURING_ANALYSIS",
            tokens=150,
            cost=Decimal("0.015")
        )

        ai_service = AIAgentsService(self.db, tenant_id)
        try:
            ai_result = await ai_service.execute_agent_action(
                agent_id=4,
                action_type="ANALYZE_SENSOR",
                payload={
                    "batch_id": batch.id,
                    "target_quantity": batch.target_quantity,  # type: ignore
                    "blueprint": blueprint.sku,
                    "line_id": batch.line_id  # type: ignore
                },
                executor_user_id=user_id,
                idempotency_key=f"AI-BATCH-T{tenant_id}-{batch.id}"
            )
            logger.info(f"AI Manufacturing optimization: {ai_result}")
        except Exception as e:
            logger.warning(f"AI analysis failed, proceeding without: {e}")

        estimated_cost = Decimal(batch.target_quantity) * Decimal("0.50")  # type: ignore
        invoice_service = InvoicingService(self.db, tenant_id)
        await invoice_service.create_invoice(  # type: ignore
            entity_id=tenant_id,
            user_id=user_id,
            amount=estimated_cost,
            description=f"Production cost for batch {batch.batch_number}",
            due_date=datetime.utcnow() + timedelta(days=30)
        )

        async with self.db.begin_nested():
            items = []
            for i in range(batch.target_quantity):  # type: ignore
                serial = f"{blueprint.sku}-{batch.batch_number}-{uuid.uuid4().hex[:6].upper()}"
                barcode = f"QR-{serial}"
                nft_id = f"NFT-{serial}" if blueprint.has_digital_twin else None  # type: ignore
                item = SmartProductItem(
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
                cast(int, batch.id),
                ProductionStatus.QC_TESTING,
                produced_quantity=len(items),
                notes="Production completed, awaiting QC"
            )

        await self.db.commit()

        await audit_log(**{  # type: ignore
            "user_id": user_id,
            "tenant_id": tenant_id,
            "action": "PRODUCTION_STARTED",
            "resource_id": batch.id,
            "details": {"batch_number": batch.batch_number, "quantity": len(items)}
        })

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

        # تخزين النتيجة كاملة
        if idempotency_key:
            await self._store_idempotency(idempotency_key, result)

        return result

    # ============================================================
    # 6. المواد الخام (Raw Materials)
    # ============================================================

    async def register_raw_material_batch(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> RawMaterialBatch:
        await self._check_saas_limits(tenant_id, "manufacturing")

        sanitized_material_name = bleach.clean(data.get("material_name", ""), tags=[], strip=True)
        sanitized_traceability = bleach.clean(data.get("source_traceability", ""), tags=[], strip=True)

        quantity = data["quantity_kg"]
        unit_price = data["unit_price_mrusdt"]
        total_cost = quantity * unit_price
        batch_number = f"RM-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        async with self.db.begin_nested():
            batch = await self.repo.create_raw_material_batch(
                tenant_id=tenant_id,
                material_name=sanitized_material_name,
                supplier_id=data.get("supplier_id"),
                source_traceability=sanitized_traceability,
                quantity_kg=quantity,
                unit_price_mrusdt=unit_price,
                total_cost_mrusdt=total_cost,
                received_date=data.get("received_date", datetime.utcnow()),
                quality_check_passed=data.get("quality_check_passed", True),
                quality_certificate_hash=data.get("quality_certificate_hash"),
                batch_number=batch_number,
                blockchain_tx_hash=None
            )

        await self.db.commit()

        await audit_log(**{  # type: ignore
            "user_id": user_id,
            "tenant_id": tenant_id,
            "action": "RAW_MATERIAL_REGISTERED",
            "resource_id": batch.id,
            "details": {
                "material_name": batch.material_name,
                "quantity": float(cast(Any, batch.quantity_kg)),
                "supplier_id": batch.supplier_id
            }
        })

        await self.event_bus.publish("manufacturing.raw_material.received", {
            "batch_id": batch.id,
            "tenant_id": tenant_id,
            "material_name": batch.material_name,
            "quantity": float(cast(Any, batch.quantity_kg)),
            "supplier_id": batch.supplier_id
        })

        return batch

    async def list_raw_materials(self, tenant_id: int, skip: int = 0, limit: int = 100) -> List[RawMaterialBatch]:
        return await self.repo.list_raw_materials(tenant_id, skip, limit)

    # ============================================================
    # 7. استهلاك المواد الخام – مع Idempotency محسّن (تخزين النتيجة كاملة)
    # ============================================================

    async def consume_raw_material(
        self,
        user_id: int,
        tenant_id: int,
        batch_id: int,
        raw_material_batch_id: int,
        quantity: Decimal,
        idempotency_key: Optional[str] = None
    ) -> MaterialConsumptionLog:
        await self._check_saas_limits(tenant_id, "manufacturing")

        # 1. التحقق من Idempotency – نعيد النتيجة المخزنة كاملة
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                # بناء كائن MaterialConsumptionLog من البيانات المخزنة
                log_id = cached.get("log_id")
                if log_id:
                    try:
                        from app.domains.manufacturing.models import MaterialConsumptionLog
                        return MaterialConsumptionLog(
                            id=log_id,
                            batch_id=cached.get("batch_id"),
                            raw_material_batch_id=cached.get("raw_material_batch_id"),
                            quantity_used_kg=Decimal(cached.get("quantity_used_kg", 0)),
                            recorded_by=cached.get("recorded_by"),
                            recorded_at=datetime.utcnow(),
                            notes=cached.get("notes"),
                            idempotency_key=idempotency_key
                        )
                    except Exception:
                        raise ValidationError("Idempotency record exists but cannot reconstruct log.")
                raise ValidationError("Idempotency record exists but log not found.")

        batch = await self.repo.get_batch(batch_id, tenant_id)
        if not batch:
            raise NotFoundError("Batch not found")

        raw_batch = await self.repo.get_raw_material_batch(raw_material_batch_id, tenant_id)
        if not raw_batch:
            raise NotFoundError("Raw material batch not found")

        if raw_batch.quantity_kg < quantity:  # type: ignore
            raise InsufficientBalanceError(f"Insufficient raw material. Available: {raw_batch.quantity_kg}kg")

        new_qty = raw_batch.quantity_kg - quantity  # type: ignore
        await self.repo.update_raw_material_batch(raw_material_batch_id, quantity_kg=new_qty)

        async with self.db.begin_nested():
            log = await self.repo.consume_material(
                tenant_id=tenant_id,
                batch_id=batch_id,
                raw_material_batch_id=raw_material_batch_id,
                quantity_used_kg=quantity,
                recorded_by=user_id,
                idempotency_key=idempotency_key
            )

        await self.db.commit()

        await audit_log(**{  # type: ignore
            "user_id": user_id,
            "tenant_id": tenant_id,
            "action": "MATERIAL_CONSUMED",
            "resource_id": log.id,
            "details": {"batch_id": batch_id, "quantity": float(quantity)}
        })

        # تخزين النتيجة كاملة (بدلاً من المعرف فقط) لضمان إمكانية إعادة بناء الكائن
        if idempotency_key:
            result_data = {
                "log_id": log.id,
                "batch_id": log.batch_id,
                "raw_material_batch_id": log.raw_material_batch_id,
                "quantity_used_kg": float(cast(Any, log.quantity_used_kg)),
                "recorded_by": log.recorded_by,
                "notes": log.notes,
                "recorded_at": log.recorded_at.isoformat() if log.recorded_at else None
            }
            await self._store_idempotency(idempotency_key, result_data)

        return log

    # ============================================================
    # 8. المنتجات الذكية والتوأم الرقمي
    # ============================================================

    async def create_digital_twin(
        self,
        product_item_id: int,
        batch_id: int,
        production_line_id: Optional[int],
        tenant_id: int,
        user_id: int
    ) -> ProductDigitalTwin:
        await self._check_saas_limits(tenant_id, "manufacturing")

        item = await self.repo.get_item(product_item_id, tenant_id)
        if not item:
            raise NotFoundError("Product item not found")

        batch = await self.repo.get_batch(batch_id, tenant_id)
        if not batch:
            raise NotFoundError("Batch not found")

        blueprint = await self.repo.get_blueprint(batch.product_blueprint_id, tenant_id)  # type: ignore
        if not blueprint:
            raise NotFoundError("Blueprint not found")

        async with self.db.begin_nested():
            twin = await self.repo.create_digital_twin(
                product_item_id=product_item_id,
                manufacturing_date=datetime.utcnow(),
                batch_number=batch.batch_number,  # type: ignore
                production_line_id=production_line_id,
                actual_bom=blueprint.bill_of_materials,  # type: ignore
                maintenance_log=[],
                total_maintenance_cost_mrusdt=Decimal(0),
                quality_certificates=[],
                digital_twin_nft_id=f"TWIN-{uuid.uuid4().hex[:12].upper()}",
                ipfs_metadata_hash=None
            )

        await self.db.commit()

        await audit_log(**{  # type: ignore
            "user_id": user_id,
            "tenant_id": tenant_id,
            "action": "DIGITAL_TWIN_CREATED",
            "resource_id": twin.id,
            "details": {"product_item_id": product_item_id, "batch_id": batch_id}
        })

        return twin

    async def get_digital_twin(self, product_item_id: int, tenant_id: int) -> Optional[ProductDigitalTwin]:
        return await self.repo.get_digital_twin(product_item_id, tenant_id)

    # ============================================================
    # 9. شهادات الجودة (Quality Certificates)
    # ============================================================

    async def issue_quality_certificate(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> QualityCertificate:
        await self._check_saas_limits(tenant_id, "manufacturing")

        if data["expiry_date"] <= data["issue_date"]:
            raise ValueError("expiry_date must be after issue_date")

        async with self.db.begin_nested():
            cert = await self.repo.create_quality_certificate(
                tenant_id=tenant_id,
                created_by=user_id,
                **data
            )

        await self.db.commit()

        await audit_log(**{  # type: ignore
            "user_id": user_id,
            "tenant_id": tenant_id,
            "action": "QUALITY_CERTIFICATE_ISSUED",
            "resource_id": cert.id,
            "details": {"type": cert.certificate_type, "entity_id": data["certified_entity_id"]}
        })

        await self.event_bus.publish("manufacturing.quality_certificate.issued", {
            "certificate_id": cert.id,
            "entity_type": data["certified_entity_type"],
            "entity_id": data["certified_entity_id"]
        })

        return cert

    async def get_entity_certificates(
        self,
        entity_type: str,
        entity_id: int,
        tenant_id: int
    ) -> List[QualityCertificate]:
        return await self.repo.get_certificates_for_entity(entity_type, entity_id, tenant_id)

    # ============================================================
    # 10. الصيانة التنبؤية (Predictive Maintenance)
    # ============================================================

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

        governance = AIGovernanceService(self.db, tenant_id)
        await governance.check_and_consume(
            agent_id=4,
            user_id=user_id,
            action_type="MAINTENANCE_ANALYSIS",
            tokens=200,
            cost=Decimal("0.02")
        )

        ai_service = AIAgentsService(self.db, tenant_id)
        try:
            ai_result = await ai_service.execute_agent_action(
                agent_id=4,
                action_type="ANALYZE_SENSOR",
                payload={
                    "line_id": production_line_id,
                    "sensor_data": sensor_data
                },
                executor_user_id=user_id,
                idempotency_key=f"AI-MAINTENANCE-T{tenant_id}-{production_line_id}-{uuid.uuid4().hex[:8]}"
            )
            ai_prediction = ai_result.get("result", {})
        except Exception as e:
            logger.warning(f"AI analysis failed, using fallback: {e}")
            ai_prediction = {
                "failure_probability": 0.65,
                "expected_remaining_hours": 150,
                "suggested_component": "bearing_assembly"
            }

        async with self.db.begin_nested():
            log = await self.repo.create_predictive_log(
                tenant_id=tenant_id,
                production_line_id=production_line_id,
                sensor_data=sensor_data,
                ai_prediction=ai_prediction,
                recommended_action=ai_prediction.get("recommended_action", "Schedule maintenance")
            )

            if ai_prediction.get("failure_probability", 0) > 0.8:
                log = await self.repo.schedule_maintenance(
                    cast(int, log.id),
                    datetime.utcnow() + timedelta(days=2)
                )
                await self.event_bus.publish("manufacturing.maintenance.urgent", {
                    "log_id": log.id,
                    "tenant_id": tenant_id,
                    "line_id": production_line_id,
                    "scheduled_at": log.maintenance_scheduled_at
                })

        invoice_service = InvoicingService(self.db, tenant_id)
        await invoice_service.create_invoice(  # type: ignore
            entity_id=tenant_id,
            user_id=user_id,
            amount=Decimal("25.00"),
            description=f"Predictive maintenance analysis for line {production_line_id}",
            due_date=datetime.utcnow() + timedelta(days=30)
        )

        await self.db.commit()

        await audit_log(**{  # type: ignore
            "user_id": user_id,
            "tenant_id": tenant_id,
            "action": "MAINTENANCE_ANALYZED",
            "resource_id": log.id,
            "details": {"line_id": production_line_id, "probability": ai_prediction.get("failure_probability")}
        })

        return log

    async def get_pending_maintenance(self, production_line_id: int, tenant_id: int) -> List[PredictiveMaintenanceLog]:
        return await self.repo.get_pending_maintenance(production_line_id, tenant_id)

    async def schedule_maintenance(self, log_id: int, scheduled_at: datetime) -> PredictiveMaintenanceLog:
        return await self.repo.schedule_maintenance(log_id, scheduled_at)

    # ============================================================
    # 11. قطع الغيار (Spare Parts)
    # ============================================================

    async def create_spare_part(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> SparePart:
        await self._check_saas_limits(tenant_id, "manufacturing")

        sanitized_part_name = bleach.clean(data.get("part_name", ""), tags=[], strip=True)

        async with self.db.begin_nested():
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

        await self.db.commit()

        await audit_log(**{  # type: ignore
            "user_id": user_id,
            "tenant_id": tenant_id,
            "action": "SPARE_PART_CREATED",
            "resource_id": part.id,
            "details": {"part_name": part.part_name, "part_number": part.part_number}
        })

        return part

    async def list_spare_parts(self, tenant_id: int, skip: int = 0, limit: int = 100) -> List[SparePart]:
        return await self.repo.list_spare_parts(tenant_id, skip, limit)

    async def restock_spare_part(
        self,
        part_id: int,
        quantity_added: int,
        user_id: int,
        tenant_id: int
    ) -> SparePart:
        await self._check_saas_limits(tenant_id, "manufacturing")

        part = await self.repo.get_spare_part(part_id, tenant_id)
        if not part:
            raise NotFoundError("Spare part not found")

        async with self.db.begin_nested():
            updated = await self.repo.update_spare_part_stock(part_id, quantity_added)

        await self.db.commit()

        await audit_log(**{  # type: ignore
            "user_id": user_id,
            "tenant_id": tenant_id,
            "action": "SPARE_PART_RESTOCKED",
            "resource_id": part.id,
            "details": {"part_name": part.part_name, "quantity_added": quantity_added}
        })

        return updated