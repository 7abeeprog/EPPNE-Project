# app/domains/agritech/service.py (الإصدار النهائي المتكامل مع التصحيحات)
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import datetime, timedelta
import uuid
import bleach
from typing import Optional, List, Dict, Any, cast
from fastapi import HTTPException

from app.domains.agritech.repository import AgriTechRepository
from app.domains.finance.service import FinanceService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, ValidationError
from app.core.idempotency import check_idempotency, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging_conf import logger
from app.domains.agritech.models import (
    SmartFarm, FarmZone, CropCycle, HarvestBatch, BioAssetCohort,
    BioProductYield, SupplyChainStage, TraceabilityQR,
    AgriculturalCertificate, SoilSensorReading, WeatherAlert,
    HarvestGrade, BioProductType, FarmType
)
from app.domains.agritech.schemas import (
    SmartFarmResponse, FarmZoneResponse, CropCycleResponse,
    HarvestBatchResponse, BioAssetCohortResponse, BioProductYieldResponse,
    SupplyChainStageResponse, TraceabilityQRResponse,
    AgriculturalCertificateResponse, SoilSensorReadingResponse,
    WeatherAlertResponse
)


class AgriTechService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AgriTechRepository(db)
        self.finance = FinanceService(db)
        self.event_bus = EventBus(redis_client)  # type: ignore

    # ==========================================
    # دوال مساعدة
    # ==========================================

    async def _check_tenant_access(self, tenant_id: int, resource_tenant_id: int):
        """التحقق من أن المستأجر يملك المورد"""
        if tenant_id != resource_tenant_id:
            raise PermissionDeniedError("ليس لديك صلاحية الوصول لهذا المورد")

    async def _validate_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """التحقق من Idempotency"""
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached
        return None

    async def _store_idempotency(self, idempotency_key: str, result: Dict[str, Any]):
        """تخزين نتيجة Idempotency"""
        if idempotency_key:
            await store_idempotency_result(idempotency_key, result)

    # ==========================================
    # 1. المزارع (Farms)
    # ==========================================

    async def create_farm(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> SmartFarm:
        """إنشاء مزرعة جديدة"""
        # تعقيم المدخلات
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

        # تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="FARM_CREATED",
            resource_id=farm.id,  # type: ignore
            details={"name": farm.name, "type": farm.farm_type.value}
        )

        # نشر حدث
        await self.event_bus.publish("agritech.farm.created", {
            "farm_id": farm.id,
            "tenant_id": tenant_id,
            "manager_id": user_id,
            "name": farm.name
        })

        return farm

    async def list_farms(self, tenant_id: int, farm_type: Optional[str] = None, skip: int = 0, limit: int = 50) -> List[SmartFarm]:
        """جلب قائمة المزارع للمستأجر"""
        return await self.repo.list_farms(tenant_id, farm_type, skip, limit)  # type: ignore

    async def get_farm(self, farm_id: int, tenant_id: int) -> Optional[SmartFarm]:
        """جلب تفاصيل مزرعة محددة"""
        farm = await self.repo.get_farm(farm_id)
        if farm:
            await self._check_tenant_access(tenant_id, farm.tenant_id)  # type: ignore
        return farm

    # ==========================================
    # 2. المناطق (Zones)
    # ==========================================

    async def add_farm_zone(self, farm_id: int, tenant_id: int, user_id: int, data: Dict[str, Any]) -> FarmZone:
        """إضافة منطقة جديدة لمزرعة"""
        # التحقق من وجود المزرعة وصلاحيتها
        farm = await self.repo.get_farm(farm_id)
        if not farm:
            raise NotFoundError("المزرعة غير موجودة")
        await self._check_tenant_access(tenant_id, farm.tenant_id)  # type: ignore

        zone = await self.repo.create_zone(
            farm_id=farm_id,
            tenant_id=tenant_id,
            **data
        )

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="ZONE_ADDED",
            resource_id=zone.id,  # type: ignore
            details={"zone_code": zone.zone_code, "farm_id": farm_id}
        )

        return zone

    async def list_farm_zones(self, farm_id: int, tenant_id: int) -> List[FarmZone]:
        """جلب مناطق مزرعة محددة"""
        farm = await self.repo.get_farm(farm_id)
        if not farm:
            raise NotFoundError("المزرعة غير موجودة")
        await self._check_tenant_access(tenant_id, farm.tenant_id)  # type: ignore
        return await self.repo.list_zones(farm_id)  # type: ignore

    # ==========================================
    # 3. الدورات الزراعية (Crop Cycles)
    # ==========================================

    async def start_crop_cycle(
        self,
        zone_id: int,
        tenant_id: int,
        user_id: int,
        data: Dict[str, Any],
        idempotency_key: str
    ) -> CropCycle:
        """بدء دورة زراعية جديدة (مع Idempotency)"""
        # 1. التحقق من Idempotency
        cached = await self._validate_idempotency(idempotency_key)
        if cached:
            return cast(CropCycle, cached)

        # 2. التحقق من المنطقة
        zone = await self.repo.get_zone(zone_id)
        if not zone:
            raise NotFoundError("المنطقة غير موجودة")
        await self._check_tenant_access(tenant_id, zone.tenant_id)  # type: ignore

        # 3. إنشاء الدورة
        cycle = await self.repo.create_crop_cycle(
            zone_id=zone_id,
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            **data
        )

        # 4. تخزين Idempotency
        await self._store_idempotency(idempotency_key, {"cycle_id": cycle.id})

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="CROP_CYCLE_STARTED",
            resource_id=cycle.id,  # type: ignore
            details={"crop_name": cycle.crop_name, "zone_id": zone_id}
        )

        return cycle

    async def list_crop_cycles(self, zone_id: int, tenant_id: int) -> List[CropCycle]:
        """جلب الدورات الزراعية لمنطقة محددة"""
        zone = await self.repo.get_zone(zone_id)
        if not zone:
            raise NotFoundError("المنطقة غير موجودة")
        await self._check_tenant_access(tenant_id, zone.tenant_id)  # type: ignore
        return await self.repo.list_crop_cycles(zone_id)  # type: ignore

    # ==========================================
    # 4. الحصاد (Harvest) - مع AI وتحليل
    # ==========================================

    async def register_harvest(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: str
    ) -> Dict[str, Any]:
        """تسجيل محصول جديد (مع Idempotency و تحليل AI)"""
        # 1. التحقق من Idempotency
        cached = await self._validate_idempotency(idempotency_key)
        if cached:
            return cached

        # 2. التحقق من الدورة الزراعية
        cycle = await self.repo.get_crop_cycle(data["cycle_id"])  # type: ignore
        if not cycle:
            raise NotFoundError("الدورة الزراعية غير موجودة")
        await self._check_tenant_access(tenant_id, cycle.tenant_id)  # type: ignore

        # 3. تعقيم المدخلات
        sanitized_data = {
            "cycle_id": data["cycle_id"],
            "grade": data["grade"],
            "quantity_kg": data["quantity_kg"],
            "waste_for_smart_bio_kg": data.get("waste_for_smart_bio_kg", Decimal(0)),
            "fodder_for_livestock_kg": data.get("fodder_for_livestock_kg", Decimal(0)),
            "destination_facility_id": data.get("destination_facility_id"),
            "shipment_tracking_number": f"SHIP-{uuid.uuid4().hex[:8].upper()}"
        }

        # 4. 🔥 معاملة ذرية (Atomicity)
        async with self.db.begin_nested():
            harvest = await self.repo.create_harvest(
                tenant_id=tenant_id,
                idempotency_key=idempotency_key,
                **sanitized_data
            )

        # 5. تحليل AI (خارج المعاملة لتجنب القفل)
        ai_logistics_actions = self._get_harvest_actions(harvest)

        # 6. تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="HARVEST_REGISTERED",
            resource_id=harvest.id,  # type: ignore
            details={"cycle_id": cycle.id, "quantity": float(data["quantity_kg"])}
        )

        # 7. نشر حدث
        await self.event_bus.publish("agritech.harvest.registered", {
            "harvest_id": harvest.id,
            "cycle_id": cycle.id,
            "tenant_id": tenant_id,
            "quantity": float(data["quantity_kg"])
        })

        # 8. تخزين Idempotency
        result = {
            "harvest_id": harvest.id,
            "grade": harvest.grade.value,
            "quantity_kg": float(harvest.quantity_kg),  # type: ignore
            "tracking_number": harvest.shipment_tracking_number,
            "ai_logistics_actions": ai_logistics_actions
        }
        await self._store_idempotency(idempotency_key, result)

        return result

    def _get_harvest_actions(self, harvest: HarvestBatch) -> List[str]:
        """تحديد إجراءات لوجستية بناءً على جودة المحصول"""
        actions = []
        grade_str = harvest.grade.value if hasattr(harvest.grade, 'value') else str(harvest.grade)
        if grade_str == "GRADE_1_EXPORT":
            actions.append("توجيه للحاويات المبردة للتصدير")
        elif grade_str == "GRADE_2_LOCAL":
            actions.append("توجيه للأسواق المحلية")
        elif grade_str == "GRADE_3_PROCESSING":
            actions.append("توجيه لمصانع التجهيز الغذائي")
        elif grade_str == "GRADE_4_FODDER":
            actions.append("توجيه كأعلاف للثروة الحيوانية")
        elif grade_str == "WASTE_SMART_BIO":
            actions.append("توجيه لمحطات الطاقة الحيوية")
            
        if harvest.waste_for_smart_bio_kg > 0:  # type: ignore
            actions.append(f"{harvest.waste_for_smart_bio_kg} كجم مخلفات لمحطات الطاقة")
        if harvest.fodder_for_livestock_kg > 0:  # type: ignore
            actions.append(f"{harvest.fodder_for_livestock_kg} كجم أعلاف للماشية")
        return actions

    # ==========================================
    # 5. الأصول الحيوانية (Bio Assets)
    # ==========================================

    async def add_bio_cohort(
        self,
        zone_id: int,
        tenant_id: int,
        user_id: int,
        data: Dict[str, Any],
        idempotency_key: str
    ) -> BioAssetCohort:
        """إضافة مجموعة حيوانية جديدة (مع Idempotency)"""
        cached = await self._validate_idempotency(idempotency_key)
        if cached:
            return cast(BioAssetCohort, cached)

        zone = await self.repo.get_zone(zone_id)
        if not zone:
            raise NotFoundError("المنطقة غير موجودة")
        await self._check_tenant_access(tenant_id, zone.tenant_id)  # type: ignore

        cohort = await self.repo.create_bio_cohort(
            zone_id=zone_id,
            tenant_id=tenant_id,
            current_count_or_kg=data["initial_count_or_kg"],
            **data
        )

        await self._store_idempotency(idempotency_key, {"cohort_id": cohort.id})

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="BIO_COHORT_ADDED",
            resource_id=cohort.id,  # type: ignore
            details={"bio_type": cohort.bio_type.value, "zone_id": zone_id}
        )

        return cohort

    async def register_bio_yield(
        self,
        user_id: int,
        tenant_id: int,
        yield_data: Dict[str, Any],
        idempotency_key: str
    ) -> Dict[str, Any]:
        """تسجيل إنتاج حيواني جديد (مع Idempotency)"""
        cached = await self._validate_idempotency(idempotency_key)
        if cached:
            return cached

        cohort = await self.repo.get_bio_cohort(yield_data["cohort_id"])
        if not cohort:
            raise NotFoundError("المجموعة الحيوانية غير موجودة")
        await self._check_tenant_access(tenant_id, cohort.tenant_id)  # type: ignore

        # معاملة ذرية
        async with self.db.begin_nested():
            yield_record = await self.repo.create_bio_yield(
                tenant_id=tenant_id,
                idempotency_key=idempotency_key,
                **yield_data
            )

            # تحديث العدد الحالي (إذا كان نوع الإنتاج يتطلب ذلك)
            if yield_record.product_type in [BioProductType.MILK, BioProductType.EGG, BioProductType.MEAT]:
                # لا نحتاج لتحديث العدد في هذه الحالة
                pass

        # تحديد الإجراءات اللوجستية
        actions = self._get_bio_yield_actions(yield_record)

        result = {
            "yield_id": yield_record.id,
            "product_type": yield_record.product_type.value,
            "quantity": float(yield_record.quantity_unit),  # type: ignore
            "ai_logistics_actions": actions
        }

        await self._store_idempotency(idempotency_key, result)

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="BIO_YIELD_REGISTERED",
            resource_id=yield_record.id,  # type: ignore
            details={"product_type": yield_record.product_type.value}
        )

        return result

    def _get_bio_yield_actions(self, yield_record: BioProductYield) -> List[str]:
        """تحديد إجراءات لوجستية للإنتاج الحيواني"""
        actions = []
        product_type_str = yield_record.product_type.value if hasattr(yield_record.product_type, 'value') else str(yield_record.product_type)
        if product_type_str in ["MILK", "EGG", "MEAT"]:
            actions.append(f"توجيه {yield_record.quantity_unit} وحدة من {product_type_str} لسلاسل التبريد")
        elif product_type_str in ["VERMICOMPOST", "COMPOST_TEA"]:
            if yield_record.destination_farm_id:  # type: ignore
                actions.append(f"توجيه السماد العضوي للمزرعة رقم {yield_record.destination_farm_id}")
            else:
                actions.append("تخزين السماد العضوي في المستودعات")
                
        if yield_record.waste_for_smart_bio_kg > 0:  # type: ignore
            actions.append(f"{yield_record.waste_for_smart_bio_kg} كجم مخلفات عضوية لمحطات Smart Bio")
        return actions

    # ==========================================
    # 6. سلسلة التوريد (Supply Chain)
    # ==========================================

    async def add_traceability_stage(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> SupplyChainStage:
        """إضافة مرحلة جديدة في سلسلة التوريد"""
        stage = await self.repo.create_supply_chain_stage(
            tenant_id=tenant_id,
            operator_id=user_id,
            **data
        )
        # إضافة Hash بلوكشين وهمي للتتبع
        stage.blockchain_tx_hash = f"0xTRACE{stage.id}{uuid.uuid4().hex[:8]}"  # type: ignore
        await self.db.commit()
        await self.db.refresh(stage)

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="TRACEABILITY_STAGE_ADDED",
            resource_id=stage.id,  # type: ignore
            details={"traceable_type": data["traceable_type"], "traceable_id": data["traceable_id"]}
        )

        return stage

    async def get_traceability_stages(
        self,
        traceable_type: str,
        traceable_id: int,
        tenant_id: int
    ) -> List[SupplyChainStage]:
        """جلب سلسلة التوريد لكيان معين"""
        stages = await self.repo.get_supply_chain_stages(traceable_type, traceable_id)
        # التحقق من صلاحية المستأجر على جميع المراحل
        for stage in stages:
            await self._check_tenant_access(tenant_id, stage.tenant_id)  # type: ignore
        return stages

    async def generate_traceability_qr(
        self,
        tenant_id: int,
        traceable_type: str,
        traceable_id: int,
        user_id: int
    ) -> TraceabilityQR:
        """توليد QR للتتبع"""
        try:
            import qrcode  # type: ignore
            from io import BytesIO
        except ImportError:
            raise ValidationError("مكتبة QR غير مثبتة")

        qr_hash = uuid.uuid4().hex[:12]
        public_url = f"https://trace.eppne.com/{qr_hash}"

        qr = await self.repo.create_traceability_qr(
            tenant_id=tenant_id,
            traceable_type=traceable_type,
            traceable_id=traceable_id,
            qr_code=qr_hash,
            public_url=public_url,
            expires_at=datetime.utcnow() + timedelta(days=365)
        )

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="QR_GENERATED",
            resource_id=qr.id,  # type: ignore
            details={"traceable_type": traceable_type, "traceable_id": traceable_id}
        )

        return qr

    # ==========================================
    # 7. الشهادات (Certificates)
    # ==========================================

    async def issue_certificate(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> AgriculturalCertificate:
        """إصدار شهادة زراعية"""
        cert = await self.repo.create_certificate(
            tenant_id=tenant_id,
            created_by=user_id,
            **data
        )
        cert.certificate_nft_id = f"CERT-{cert.id}-{uuid.uuid4().hex[:8].upper()}"  # type: ignore
        await self.db.commit()
        await self.db.refresh(cert)

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="CERTIFICATE_ISSUED",
            resource_id=cert.id,  # type: ignore
            details={"type": data["certificate_type"], "entity_id": data["certified_entity_id"]}
        )

        await self.event_bus.publish("agritech.certificate.issued", {
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
    ) -> List[AgriculturalCertificate]:
        """جلب شهادات كيان معين"""
        certs = await self.repo.get_certificates_for_entity(entity_type, entity_id)
        # تصفية حسب المستأجر
        return [c for c in certs if c.tenant_id == tenant_id]  # type: ignore

    # ==========================================
    # 8. مستشعرات التربة (Soil Sensors)
    # ==========================================

    async def record_soil_data(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> SoilSensorReading:
        """تسجيل قراءة جديدة من مستشعر التربة"""
        # التحقق من المنطقة
        zone = await self.repo.get_zone(data["zone_id"])
        if not zone:  # type: ignore
            raise NotFoundError("المنطقة غير موجودة")
        await self._check_tenant_access(tenant_id, zone.tenant_id)  # type: ignore

        # تعقيم المدخلات
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

        reading = await self.repo.create_soil_reading(**sanitized_data)

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="SOIL_READING_RECORDED",
            resource_id=reading.id,  # type: ignore
            details={"zone_id": zone.id, "moisture": data.get("moisture_percent")}
        )

        # نشر حدث لتحليل البيانات (يمكن استبداله بـ Celery)
        await self.event_bus.publish("agritech.soil_reading.recorded", {
            "reading_id": reading.id,
            "zone_id": zone.id,
            "tenant_id": tenant_id
        })

        return reading

    async def get_recent_soil_readings(self, zone_id: int, tenant_id: int, limit: int = 100) -> List[SoilSensorReading]:
        """جلب قراءات المستشعرات لمنطقة محددة"""
        zone = await self.repo.get_zone(zone_id)
        if not zone:
            raise NotFoundError("المنطقة غير موجودة")
        await self._check_tenant_access(tenant_id, zone.tenant_id)  # type: ignore
        return await self.repo.get_recent_soil_readings(zone_id, limit)

    # ==========================================
    # 9. تنبيهات الطقس (Weather Alerts)
    # ==========================================

    async def create_weather_alert(
        self,
        tenant_id: int,
        user_id: int,
        data: Dict[str, Any]
    ) -> WeatherAlert:
        """إنشاء تنبيه طقس جديد"""
        sanitized_message = bleach.clean(data["message"], tags=[], strip=True)
        alert = await self.repo.create_weather_alert(
            tenant_id=tenant_id,
            alert_type=data["alert_type"],
            severity=data.get("severity", "WARNING"),
            location_gps=data.get("location_gps"),
            message=sanitized_message,
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            affected_farm_ids=data.get("affected_farm_ids", [])
        )

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="WEATHER_ALERT_CREATED",
            resource_id=alert.id,  # type: ignore
            details={"alert_type": alert.alert_type, "severity": alert.severity}
        )

        await self.event_bus.publish("agritech.weather_alert.created", {
            "alert_id": alert.id,
            "tenant_id": tenant_id,
            "severity": alert.severity
        })

        return alert

    async def get_weather_alerts(self, tenant_id: int) -> List[WeatherAlert]:
        """جلب تنبيهات الطقس النشطة"""
        return await self.repo.get_active_weather_alerts(tenant_id)