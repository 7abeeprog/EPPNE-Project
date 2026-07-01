# app/domains/agritech/service.py (الإصدار النهائي المتكامل مع تحديث record_soil_data)
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import datetime, timedelta
import uuid
import bleach
from typing import Optional, List, Dict, Any

from app.domains.agritech.repository import AgriTechRepository
from app.domains.finance.service import FinanceService
from app.domains.ai_agents.service import AIAgentsService
from app.domains.saas.service import SaaSSubscriptionService
from app.domains.affiliate.service import AffiliateService
from app.domains.invoicing.service import InvoicingService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError
from app.core.idempotency import check_idempotency, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging import logger
from app.domains.agritech.models import (
    SmartFarm, FarmZone, CropCycle, HarvestBatch, BioAssetCohort,
    BioProductYield, SupplyChainStage, TraceabilityQR,
    AgriculturalCertificate, SoilSensorReading, WeatherAlert,
    HarvestGrade, BioProductType
)
from app.tasks.agritech import (  # 🔥 استيراد المهام من Celery
    process_soil_reading_high,
    process_soil_reading_medium,
    process_soil_reading_low
)

class AgriTechService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AgriTechRepository(db)
        self.finance = FinanceService(db)
        self.ai_service = AIAgentsService(db)
        self.saas_service = SaaSSubscriptionService(db)
        self.affiliate_service = AffiliateService(db)
        self.invoicing_service = InvoicingService(db)
        self.event_bus = EventBus(redis_client)
        self.redis = redis_client

    # ========== التحقق من صلاحيات SaaS ==========
    async def _check_saas_limits(self, tenant_id: int, feature: str = "agritech"):
        subscription = await self.saas_service.get_active_subscription(tenant_id)
        if not subscription:
            raise PermissionDeniedError("No active subscription found for this entity.")
        features = subscription.features or {}
        if not features.get(feature, False):
            raise PermissionDeniedError("Agritech feature is not included in your current plan.")
        return subscription, features

    # ========== إنشاء مزرعة (مع SaaS + Affiliate + Audit) ==========
    async def create_farm(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> SmartFarm:
        await self._check_saas_limits(tenant_id, "agritech")

        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)

        farm = await self.repo.create_farm(
            tenant_id=tenant_id,
            manager_id=user_id,
            land_asset_id=data["land_asset_id"],
            name=sanitized_name,
            farm_type=data["farm_type"],
            total_area_acres=data["total_area_acres"],
            has_insurance=data.get("has_insurance", False)
        )

        await self._register_affiliate_commission(user_id, tenant_id, "FARM_CREATED")

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="FARM_CREATED",
            resource_id=farm.id,
            details={"name": farm.name, "type": farm.farm_type.value}
        )

        await self.event_bus.publish("agritech.farm.created", {
            "farm_id": farm.id,
            "tenant_id": tenant_id,
            "manager_id": user_id,
            "name": farm.name
        })

        return farm

    # ========== تسجيل الحصاد (مع Idempotency + AI + Invoicing + Audit + Event) ==========
    async def register_harvest(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: str = None
    ) -> Dict[str, Any]:
        # 1. التحقق من SaaS
        await self._check_saas_limits(tenant_id, "agritech")

        # 2. التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # 3. جلب الدورة الزراعية مع التحقق من العزل
        cycle = await self.repo.get_crop_cycle(data["cycle_id"])
        if not cycle or cycle.tenant_id != tenant_id:
            raise NotFoundError("Crop cycle not found")

        # 4. تعقيم المدخلات
        sanitized_data = {
            "cycle_id": data["cycle_id"],
            "grade": data["grade"],
            "quantity_kg": data["quantity_kg"],
            "waste_for_smart_bio_kg": data.get("waste_for_smart_bio_kg", 0),
            "fodder_for_livestock_kg": data.get("fodder_for_livestock_kg", 0),
            "destination_facility_id": data.get("destination_facility_id"),
            "shipment_tracking_number": f"SHIP-{uuid.uuid4().hex[:8].upper()}"
        }

        # 5. استدعاء وكيل الذكاء الاصطناعي (AGRI_EXPERT) لتحليل جودة المحصول
        try:
            ai_result = await self.ai_service.execute_agent_action(
                agent_id=3,
                tenant_id=tenant_id,
                action_type="ANALYZE_SENSOR",
                payload={
                    "crop_name": cycle.crop_name,
                    "quantity": float(data["quantity_kg"]),
                    "grade": data["grade"].value,
                    "farm_id": cycle.zone.farm_id if cycle.zone else None
                },
                executor_user_id=user_id
            )
            logger.info(f"AI Agritech analysis: {ai_result}")
        except Exception as e:
            logger.warning(f"AI analysis failed, proceeding without: {e}")

        # 6. إنشاء فاتورة (Invoicing) لخدمات التحليل
        await self.invoicing_service.create_invoice(
            entity_id=tenant_id,
            user_id=user_id,
            amount=Decimal("10.00"),
            description=f"Harvest analysis for cycle {cycle.id}",
            due_date=datetime.utcnow() + timedelta(days=30)
        )

        # 7. إنشاء سجل الحصاد
        harvest = await self.repo.create_harvest(
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            **sanitized_data
        )

        # 8. تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="HARVEST_REGISTERED",
            resource_id=harvest.id,
            details={"cycle_id": cycle.id, "quantity": float(data["quantity_kg"])}
        )

        # 9. نشر حدث للأتمتة
        await self.event_bus.publish("agritech.harvest.registered", {
            "harvest_id": harvest.id,
            "cycle_id": cycle.id,
            "tenant_id": tenant_id,
            "quantity": float(data["quantity_kg"])
        })

        # 10. تخزين نتيجة Idempotency
        result = {
            "harvest_id": harvest.id,
            "grade": harvest.grade.value,
            "quantity_kg": float(harvest.quantity_kg),
            "tracking_number": harvest.shipment_tracking_number,
            "ai_logistics_actions": self._get_harvest_actions(harvest)
        }
        if idempotency_key:
            await store_idempotency_result(idempotency_key, result)

        return result

    def _get_harvest_actions(self, harvest: HarvestBatch) -> List[str]:
        actions = []
        if harvest.grade == HarvestGrade.GRADE_1_EXPORT:
            actions.append("توجيه للحاويات المبردة للتصدير")
        elif harvest.grade == HarvestGrade.GRADE_2_LOCAL:
            actions.append("توجيه للأسواق المحلية")
        elif harvest.grade == HarvestGrade.GRADE_3_PROCESSING:
            actions.append("توجيه لمصانع التجهيز الغذائي")
        elif harvest.grade == HarvestGrade.GRADE_4_FODDER:
            actions.append("توجيه كأعلاف للثروة الحيوانية")
        elif harvest.grade == HarvestGrade.WASTE_SMART_BIO:
            actions.append("توجيه لمحطات الطاقة الحيوية")
        if harvest.waste_for_smart_bio_kg > 0:
            actions.append(f"{harvest.waste_for_smart_bio_kg} كجم مخلفات لمحطات الطاقة")
        if harvest.fodder_for_livestock_kg > 0:
            actions.append(f"{harvest.fodder_for_livestock_kg} كجم أعلاف للماشية")
        return actions

    # ========== تسجيل الإنتاج الحيواني (محفوظ مع تحسين SaaS) ==========
    async def register_bio_yield(
        self,
        user_id: int,
        tenant_id: int,
        yield_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        await self._check_saas_limits(tenant_id, "agritech")

        yield_record = await self.repo.create_bio_yield(**yield_data)
        actions = []

        if yield_record.product_type in [BioProductType.MILK, BioProductType.EGG, BioProductType.MEAT]:
            actions.append(f"توجيه {yield_record.quantity_unit} وحدة من {yield_record.product_type.value} لسلاسل التبريد")
        elif yield_record.product_type in [BioProductType.VERMICOMPOST, BioProductType.COMPOST_TEA]:
            if yield_record.destination_farm_id:
                actions.append(f"توجيه السماد العضوي للمزرعة رقم {yield_record.destination_farm_id}")
            else:
                actions.append("تخزين السماد العضوي في المستودعات")

        if yield_record.waste_for_smart_bio_kg > 0:
            actions.append(f"{yield_record.waste_for_smart_bio_kg} كجم مخلفات عضوية لمحطات Smart Bio")

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="BIO_YIELD_REGISTERED",
            resource_id=yield_record.id,
            details={"product_type": yield_record.product_type.value}
        )

        return {
            "yield_id": yield_record.id,
            "product_type": yield_record.product_type.value,
            "quantity": float(yield_record.quantity_unit),
            "ai_logistics_actions": actions
        }

    # ========== تسجيل بيانات المستشعر (مع AI Governance + Celery) ==========
    async def record_soil_data(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> SoilSensorReading:
        # 1. التحقق من SaaS
        await self._check_saas_limits(tenant_id, "agritech")

        # 2. التحقق من وجود المنطقة
        zone = await self.repo.get_zone(data["zone_id"])
        if not zone or zone.tenant_id != tenant_id:
            raise NotFoundError("Zone not found")

        # 3. تعقيم المدخلات
        sanitized_data = {
            "tenant_id": tenant_id,
            "zone_id": data["zone_id"],
            "sensor_device_id": bleach.clean(data["sensor_device_id"], tags=[], strip=True),
            "moisture_percent": data.get("moisture_percent"),
            "temperature_celsius": data.get("temperature_celsius"),
            "ph_level": data.get("ph_level"),
            "nitrogen_ppm": data.get("nitrogen_ppm"),
            "phosphorus_ppm": data.get("phosphorus_ppm"),
            "potassium_ppm": data.get("potassium_ppm"),
            "recorded_at": data.get("recorded_at", datetime.utcnow())
        }

        # 4. تسجيل القراءة في قاعدة البيانات
        reading = await self.repo.create_soil_reading(**sanitized_data)

        # 5. 🔥 إرسال المهمة إلى Celery حسب نوع المنطقة
        zone = await self.repo.get_zone(data["zone_id"])
        farm = await self.repo.get_farm(zone.farm_id)

        # تحديد المسار المناسب حسب نوع المزرعة
        farm_type = farm.farm_type.value
        if farm_type in ["TRADITIONAL_SOIL", "HYDROPONICS"]:
            queue = "agritech.high"
            task_func = process_soil_reading_high
        elif farm_type in ["VERTICAL_FARM", "AQUAPONICS"]:
            queue = "agritech.medium"
            task_func = process_soil_reading_medium
        else:  # ALGAE_FARM, VERMICULTURE_FARM, إلخ
            queue = "agritech.low"
            task_func = process_soil_reading_low

        # إرسال المهمة إلى Celery
        task_func.apply_async(args=[reading.id], queue=queue)

        # 6. تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="SOIL_READING_RECORDED",
            resource_id=reading.id,
            details={"zone_id": zone.id, "moisture": data.get("moisture_percent")}
        )

        return reading

    # ========== سلسلة التوريد (محفوظ مع تحسين SaaS و Audit) ==========
    async def add_traceability_stage(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> SupplyChainStage:
        await self._check_saas_limits(tenant_id, "agritech")

        stage = await self.repo.create_supply_chain_stage(
            operator_id=user_id,
            **data
        )
        tx_hash = f"0xTRACE{stage.id}{uuid.uuid4().hex[:8]}"
        stage.blockchain_tx_hash = tx_hash
        await self.db.commit()
        await self.db.refresh(stage)

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="TRACEABILITY_STAGE_ADDED",
            resource_id=stage.id,
            details={"traceable_type": data["traceable_type"], "traceable_id": data["traceable_id"]}
        )

        return stage

    # ========== توليد QR للتتبع (محفوظ) ==========
    async def generate_traceability_qr(
        self,
        tenant_id: int,
        traceable_type: str,
        traceable_id: int
    ) -> TraceabilityQR:
        await self._check_saas_limits(tenant_id, "agritech")

        import qrcode
        from io import BytesIO

        qr_hash = uuid.uuid4().hex[:12]
        public_url = f"https://trace.eppne.com/{qr_hash}"
        qr_code_img = qrcode.make(public_url)

        qr = await self.repo.create_traceability_qr(
            tenant_id=tenant_id,
            traceable_type=traceable_type,
            traceable_id=traceable_id,
            qr_code=qr_hash,
            public_url=public_url,
            expires_at=datetime.utcnow() + timedelta(days=365)
        )
        return qr

    # ========== إصدار شهادات (محفوظ مع تحسين SaaS و Audit) ==========
    async def issue_certificate(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> AgriculturalCertificate:
        await self._check_saas_limits(tenant_id, "agritech")

        cert = await self.repo.create_certificate(
            tenant_id=tenant_id,
            created_by=user_id,
            **data
        )
        cert.certificate_nft_id = f"CERT-{cert.id}-{uuid.uuid4().hex[:8].upper()}"
        await self.db.commit()
        await self.db.refresh(cert)

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="CERTIFICATE_ISSUED",
            resource_id=cert.id,
            details={"type": data["certificate_type"], "entity_id": data["certified_entity_id"]}
        )

        return cert

    # ========== جلب تنبيهات الطقس ==========
    async def get_weather_alerts(self, tenant_id: int) -> List[WeatherAlert]:
        await self._check_saas_limits(tenant_id, "agritech")
        return await self.repo.get_active_weather_alerts(tenant_id)

    # ========== إنشاء تنبيه (مع تعقيم) ==========
    async def _create_alert(self, tenant_id: int, alert_type: str, message: str, farm_id: int = None):
        sanitized_message = bleach.clean(message, tags=[], strip=True)
        alert = WeatherAlert(
            tenant_id=tenant_id,
            alert_type=alert_type,
            severity="WARNING",
            message=sanitized_message,
            start_time=datetime.utcnow(),
            affected_farm_ids=[farm_id] if farm_id else []
        )
        self.db.add(alert)
        await self.db.commit()

    # ========== تسجيل الإحالة (Affiliate) ==========
    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, action_type: str):
        try:
            from app.domains.identity.repository import UserRepository
            user_repo = UserRepository(self.db)
            user = await user_repo.get_by_id(user_id)
            if user and user.referred_by:
                commission = Decimal("5.00") if action_type == "FARM_CREATED" else Decimal("2.00")
                await self.affiliate_service.register_commission(
                    affiliate_id=user.referred_by,
                    user_id=user_id,
                    amount=commission,
                    description=f"Affiliate commission for {action_type}",
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")