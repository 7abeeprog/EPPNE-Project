# app/domains/agritech/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from typing import Optional, List, cast
from datetime import datetime
from app.domains.agritech.models import *
from app.core.errors import NotFoundError
from decimal import Decimal
from app.core.pagination import PaginatedResponse


class AgriTechRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- Farms ----------
    async def create_farm(self, **kwargs) -> SmartFarm:
        farm = SmartFarm(**kwargs)
        self.db.add(farm)
        await self.db.commit()
        await self.db.refresh(farm)
        return farm

    async def get_farm(self, farm_id: int, tenant_id: int) -> Optional[SmartFarm]:
        result = await self.db.execute(
            select(SmartFarm).where(
                and_(SmartFarm.id == farm_id, SmartFarm.tenant_id == tenant_id, SmartFarm.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def list_farms(
        self,
        tenant_id: int,
        farm_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> PaginatedResponse[SmartFarm]:
        query = select(SmartFarm).where(
            and_(SmartFarm.tenant_id == tenant_id, SmartFarm.is_deleted == False)
        )
        if farm_type:
            query = query.where(SmartFarm.farm_type == farm_type)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return PaginatedResponse[SmartFarm](
            data=items,
            total=total,
            skip=skip,
            limit=limit
        )

    # ---------- Zones ----------
    async def create_zone(self, **kwargs) -> FarmZone:
        zone = FarmZone(**kwargs)
        self.db.add(zone)
        await self.db.commit()
        await self.db.refresh(zone)
        return zone

    async def get_zone(self, zone_id: int, tenant_id: int) -> Optional[FarmZone]:
        result = await self.db.execute(
            select(FarmZone).where(and_(FarmZone.id == zone_id, FarmZone.tenant_id == tenant_id))
        )
        return result.scalar_one_or_none()

    async def list_zones(self, farm_id: int, tenant_id: int) -> PaginatedResponse[FarmZone]:
        query = select(FarmZone).where(FarmZone.farm_id == farm_id)
        query = query.join(SmartFarm, SmartFarm.id == FarmZone.farm_id).where(SmartFarm.tenant_id == tenant_id)
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        query = query.offset(0).limit(1000)
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return PaginatedResponse[FarmZone](
            data=items,
            total=total,
            skip=0,
            limit=1000
        )

    # ---------- Crop Cycles ----------
    async def create_crop_cycle(self, **kwargs) -> CropCycle:
        cycle = CropCycle(**kwargs)
        self.db.add(cycle)
        await self.db.commit()
        await self.db.refresh(cycle)
        return cycle

    async def get_crop_cycle(self, cycle_id: int, tenant_id: int) -> Optional[CropCycle]:
        result = await self.db.execute(
            select(CropCycle).where(and_(CropCycle.id == cycle_id, CropCycle.tenant_id == tenant_id))
        )
        return result.scalar_one_or_none()

    async def list_crop_cycles(self, zone_id: int, tenant_id: int) -> PaginatedResponse[CropCycle]:
        query = select(CropCycle).where(CropCycle.zone_id == zone_id)
        query = query.join(FarmZone, FarmZone.id == CropCycle.zone_id).where(FarmZone.tenant_id == tenant_id)
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        query = query.offset(0).limit(1000)
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return PaginatedResponse[CropCycle](
            data=items,
            total=total,
            skip=0,
            limit=1000
        )

    async def create_harvest(self, **kwargs) -> HarvestBatch:
        harvest = HarvestBatch(**kwargs)
        self.db.add(harvest)
        await self.db.flush()
        await self.db.refresh(harvest)
        return harvest

    # ---------- Bio Assets ----------
    async def create_bio_cohort(self, **kwargs) -> BioAssetCohort:
        cohort = BioAssetCohort(**kwargs)
        self.db.add(cohort)
        await self.db.commit()
        await self.db.refresh(cohort)
        return cohort

    async def get_bio_cohort(self, cohort_id: int, tenant_id: int) -> Optional[BioAssetCohort]:
        result = await self.db.execute(
            select(BioAssetCohort).where(and_(BioAssetCohort.id == cohort_id, BioAssetCohort.tenant_id == tenant_id))
        )
        return result.scalar_one_or_none()

    async def update_bio_cohort_count(self, cohort_id: int, new_count: Decimal) -> BioAssetCohort:
        await self.db.execute(update(BioAssetCohort).where(BioAssetCohort.id == cohort_id).values(current_count_or_kg=new_count))
        await self.db.commit()
        return await self.get_bio_cohort(cohort_id)

    async def create_bio_yield(self, **kwargs) -> BioProductYield:
        yield_record = BioProductYield(**kwargs)
        self.db.add(yield_record)
        await self.db.flush()
        await self.db.refresh(yield_record)
        return yield_record

    # ---------- Supply Chain ----------
    async def create_supply_chain_stage(self, **kwargs) -> SupplyChainStage:
        stage = SupplyChainStage(**kwargs)
        self.db.add(stage)
        await self.db.commit()
        await self.db.refresh(stage)
        return stage

    async def get_supply_chain_stages(
        self,
        traceable_type: str,
        traceable_id: int,
        tenant_id: int
    ) -> PaginatedResponse[SupplyChainStage]:
        query = select(SupplyChainStage).where(
            and_(
                SupplyChainStage.traceable_type == traceable_type,
                SupplyChainStage.traceable_id == traceable_id,
                SupplyChainStage.tenant_id == tenant_id
            )
        ).order_by(SupplyChainStage.stage_order)
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        query = query.offset(0).limit(1000)
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return PaginatedResponse[SupplyChainStage](
            data=items,
            total=total,
            skip=0,
            limit=1000
        )

    async def create_traceability_qr(self, **kwargs) -> TraceabilityQR:
        qr = TraceabilityQR(**kwargs)
        self.db.add(qr)
        await self.db.commit()
        await self.db.refresh(qr)
        return qr

    # ---------- Certificates ----------
    async def create_certificate(self, **kwargs) -> AgriculturalCertificate:
        cert = AgriculturalCertificate(**kwargs)
        self.db.add(cert)
        await self.db.commit()
        await self.db.refresh(cert)
        return cert

    async def get_certificates_for_entity(
        self,
        entity_type: str,
        entity_id: int,
        tenant_id: int
    ) -> PaginatedResponse[AgriculturalCertificate]:
        query = select(AgriculturalCertificate).where(
            and_(
                AgriculturalCertificate.certified_entity_type == entity_type,
                AgriculturalCertificate.certified_entity_id == entity_id,
                AgriculturalCertificate.tenant_id == tenant_id,
                AgriculturalCertificate.is_deleted == False
            )
        )
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        query = query.offset(0).limit(1000)
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return PaginatedResponse[AgriculturalCertificate](
            data=items,
            total=total,
            skip=0,
            limit=1000
        )

    # ---------- IoT Sensors ----------
    async def get_soil_reading(self, reading_id: int, tenant_id: int) -> Optional[SoilSensorReading]:
        result = await self.db.execute(
            select(SoilSensorReading).where(and_(SoilSensorReading.id == reading_id, SoilSensorReading.tenant_id == tenant_id))
        )
        return result.scalar_one_or_none()

    async def create_soil_reading(self, **kwargs) -> SoilSensorReading:
        reading = SoilSensorReading(**kwargs)
        self.db.add(reading)
        await self.db.commit()
        await self.db.refresh(reading)
        return reading

    async def get_recent_soil_readings(
        self,
        zone_id: int,
        tenant_id: int,
        limit: int = 100
    ) -> PaginatedResponse[SoilSensorReading]:
        query = select(SoilSensorReading).where(SoilSensorReading.zone_id == zone_id)
        query = query.join(FarmZone, FarmZone.id == SoilSensorReading.zone_id).where(FarmZone.tenant_id == tenant_id)
        query = query.order_by(SoilSensorReading.recorded_at.desc()).limit(limit)
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return PaginatedResponse[SoilSensorReading](
            data=items,
            total=total,
            skip=0,
            limit=limit
        )

    # ---------- Weather Alerts ----------
    async def create_weather_alert(self, **kwargs) -> WeatherAlert:
        alert = WeatherAlert(**kwargs)
        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def get_active_weather_alerts(self, tenant_id: int) -> List[WeatherAlert]:
        now = datetime.utcnow()
        result = await self.db.execute(
            select(WeatherAlert).where(
                and_(
                    WeatherAlert.tenant_id == tenant_id,
                    WeatherAlert.is_active == True,
                    WeatherAlert.start_time <= now,
                    (WeatherAlert.end_time >= now) | (WeatherAlert.end_time == None)
                )
            )
        )
        return list(result.scalars().all())