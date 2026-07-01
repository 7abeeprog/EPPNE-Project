from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from typing import Optional, List
from app.domains.agritech.models import *
from app.core.errors import NotFoundError
from decimal import Decimal

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

    async def get_farm(self, farm_id: int) -> Optional[SmartFarm]:
        result = await self.db.execute(select(SmartFarm).where(SmartFarm.id == farm_id))
        return result.scalar_one_or_none()

    async def list_farms(self, tenant_id: int, farm_type: Optional[str] = None, skip=0, limit=100):
        query = select(SmartFarm).where(SmartFarm.tenant_id == tenant_id, SmartFarm.is_deleted == False)
        if farm_type:
            query = query.where(SmartFarm.farm_type == farm_type)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    # ---------- Zones ----------
    async def create_zone(self, **kwargs) -> FarmZone:
        zone = FarmZone(**kwargs)
        self.db.add(zone)
        await self.db.commit()
        await self.db.refresh(zone)
        return zone

    async def list_zones(self, farm_id: int):
        result = await self.db.execute(select(FarmZone).where(FarmZone.farm_id == farm_id))
        return result.scalars().all()

    async def get_zone(self, zone_id: int) -> Optional[FarmZone]:
        result = await self.db.execute(select(FarmZone).where(FarmZone.id == zone_id))
        return result.scalar_one_or_none()

    # ---------- Crop Cycles ----------
    async def create_crop_cycle(self, **kwargs) -> CropCycle:
        cycle = CropCycle(**kwargs)
        self.db.add(cycle)
        await self.db.commit()
        await self.db.refresh(cycle)
        return cycle

    async def create_harvest(self, **kwargs) -> HarvestBatch:
        harvest = HarvestBatch(**kwargs)
        self.db.add(harvest)
        await self.db.commit()
        await self.db.refresh(harvest)
        return harvest

    async def list_harvests_by_cycle(self, cycle_id: int):
        result = await self.db.execute(select(HarvestBatch).where(HarvestBatch.cycle_id == cycle_id))
        return result.scalars().all()

    # ---------- Bio Assets ----------
    async def create_bio_cohort(self, **kwargs) -> BioAssetCohort:
        cohort = BioAssetCohort(**kwargs)
        self.db.add(cohort)
        await self.db.commit()
        await self.db.refresh(cohort)
        return cohort

    async def update_bio_cohort_count(self, cohort_id: int, new_count: Decimal) -> BioAssetCohort:
        await self.db.execute(update(BioAssetCohort).where(BioAssetCohort.id == cohort_id).values(current_count_or_kg=new_count))
        await self.db.commit()
        return await self.get_bio_cohort(cohort_id)

    async def get_bio_cohort(self, cohort_id: int) -> Optional[BioAssetCohort]:
        result = await self.db.execute(select(BioAssetCohort).where(BioAssetCohort.id == cohort_id))
        return result.scalar_one_or_none()

    async def create_bio_yield(self, **kwargs) -> BioProductYield:
        yield_record = BioProductYield(**kwargs)
        self.db.add(yield_record)
        await self.db.commit()
        await self.db.refresh(yield_record)
        return yield_record

    # ========== Supply Chain ==========
    async def create_supply_chain_stage(self, **kwargs) -> SupplyChainStage:
        stage = SupplyChainStage(**kwargs)
        self.db.add(stage)
        await self.db.commit()
        await self.db.refresh(stage)
        return stage

    async def get_supply_chain_stages(self, traceable_type: str, traceable_id: int) -> List[SupplyChainStage]:
        result = await self.db.execute(
            select(SupplyChainStage).where(
                SupplyChainStage.traceable_type == traceable_type,
                SupplyChainStage.traceable_id == traceable_id
            ).order_by(SupplyChainStage.stage_order)
        )
        return result.scalars().all()

    async def create_traceability_qr(self, **kwargs) -> TraceabilityQR:
        qr = TraceabilityQR(**kwargs)
        self.db.add(qr)
        await self.db.commit()
        await self.db.refresh(qr)
        return qr

    # ========== Certificates ==========
    async def create_certificate(self, **kwargs) -> AgriculturalCertificate:
        cert = AgriculturalCertificate(**kwargs)
        self.db.add(cert)
        await self.db.commit()
        await self.db.refresh(cert)
        return cert

    async def get_certificates_for_entity(self, entity_type: str, entity_id: int) -> List[AgriculturalCertificate]:
        result = await self.db.execute(
            select(AgriculturalCertificate).where(
                AgriculturalCertificate.certified_entity_type == entity_type,
                AgriculturalCertificate.certified_entity_id == entity_id,
                AgriculturalCertificate.is_deleted == False
            )
        )
        return result.scalars().all()

    # ========== IoT Sensors ==========
    async def create_soil_reading(self, **kwargs) -> SoilSensorReading:
        reading = SoilSensorReading(**kwargs)
        self.db.add(reading)
        await self.db.commit()
        await self.db.refresh(reading)
        return reading

    async def get_recent_soil_readings(self, zone_id: int, limit: int = 100) -> List[SoilSensorReading]:
        result = await self.db.execute(
            select(SoilSensorReading).where(SoilSensorReading.zone_id == zone_id)
            .order_by(SoilSensorReading.recorded_at.desc()).limit(limit)
        )
        return result.scalars().all()

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
                WeatherAlert.tenant_id == tenant_id,
                WeatherAlert.is_active == True,
                WeatherAlert.start_time <= now,
                (WeatherAlert.end_time >= now) | (WeatherAlert.end_time == None)
            )
        )
        return result.scalars().all()