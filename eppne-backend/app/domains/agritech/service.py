# app/domains/agritech/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update  # ✅ إضافة import update
from decimal import Decimal
from datetime import datetime, timedelta
import uuid
import bleach
from typing import Optional, List, Dict, Any, cast
from fastapi import HTTPException

from app.domains.agritech.repository import AgriTechRepository
from app.domains.finance.service import FinanceService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, ValidationError
from app.core.idempotency import get_idempotency_result, store_idempotency_result
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


class AgriTechService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = AgriTechRepository(db)
        self.finance = FinanceService(db, tenant_id)
        # ✅ معالجة نوع redis_client بشكل آمن
        redis = redis_client.client if hasattr(redis_client, 'client') else redis_client
        self.event_bus = EventBus(redis)

    # ==========================================
    # دوال مساعدة
    # ==========================================

    async def _check_tenant_access(self, resource_tenant_id: int):
        if self.tenant_id != resource_tenant_id:
            raise PermissionDeniedError("ليس لديك صلاحية الوصول لهذا المورد")

    async def _validate_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        if idempotency_key:
            cache_key = f"idempotency:{self.tenant_id}:{idempotency_key}"
            cached = await get_idempotency_result(cache_key)
            if cached is not None:
                return cached
        return None

    async def _store_idempotency(self, idempotency_key: str, result: Dict[str, Any]):
        if idempotency_key:
            cache_key = f"idempotency:{self.tenant_id}:{idempotency_key}"
            await store_idempotency_result(cache_key, result)

    # ==========================================
    # 1. المزارع (Farms)
    # ==========================================

    async def create_farm(self, user_id: int, data: Dict[str, Any]) -> SmartFarm:
        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)

        farm = await self.repo.create_farm(
            tenant_id=self.tenant_id,
            manager_id=user_id,
            land_asset_id=data["land_asset_id"],
            name=sanitized_name,
            farm_type=data["farm_type"],
            total_area_acres=data["total_area_acres"],
            has_insurance=data.get("has_insurance", False)
        )

        await audit_log(
            user_id=user_id,
            action="FARM_CREATED",
            details={
                "tenant_id": self.tenant_id,
                "farm_id": farm.id,
                "name": farm.name,
                "type": farm.farm_type.value
            }
        )

        await self.event_bus.publish("agritech.farm.created", {
            "farm_id": farm.id,
            "tenant_id": self.tenant_id,
            "manager_id": user_id,
            "name": farm.name
        })

        return farm

    async def list_farms(
        self,
        farm_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        result = await self.repo.list_farms(
            tenant_id=self.tenant_id,
            farm_type=farm_type,
            skip=skip,
            limit=limit
        )
        return {
            "items": result.data,
            "total": result.total,
            "skip": result.skip,
            "limit": result.limit
        }

    async def get_farm(self, farm_id: int) -> Optional[SmartFarm]:
        farm = await self.repo.get_farm(farm_id, self.tenant_id)
        if farm:
            await self._check_tenant_access(cast(int, farm.tenant_id))
        return farm

    # ==========================================
    # 2. المناطق (Zones)
    # ==========================================

    async def add_farm_zone(self, farm_id: int, user_id: int, data: Dict[str, Any]) -> FarmZone:
        farm = await self.repo.get_farm(farm_id, self.tenant_id)
        if not farm:
            raise NotFoundError("المزرعة غير موجودة")
        await self._check_tenant_access(cast(int, farm.tenant_id))

        zone = await self.repo.create_zone(
            farm_id=farm_id,
            tenant_id=self.tenant_id,
            **data
        )

        await audit_log(
            user_id=user_id,
            action="ZONE_ADDED",
            details={
                "tenant_id": self.tenant_id,
                "zone_id": zone.id,
                "zone_code": zone.zone_code,
                "farm_id": farm_id
            }
        )

        return zone

    async def list_farm_zones(self, farm_id: int) -> Dict[str, Any]:
        farm = await self.repo.get_farm(farm_id, self.tenant_id)
        if not farm:
            raise NotFoundError("المزرعة غير موجودة")
        await self._check_tenant_access(cast(int, farm.tenant_id))
        result = await self.repo.list_zones(farm_id, self.tenant_id)
        return {
            "items": result.data,
            "total": result.total,
            "skip": result.skip,
            "limit": result.limit
        }

    # ==========================================
    # 3. الدورات الزراعية (Crop Cycles)
    # ==========================================

    async def start_crop_cycle(
        self,
        zone_id: int,
        user_id: int,
        data: Dict[str, Any],
        idempotency_key: str
    ) -> CropCycle:
        cached = await self._validate_idempotency(idempotency_key)
        if cached:
            cycle_id = cached.get("cycle_id")
            if cycle_id:
                cycle = await self.repo.get_crop_cycle(cycle_id, self.tenant_id)
                if cycle:
                    return cycle
            raise ValidationError("Idempotency record exists but cycle not found.")

        zone = await self.repo.get_zone(zone_id, self.tenant_id)
        if not zone:
            raise NotFoundError("المنطقة غير موجودة")
        await self._check_tenant_access(cast(int, zone.tenant_id))

        cycle = await self.repo.create_crop_cycle(
            zone_id=zone_id,
            tenant_id=self.tenant_id,
            idempotency_key=idempotency_key,
            **data
        )

        await self._store_idempotency(idempotency_key, {"cycle_id": cycle.id})

        await audit_log(
            user_id=user_id,
            action="CROP_CYCLE_STARTED",
            details={
                "tenant_id": self.tenant_id,
                "cycle_id": cycle.id,
                "crop_name": cycle.crop_name,
                "zone_id": zone_id
            }
        )

        return cycle

    async def list_crop_cycles(self, zone_id: int) -> Dict[str, Any]:
        zone = await self.repo.get_zone(zone_id, self.tenant_id)
        if not zone:
            raise NotFoundError("المنطقة غير موجودة")
        await self._check_tenant_access(cast(int, zone.tenant_id))
        result = await self.repo.list_crop_cycles(zone_id, self.tenant_id)
        return {
            "items": result.data,
            "total": result.total,
            "skip": result.skip,
            "limit": result.limit
        }

    # ==========================================
    # 4. الحصاد (Harvest)
    # ==========================================

    async def register_harvest(
        self,
        user_id: int,
        data: Dict[str, Any],
        idempotency_key: str
    ) -> Dict[str, Any]:
        cached = await self._validate_idempotency(idempotency_key)
        if cached:
            return cached

        cycle = await self.repo.get_crop_cycle(data["cycle_id"], self.tenant_id)
        if not cycle:
            raise NotFoundError("الدورة الزراعية غير موجودة")
        await self._check_tenant_access(cast(int, cycle.tenant_id))

        sanitized_data = {
            "cycle_id": data["cycle_id"],
            "grade": data["grade"],
            "quantity_kg": data["quantity_kg"],
            "waste_for_smart_bio_kg": data.get("waste_for_smart_bio_kg", Decimal(0)),
            "fodder_for_livestock_kg": data.get("fodder_for_livestock_kg", Decimal(0)),
            "destination_facility_id": data.get("destination_facility_id"),
            "shipment_tracking_number": f"SHIP-{uuid.uuid4().hex[:8].upper()}"
        }

        async with self.db.begin_nested():
            harvest = await self.repo.create_harvest(
                tenant_id=self.tenant_id,
                idempotency_key=idempotency_key,
                **sanitized_data
            )

        ai_logistics_actions = self._get_harvest_actions(harvest)

        await audit_log(
            user_id=user_id,
            action="HARVEST_REGISTERED",
            details={
                "tenant_id": self.tenant_id,
                "harvest_id": harvest.id,
                "cycle_id": cycle.id,
                "quantity": float(Decimal(str(harvest.quantity_kg)))
            }
        )

        await self.event_bus.publish("agritech.harvest.registered", {
            "harvest_id": harvest.id,
            "cycle_id": cycle.id,
            "tenant_id": self.tenant_id,
            "quantity": float(Decimal(str(harvest.quantity_kg)))
        })

        result = {
            "harvest_id": harvest.id,
            "grade": harvest.grade.value,
            "quantity_kg": float(Decimal(str(harvest.quantity_kg))),
            "tracking_number": harvest.shipment_tracking_number,
            "ai_logistics_actions": ai_logistics_actions
        }
        await self._store_idempotency(idempotency_key, result)

        return result

    def _get_harvest_actions(self, harvest: HarvestBatch) -> List[str]:
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
        if cast(Decimal, harvest.waste_for_smart_bio_kg) > 0:
            actions.append(f"{harvest.waste_for_smart_bio_kg} كجم مخلفات لمحطات الطاقة")
        if cast(Decimal, harvest.fodder_for_livestock_kg) > 0:
            actions.append(f"{harvest.fodder_for_livestock_kg} كجم أعلاف للماشية")
        return actions

    # ==========================================
    # 5. الأصول الحيوانية (Bio Assets)
    # ==========================================

    async def add_bio_cohort(
        self,
        zone_id: int,
        user_id: int,
        data: Dict[str, Any],
        idempotency_key: str
    ) -> BioAssetCohort:
        cached = await self._validate_idempotency(idempotency_key)
        if cached:
            cohort_id = cached.get("cohort_id")
            if cohort_id:
                cohort = await self.repo.get_bio_cohort(cohort_id, self.tenant_id)
                if cohort:
                    return cohort
            raise ValidationError("Idempotency record exists but cohort not found.")

        zone = await self.repo.get_zone(zone_id, self.tenant_id)
        if not zone:
            raise NotFoundError("المنطقة غير موجودة")
        await self._check_tenant_access(cast(int, zone.tenant_id))

        cohort = await self.repo.create_bio_cohort(
            zone_id=zone_id,
            tenant_id=self.tenant_id,
            current_count_or_kg=data["initial_count_or_kg"],
            **data
        )

        await self._store_idempotency(idempotency_key, {"cohort_id": cohort.id})

        await audit_log(
            user_id=user_id,
            action="BIO_COHORT_ADDED",
            details={
                "tenant_id": self.tenant_id,
                "cohort_id": cohort.id,
                "bio_type": cohort.bio_type.value,
                "zone_id": zone_id
            }
        )

        return cohort

    async def register_bio_yield(
        self,
        user_id: int,
        yield_data: Dict[str, Any],
        idempotency_key: str
    ) -> Dict[str, Any]:
        cached = await self._validate_idempotency(idempotency_key)
        if cached:
            return cached

        cohort = await self.repo.get_bio_cohort(yield_data["cohort_id"], self.tenant_id)
        if not cohort:
            raise NotFoundError("المجموعة الحيوانية غير موجودة")
        await self._check_tenant_access(cast(int, cohort.tenant_id))

        async with self.db.begin_nested():
            yield_record = await self.repo.create_bio_yield(
                tenant_id=self.tenant_id,
                idempotency_key=idempotency_key,
                **yield_data
            )

        actions = self._get_bio_yield_actions(yield_record)

        result = {
            "yield_id": yield_record.id,
            "product_type": yield_record.product_type.value,
            "quantity": float(Decimal(str(yield_record.quantity_unit))),
            "ai_logistics_actions": actions
        }

        await self._store_idempotency(idempotency_key, result)

        await audit_log(
            user_id=user_id,
            action="BIO_YIELD_REGISTERED",
            details={
                "tenant_id": self.tenant_id,
                "yield_id": yield_record.id,
                "product_type": yield_record.product_type.value
            }
        )

        return result

    def _get_bio_yield_actions(self, yield_record: BioProductYield) -> List[str]:
        actions = []
        product_type_str = yield_record.product_type.value if hasattr(yield_record.product_type, 'value') else str(yield_record.product_type)
        if product_type_str in ["MILK", "EGG", "MEAT"]:
            actions.append(f"توجيه {yield_record.quantity_unit} وحدة من {product_type_str} لسلاسل التبريد")
        elif product_type_str in ["VERMICOMPOST", "COMPOST_TEA"]:
            if yield_record.destination_farm_id:
                actions.append(f"توجيه السماد العضوي للمزرعة رقم {yield_record.destination_farm_id}")
            else:
                actions.append("تخزين السماد العضوي في المستودعات")
        if cast(Decimal, yield_record.waste_for_smart_bio_kg) > 0:
            actions.append(f"{yield_record.waste_for_smart_bio_kg} كجم مخلفات عضوية لمحطات Smart Bio")
        return actions

    # ==========================================
    # 6. سلسلة التوريد (Supply Chain)
    # ==========================================

    async def add_traceability_stage(
        self,
        user_id: int,
        data: Dict[str, Any]
    ) -> SupplyChainStage:
        stage = await self.repo.create_supply_chain_stage(
            tenant_id=self.tenant_id,
            operator_id=user_id,
            **data
        )
        # ✅ استخدام update مع استيراد update
        await self.db.execute(
            update(SupplyChainStage)
            .where(SupplyChainStage.id == stage.id)
            .values(blockchain_tx_hash=f"0xTRACE{stage.id}{uuid.uuid4().hex[:8]}")
        )
        await self.db.commit()
        await self.db.refresh(stage)

        await audit_log(
            user_id=user_id,
            action="TRACEABILITY_STAGE_ADDED",
            details={
                "tenant_id": self.tenant_id,
                "stage_id": stage.id,
                "traceable_type": data["traceable_type"],
                "traceable_id": data["traceable_id"]
            }
        )

        return stage

    async def get_traceability_stages(
        self,
        traceable_type: str,
        traceable_id: int
    ) -> Dict[str, Any]:
        result = await self.repo.get_supply_chain_stages(
            traceable_type=traceable_type,
            traceable_id=traceable_id,
            tenant_id=self.tenant_id
        )
        return {
            "items": result.data,
            "total": result.total,
            "skip": result.skip,
            "limit": result.limit
        }

    async def generate_traceability_qr(
        self,
        traceable_type: str,
        traceable_id: int,
        user_id: int
    ) -> TraceabilityQR:
        try:
            import qrcode
        except ImportError:
            raise ValidationError("مكتبة QR غير مثبتة، يرجى تثبيت qrcode باستخدام: pip install qrcode[pil]")

        qr_hash = uuid.uuid4().hex[:12]
        public_url = f"https://trace.eppne.com/{qr_hash}"

        qr = await self.repo.create_traceability_qr(
            tenant_id=self.tenant_id,
            traceable_type=traceable_type,
            traceable_id=traceable_id,
            qr_code=qr_hash,
            public_url=public_url,
            expires_at=datetime.utcnow() + timedelta(days=365)
        )

        await audit_log(
            user_id=user_id,
            action="QR_GENERATED",
            details={
                "tenant_id": self.tenant_id,
                "qr_id": qr.id,
                "traceable_type": traceable_type,
                "traceable_id": traceable_id
            }
        )

        return qr

    # ==========================================
    # 7. الشهادات (Certificates)
    # ==========================================

    async def issue_certificate(
        self,
        user_id: int,
        data: Dict[str, Any]
    ) -> AgriculturalCertificate:
        cert = await self.repo.create_certificate(
            tenant_id=self.tenant_id,
            created_by=user_id,
            **data
        )
        # ✅ استخدام update
        await self.db.execute(
            update(AgriculturalCertificate)
            .where(AgriculturalCertificate.id == cert.id)
            .values(certificate_nft_id=f"CERT-{cert.id}-{uuid.uuid4().hex[:8].upper()}")
        )
        await self.db.commit()
        await self.db.refresh(cert)

        await audit_log(
            user_id=user_id,
            action="CERTIFICATE_ISSUED",
            details={
                "tenant_id": self.tenant_id,
                "certificate_id": cert.id,
                "type": data["certificate_type"],
                "entity_id": data["certified_entity_id"]
            }
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
        entity_id: int
    ) -> Dict[str, Any]:
        result = await self.repo.get_certificates_for_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            tenant_id=self.tenant_id
        )
        return {
            "items": result.data,
            "total": result.total,
            "skip": result.skip,
            "limit": result.limit
        }

    # ==========================================
    # 8. مستشعرات التربة (Soil Sensors)
    # ==========================================

    async def record_soil_data(
        self,
        user_id: int,
        data: Dict[str, Any]
    ) -> SoilSensorReading:
        zone = await self.repo.get_zone(data["zone_id"], self.tenant_id)
        if not zone:
            raise NotFoundError("المنطقة غير موجودة")
        await self._check_tenant_access(cast(int, zone.tenant_id))

        sanitized_data = {
            "tenant_id": self.tenant_id,
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
            action="SOIL_READING_RECORDED",
            details={
                "tenant_id": self.tenant_id,
                "reading_id": reading.id,
                "zone_id": zone.id,
                "moisture": data.get("moisture_percent")
            }
        )

        await self.event_bus.publish("agritech.soil_reading.recorded", {
            "reading_id": reading.id,
            "zone_id": zone.id,
            "tenant_id": self.tenant_id
        })

        return reading

    async def get_recent_soil_readings(
        self,
        zone_id: int,
        limit: int = 100
    ) -> Dict[str, Any]:
        zone = await self.repo.get_zone(zone_id, self.tenant_id)
        if not zone:
            raise NotFoundError("المنطقة غير موجودة")
        await self._check_tenant_access(cast(int, zone.tenant_id))
        result = await self.repo.get_recent_soil_readings(zone_id, self.tenant_id, limit)
        return {
            "items": result.data,
            "total": result.total,
            "skip": result.skip,
            "limit": result.limit
        }

    # ==========================================
    # 9. تنبيهات الطقس (Weather Alerts)
    # ==========================================

    async def create_weather_alert(
        self,
        user_id: int,
        data: Dict[str, Any]
    ) -> WeatherAlert:
        sanitized_message = bleach.clean(data["message"], tags=[], strip=True)
        alert = await self.repo.create_weather_alert(
            tenant_id=self.tenant_id,
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
            action="WEATHER_ALERT_CREATED",
            details={
                "tenant_id": self.tenant_id,
                "alert_id": alert.id,
                "alert_type": alert.alert_type,
                "severity": alert.severity
            }
        )

        await self.event_bus.publish("agritech.weather_alert.created", {
            "alert_id": alert.id,
            "tenant_id": self.tenant_id,
            "severity": alert.severity
        })

        return alert

    async def get_weather_alerts(self) -> List[WeatherAlert]:
        return await self.repo.get_active_weather_alerts(self.tenant_id)