"""
جلسة `agritech-full-domain-build` (2026-09-04).
تقرير الجلسة: .claude/reports/agritech-full-domain-build-session-log.md

السياق: `agritech` كان دومين orphaned بالكامل (صفر router). هذا الاختبار
يتحقق حيًا (DB حقيقية، صفر mock) من كل مسار رئيسي بعد بناء router.py من
الصفر وتسجيله في main.py: farms, zones, crop cycles, harvest, bio assets,
traceability (+QR), certificates, soil sensors, weather alerts — بالإضافة
لتحقق عزل tenant_id على farms (عمود مباشر) وsoil readings (عبر join مع
FarmZone).
"""
import uuid
from decimal import Decimal
from datetime import datetime, timedelta

import pytest
from sqlalchemy import delete

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل agritech_router بنجاح
from app.core.database import AsyncSessionLocal

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.agritech.service import AgriTechService
from app.domains.agritech.models import (
    SmartFarm, FarmZone, CropCycle, HarvestBatch, BioAssetCohort,
    BioProductYield, SupplyChainStage, TraceabilityQR,
    AgriculturalCertificate, SoilSensorReading, WeatherAlert,
    FarmType, CropCategory, HarvestGrade, BioAssetType, BioProductType,
)

from app.domains.realestate.models import LandAsset, ZoningCategory, LegalStatus
from app.domains.sites.models import Site, SiteType

TENANT_ID = 1
OTHER_TENANT_ID = 2


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


async def _create_land_asset(db, tenant_id: int, owner_id: int) -> LandAsset:
    land = LandAsset(
        tenant_id=tenant_id,
        plot_number=f"REGTEST-PLOT-{_suffix()}",
        area_sqm=Decimal("5000"),
        gps_polygon={"type": "Polygon", "coordinates": []},
        zoning=ZoningCategory.AGRICULTURAL,
        legal_status=LegalStatus.REGISTERED,
        owner_id=owner_id,
    )
    db.add(land)
    await db.commit()
    await db.refresh(land)
    return land


@pytest.mark.asyncio
async def test_agritech_full_domain_flow_live(db):
    manager = await _create_user(db, "p_regtest_agritech_manager")
    land = await _create_land_asset(db, TENANT_ID, manager.id)

    site = Site(
        tenant_id=TENANT_ID, site_type=SiteType.FARM,
        name=f"REGTEST-AGRITECH-SITE-{_suffix()}",
    )
    db.add(site)
    await db.flush()

    service = AgriTechService(db, TENANT_ID)

    farm = zone = cycle = harvest_res = cohort = yield_res = None
    stage = qr = cert = reading = alert = None
    try:
        # ---------- 1. Farms ----------
        farm = await service.create_farm(manager.id, {
            "land_asset_id": land.id,
            "site_id": site.id,
            "name": f"REGTEST-FARM-{_suffix()}",
            "farm_type": FarmType.HYDROPONICS,
            "total_area_acres": Decimal("12.5"),
            "has_insurance": True,
        })
        assert farm.id is not None
        assert farm.tenant_id == TENANT_ID

        fetched = await service.get_farm(farm.id)
        assert fetched is not None and fetched.id == farm.id

        listed = await service.list_farms(limit=100)
        assert any(f.id == farm.id for f in listed["items"])

        # ---------- tenant isolation sample #1: عمود tenant_id مباشر ----------
        other_service = AgriTechService(db, OTHER_TENANT_ID)
        assert await other_service.get_farm(farm.id) is None
        other_listed = await other_service.list_farms(limit=100)
        assert not any(f.id == farm.id for f in other_listed["items"])

        # ---------- 2. Zones ----------
        zone = await service.add_farm_zone(farm.id, manager.id, {
            "zone_code": f"Z-{_suffix()}",
            "zone_type": "GREENHOUSE",
            "area_sqm": Decimal("500"),
            "soil_type": "LOAM",
            "irrigation_type": "DRIP",
        })
        assert zone.farm_id == farm.id

        zones_list = await service.list_farm_zones(farm.id)
        assert any(z.id == zone.id for z in zones_list["items"])

        # كيان مزرعة تابع لـtenant تاني: لازم يرجع NotFoundError مش تسريب zone
        from app.core.errors import NotFoundError
        with pytest.raises(NotFoundError):
            await other_service.list_farm_zones(farm.id)

        # ---------- 3. Crop Cycles ----------
        cycle = await service.start_crop_cycle(zone.id, manager.id, {
            "crop_name": "طماطم",
            "category": CropCategory.VEGETABLES,
            "planting_date": datetime.utcnow(),
            "expected_harvest_date": datetime.utcnow() + timedelta(days=90),
            "expected_yield_kg": Decimal("1000"),
        }, idempotency_key=f"REGTEST-CYCLE-{_suffix()}")
        assert cycle.zone_id == zone.id

        cycles_list = await service.list_crop_cycles(zone.id)
        assert any(c.id == cycle.id for c in cycles_list["items"])

        # ---------- 4. Harvest ----------
        harvest_res = await service.register_harvest(manager.id, {
            "cycle_id": cycle.id,
            "grade": HarvestGrade.GRADE_1_EXPORT,
            "quantity_kg": Decimal("800"),
        }, idempotency_key=f"REGTEST-HARVEST-{_suffix()}")
        assert harvest_res["id"] == harvest_res["harvest_id"]
        assert harvest_res["cycle_id"] == cycle.id
        assert harvest_res["shipment_tracking_number"] == harvest_res["tracking_number"]
        assert harvest_res["harvest_date"] is not None
        assert "توجيه للحاويات المبردة للتصدير" in harvest_res["ai_logistics_actions"]

        # ---------- 5. Bio Assets ----------
        cohort = await service.add_bio_cohort(zone.id, manager.id, {
            "bio_type": BioAssetType.POULTRY,
            "species_or_breed": "دجاج بياض",
            "initial_count_or_kg": Decimal("500"),
            "start_date": datetime.utcnow(),
        }, idempotency_key=f"REGTEST-COHORT-{_suffix()}")
        assert cohort.zone_id == zone.id

        yield_res = await service.register_bio_yield(manager.id, {
            "cohort_id": cohort.id,
            "product_type": BioProductType.EGG,
            "quantity_unit": Decimal("300"),
            "collection_date": datetime.utcnow(),
        }, idempotency_key=f"REGTEST-YIELD-{_suffix()}")
        assert yield_res["id"] == yield_res["yield_id"]
        assert yield_res["cohort_id"] == cohort.id
        assert yield_res["quantity_unit"] == yield_res["quantity"]
        assert yield_res["collection_date"] is not None

        # ---------- 6. Traceability ----------
        stage = await service.add_traceability_stage(manager.id, {
            "traceable_type": "HARVEST",
            "traceable_id": harvest_res["id"],
            "stage_name": "PACKAGING",
            "stage_order": 1,
        })
        assert stage.blockchain_tx_hash is not None

        stages_list = await service.get_traceability_stages("HARVEST", harvest_res["id"])
        assert any(s.id == stage.id for s in stages_list["items"])

        qr = await service.generate_traceability_qr("HARVEST", harvest_res["id"], manager.id)
        assert qr.qr_code is not None and qr.public_url is not None

        # ---------- 7. Certificates ----------
        cert = await service.issue_certificate(manager.id, {
            "certificate_type": "ORGANIC",
            "certificate_name": "شهادة عضوية",
            "issuing_body": "الهيئة المصرية للزراعة العضوية",
            "certified_entity_type": "FARM",
            "certified_entity_id": farm.id,
            "issue_date": datetime.utcnow(),
            "expiry_date": datetime.utcnow() + timedelta(days=365),
        })
        assert cert.certificate_nft_id is not None

        certs_list = await service.get_entity_certificates("FARM", farm.id)
        assert any(c.id == cert.id for c in certs_list["items"])

        # ---------- 8. Soil Sensors ----------
        reading = await service.record_soil_data(manager.id, {
            "zone_id": zone.id,
            "sensor_device_id": f"SENSOR-{_suffix()}",
            "moisture_percent": Decimal("45.5"),
            "temperature_celsius": Decimal("28.0"),
            "ph_level": Decimal("6.5"),
            "nitrogen_ppm": Decimal("30"),
            "recorded_at": datetime.utcnow(),
        })
        assert reading.zone_id == zone.id

        readings_list = await service.get_recent_soil_readings(zone.id, limit=10)
        assert any(r.id == reading.id for r in readings_list["items"])

        # ---------- tenant isolation sample #2: عبر join مع FarmZone ----------
        with pytest.raises(NotFoundError):
            await other_service.get_recent_soil_readings(zone.id, limit=10)

        # ---------- 9. Weather Alerts ----------
        alert = await service.create_weather_alert(manager.id, {
            "alert_type": "HEATWAVE",
            "severity": "WARNING",
            "message": "موجة حر متوقعة",
            "start_time": datetime.utcnow(),
            "affected_farm_ids": [farm.id],
        })
        assert alert.tenant_id == TENANT_ID

        alerts_list = await service.get_weather_alerts()
        assert any(a.id == alert.id for a in alerts_list)
        assert not any(a.id == alert.id for a in await other_service.get_weather_alerts())

    finally:
        async with AsyncSessionLocal() as cleanup_db:
            if alert:
                await cleanup_db.execute(delete(WeatherAlert).where(WeatherAlert.id == alert.id))
            if reading:
                await cleanup_db.execute(delete(SoilSensorReading).where(SoilSensorReading.id == reading.id))
            if cert:
                await cleanup_db.execute(delete(AgriculturalCertificate).where(AgriculturalCertificate.id == cert.id))
            if qr:
                await cleanup_db.execute(delete(TraceabilityQR).where(TraceabilityQR.id == qr.id))
            if stage:
                await cleanup_db.execute(delete(SupplyChainStage).where(SupplyChainStage.id == stage.id))
            if yield_res:
                await cleanup_db.execute(delete(BioProductYield).where(BioProductYield.id == yield_res["id"]))
            if cohort:
                await cleanup_db.execute(delete(BioAssetCohort).where(BioAssetCohort.id == cohort.id))
            if harvest_res:
                await cleanup_db.execute(delete(HarvestBatch).where(HarvestBatch.id == harvest_res["id"]))
            if cycle:
                await cleanup_db.execute(delete(CropCycle).where(CropCycle.id == cycle.id))
            if zone:
                await cleanup_db.execute(delete(FarmZone).where(FarmZone.id == zone.id))
            if farm:
                await cleanup_db.execute(delete(SmartFarm).where(SmartFarm.id == farm.id))
            await cleanup_db.execute(delete(Site).where(Site.id == site.id))
            await cleanup_db.execute(delete(LandAsset).where(LandAsset.id == land.id))
            await cleanup_db.execute(delete(User).where(User.id == manager.id))
            await cleanup_db.commit()
