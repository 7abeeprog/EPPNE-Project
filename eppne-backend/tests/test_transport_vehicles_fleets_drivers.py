"""
regression test لجلسة `transport-vehicles-drivers-feature-build` (2026-09-04/05).
تقرير الجلسة: .claude/reports/transport-vehicles-drivers-session-log.md

السياق: الفرونت إند كان بيستدعي useVehicles/useCreateVehicle/useDeleteVehicle/
useAvailableVehicles/useDrivers بدون أي غطاء باك إند حقيقي — list/update/
delete للمركبات والأساطيل، وسرد للسائقين، كانت كلها غير موجودة إطلاقًا.
هذا الاختبار يتحقق حيًا (DB حقيقية) من الإضافات الجديدة في service.py
(transport + identity)، بما في ذلك عزل tenant_id، وحماية FK عند حذف مركبة
لها تاريخ رحلات (hard delete)، والحذف الناعم للأسطول (soft delete).
"""
import uuid
from decimal import Decimal
from datetime import datetime, timedelta

import pytest
from sqlalchemy import delete, select, update

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.core.errors import NotFoundError, ValidationError

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.saas.models import ServiceCatalog, ServicePlan, TenantSubscription, TenantServiceAccess

from app.domains.transport.service import TransportService
from app.domains.transport.repository import TransportRepository
from app.domains.transport.models import (
    TransportHub, Fleet, Vehicle, Route, Trip, TripCategory,
)

TENANT_ID = 1
# ملاحظة: academy_tenants في قاعدة بيانات الديف الحالية فيها بس id
# 1/15/16 — 2 مش موجود، فأي INSERT فعلي (مش مجرد query) بـtenant_id=2
# بيفشل بـForeignKeyViolationError. 15 موجود فعليًا ومستخدَم هنا فقط
# للحالات اللي بتحتاج صف حقيقي بتينانت مختلف (مش مجرد استعلام سلبي).
OTHER_TENANT_ID = 15


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str, tenant_id: int = TENANT_ID) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, tenant_id).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


async def _deactivate(db, user_id: int, tenant_id: int) -> None:
    await db.execute(update(User).where(User.id == user_id, User.tenant_id == tenant_id).values(is_active=False))
    await db.commit()


async def _grant_transport_saas_access(db, *tenant_ids: int) -> None:
    """يمنح تينانت (أو أكتر) وصول SaaS مؤقت لميزة 'transport'.

    saas_service_catalog في بيئة الديف الحالية صفر صف بـcode='transport'
    (اتنضّف عمدًا في نهاية جلسة transport-domain-full-build السابقة، §7.9
    من تقرير تلك الجلسة)، فأي service method بتنادي
    _check_saas_limits(tenant_id, "transport") بترجع PermissionDeniedError
    بدون المنحة دي — ده تأكيد حي على إن هذه الفجوة تمنع الدومين بالكامل من
    العمل فعليًا (مش خاص بمركبات/أساطيل/سائقين بس)، موثَّق في §6 من ملف
    الجلسة. بيانات throwaway بالكامل — بتتنضف بالكامل في finally كل test."""
    result = await db.execute(select(ServiceCatalog).where(ServiceCatalog.code == "transport"))
    catalog = result.scalar_one_or_none()
    if catalog is None:
        catalog = ServiceCatalog(name=f"REGTEST-Transport-{_suffix()}", code="transport", is_active=True)
        db.add(catalog)
        await db.flush()

    result = await db.execute(select(ServicePlan).where(ServicePlan.service_id == catalog.id))
    plan = result.scalars().first()
    if plan is None:
        plan = ServicePlan(
            service_id=catalog.id, name="REGTEST-Basic", code=f"regtest-basic-{_suffix()}",
            price_monthly=Decimal("0"), price_yearly=Decimal("0"),
        )
        db.add(plan)
        await db.flush()

    for tenant_id in tenant_ids:
        result = await db.execute(
            select(TenantServiceAccess).where(
                TenantServiceAccess.tenant_id == tenant_id, TenantServiceAccess.service_id == catalog.id
            )
        )
        if result.scalar_one_or_none() is None:
            db.add(TenantServiceAccess(tenant_id=tenant_id, service_id=catalog.id, access_level="BASIC", is_active=True))

        result = await db.execute(
            select(TenantSubscription).where(
                TenantSubscription.tenant_id == tenant_id, TenantSubscription.plan_id == plan.id,
                TenantSubscription.status.in_(["ACTIVE", "TRIAL"]),
            )
        )
        if result.scalar_one_or_none() is None:
            db.add(TenantSubscription(tenant_id=tenant_id, plan_id=plan.id, status="ACTIVE"))

    await db.commit()


async def _revoke_transport_saas_access() -> None:
    """ينضّف صفوف saas_service_catalog/plans/subscriptions/access الخاصة
    بـ'transport' بالكامل — نفس منهجية تنظيف saas_service_catalog الموثَّقة
    في §7.9 من جلسة transport-domain-full-build (صفر أثر باقٍ)."""
    async with AsyncSessionLocal() as cleanup_db:
        result = await cleanup_db.execute(select(ServiceCatalog).where(ServiceCatalog.code == "transport"))
        catalog = result.scalar_one_or_none()
        if catalog is None:
            return
        plan_ids_result = await cleanup_db.execute(select(ServicePlan.id).where(ServicePlan.service_id == catalog.id))
        plan_ids = [row[0] for row in plan_ids_result.fetchall()]
        if plan_ids:
            await cleanup_db.execute(delete(TenantSubscription).where(TenantSubscription.plan_id.in_(plan_ids)))
        await cleanup_db.execute(delete(TenantServiceAccess).where(TenantServiceAccess.service_id == catalog.id))
        await cleanup_db.execute(delete(ServicePlan).where(ServicePlan.service_id == catalog.id))
        await cleanup_db.execute(delete(ServiceCatalog).where(ServiceCatalog.id == catalog.id))
        await cleanup_db.commit()


@pytest.mark.asyncio
async def test_list_vehicles_tenant_isolation_and_fleet_filter(db):
    await _grant_transport_saas_access(db, TENANT_ID)
    repo = TransportRepository(db)
    suffix = _suffix()
    fleet = await repo.create_fleet(tenant_id=TENANT_ID, entity_id=1, name=f"REGTEST-FLEET-{suffix}")
    other_fleet = await repo.create_fleet(tenant_id=TENANT_ID, entity_id=1, name=f"REGTEST-FLEET2-{suffix}")
    vehicle1 = await repo.create_vehicle(
        tenant_id=TENANT_ID, fleet_id=fleet.id, license_plate=f"REGTEST-V1-{suffix}", vehicle_type="CAR",
    )
    vehicle2 = await repo.create_vehicle(
        tenant_id=TENANT_ID, fleet_id=other_fleet.id, license_plate=f"REGTEST-V2-{suffix}", vehicle_type="TRUCK",
    )
    other_tenant_vehicle = await repo.create_vehicle(
        tenant_id=OTHER_TENANT_ID, fleet_id=fleet.id, license_plate=f"REGTEST-V3-{suffix}", vehicle_type="CAR",
    )

    service = TransportService(db)
    try:
        result = await service.list_vehicles(TENANT_ID)
        ids = {v.id for v in result}
        assert vehicle1.id in ids
        assert vehicle2.id in ids
        assert other_tenant_vehicle.id not in ids

        filtered = await service.list_vehicles(TENANT_ID, fleet_id=fleet.id)
        filtered_ids = {v.id for v in filtered}
        assert vehicle1.id in filtered_ids
        assert vehicle2.id not in filtered_ids
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(Vehicle).where(Vehicle.id.in_([vehicle1.id, vehicle2.id, other_tenant_vehicle.id])))
            await cleanup_db.execute(delete(Fleet).where(Fleet.id.in_([fleet.id, other_fleet.id])))
            await cleanup_db.commit()
    await _revoke_transport_saas_access()


@pytest.mark.asyncio
async def test_update_vehicle_sanitizes_and_isolates_tenant(db):
    # OTHER_TENANT_ID لازم يتمنح هنا كمان — update_vehicle بتفحص SaaS الأول
    # قبل فحص وجود المركبة، فبدون المنحة هنرجّع PermissionDeniedError مش
    # NotFoundError المتوقع لعزل التينانت.
    await _grant_transport_saas_access(db, TENANT_ID, OTHER_TENANT_ID)
    repo = TransportRepository(db)
    suffix = _suffix()
    fleet = await repo.create_fleet(tenant_id=TENANT_ID, entity_id=1, name=f"REGTEST-FLEET-{suffix}")
    vehicle = await repo.create_vehicle(
        tenant_id=TENANT_ID, fleet_id=fleet.id, license_plate=f"REGTEST-{suffix}", vehicle_type="CAR",
    )

    service = TransportService(db)
    try:
        updated = await service.update_vehicle(
            TENANT_ID, vehicle.id, {"license_plate": f"<script>ABC-{suffix}</script>", "capacity_kg": Decimal("500")}
        )
        assert "<script>" not in updated.license_plate
        assert updated.capacity_kg == Decimal("500")

        with pytest.raises(NotFoundError):
            await service.update_vehicle(OTHER_TENANT_ID, vehicle.id, {"capacity_kg": Decimal("1")})
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(Vehicle).where(Vehicle.id == vehicle.id))
            await cleanup_db.execute(delete(Fleet).where(Fleet.id == fleet.id))
            await cleanup_db.commit()
    await _revoke_transport_saas_access()


@pytest.mark.asyncio
async def test_delete_vehicle_success_when_no_trip_history(db):
    repo = TransportRepository(db)
    suffix = _suffix()
    fleet = await repo.create_fleet(tenant_id=TENANT_ID, entity_id=1, name=f"REGTEST-FLEET-{suffix}")
    vehicle = await repo.create_vehicle(
        tenant_id=TENANT_ID, fleet_id=fleet.id, license_plate=f"REGTEST-{suffix}", vehicle_type="CAR",
    )

    service = TransportService(db)
    try:
        await service.delete_vehicle(TENANT_ID, vehicle.id)
        assert await repo.get_vehicle(vehicle.id, TENANT_ID) is None

        with pytest.raises(NotFoundError):
            await service.delete_vehicle(TENANT_ID, vehicle.id)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(Fleet).where(Fleet.id == fleet.id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_delete_vehicle_blocked_by_trip_history_fk(db):
    driver = await _create_user(db, "p_regtest_veh_driver")
    repo = TransportRepository(db)
    suffix = _suffix()
    hub1 = await repo.create_hub(tenant_id=TENANT_ID, name=f"REGTEST-HUB1-{suffix}", hub_type="LAND", gps_location={"lat": 0, "lng": 0})
    hub2 = await repo.create_hub(tenant_id=TENANT_ID, name=f"REGTEST-HUB2-{suffix}", hub_type="LAND", gps_location={"lat": 1, "lng": 1})
    fleet = await repo.create_fleet(tenant_id=TENANT_ID, entity_id=1, name=f"REGTEST-FLEET-{suffix}")
    vehicle = await repo.create_vehicle(tenant_id=TENANT_ID, fleet_id=fleet.id, license_plate=f"REGTEST-{suffix}", vehicle_type="CAR")
    route = await repo.create_route(
        tenant_id=TENANT_ID, name=f"REGTEST-ROUTE-{suffix}", start_hub_id=hub1.id, end_hub_id=hub2.id,
        waypoints=[], distance_km=Decimal("10"), estimated_duration_minutes=30,
    )
    trip = await repo.create_trip(
        tenant_id=TENANT_ID, route_id=route.id, vehicle_id=vehicle.id, driver_id=driver.id,
        trip_category=TripCategory.PASSENGER, scheduled_start=datetime.utcnow(), scheduled_end=datetime.utcnow() + timedelta(hours=1),
    )

    # نسخ الـids لمتغيرات int عادية *قبل* محاولة الحذف الفاشلة — بعد فشل
    # commit حقيقي (IntegrityError)، كائنات ORM القديمة (vehicle/trip/...)
    # بتتـexpire، وأي وصول لاحق لـ.id عليها (حتى من جوه session تانية تمامًا)
    # بيحاول lazy-reload عبر الـsession الأصلية المكسورة فيكسر بـ
    # MissingGreenlet — نفس الاكتشاف الموثَّق في
    # tests/test_realestate_insurance_savepoint.py:263-268. مش قضية "أي
    # session تستخدم" زي ما افتُرض في محاولة سابقة هنا — القضية في العنصر
    # (.id) نفسه.
    driver_id = driver.id
    hub_ids = [hub1.id, hub2.id]
    fleet_id = fleet.id
    vehicle_id = vehicle.id
    route_id = route.id
    trip_id = trip.id

    service = TransportService(db)
    try:
        with pytest.raises(ValidationError):
            await service.delete_vehicle(TENANT_ID, vehicle_id)

        async with AsyncSessionLocal() as verify_db:
            verify_repo = TransportRepository(verify_db)
            still_there = await verify_repo.get_vehicle(vehicle_id, TENANT_ID)
            assert still_there is not None
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(Trip).where(Trip.id == trip_id))
            await cleanup_db.execute(delete(Route).where(Route.id == route_id))
            await cleanup_db.execute(delete(Vehicle).where(Vehicle.id == vehicle_id))
            await cleanup_db.execute(delete(Fleet).where(Fleet.id == fleet_id))
            await cleanup_db.execute(delete(TransportHub).where(TransportHub.id.in_(hub_ids)))
            await cleanup_db.execute(delete(User).where(User.id == driver_id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_list_fleets_tenant_isolation(db):
    await _grant_transport_saas_access(db, TENANT_ID)
    repo = TransportRepository(db)
    suffix = _suffix()
    fleet = await repo.create_fleet(tenant_id=TENANT_ID, entity_id=1, name=f"REGTEST-FLEET-{suffix}")
    other_tenant_fleet = await repo.create_fleet(tenant_id=OTHER_TENANT_ID, entity_id=1, name=f"REGTEST-FLEET-OT-{suffix}")

    service = TransportService(db)
    try:
        result = await service.list_fleets(TENANT_ID)
        ids = {f.id for f in result}
        assert fleet.id in ids
        assert other_tenant_fleet.id not in ids
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(Fleet).where(Fleet.id.in_([fleet.id, other_tenant_fleet.id])))
            await cleanup_db.commit()
    await _revoke_transport_saas_access()


@pytest.mark.asyncio
async def test_update_and_soft_delete_fleet(db):
    await _grant_transport_saas_access(db, TENANT_ID)
    repo = TransportRepository(db)
    suffix = _suffix()
    fleet = await repo.create_fleet(tenant_id=TENANT_ID, entity_id=1, name=f"REGTEST-FLEET-{suffix}")

    service = TransportService(db)
    try:
        updated = await service.update_fleet(TENANT_ID, fleet.id, f"<b>New-{suffix}</b>")
        assert "<b>" not in updated.name

        await service.delete_fleet(TENANT_ID, fleet.id)
        remaining = await service.list_fleets(TENANT_ID)
        assert fleet.id not in {f.id for f in remaining}

        # soft delete — الصف لسه موجود فعليًا بس is_active=False
        raw = await repo.get_fleet(fleet.id, TENANT_ID)
        assert raw is not None
        assert raw.is_active is False

        with pytest.raises(NotFoundError):
            await service.delete_fleet(OTHER_TENANT_ID, fleet.id)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(Fleet).where(Fleet.id == fleet.id))
            await cleanup_db.commit()
    await _revoke_transport_saas_access()


@pytest.mark.asyncio
async def test_list_drivers_active_only_and_tenant_isolation(db):
    await _grant_transport_saas_access(db, TENANT_ID)
    active_user = await _create_user(db, "p_regtest_driver_active")
    inactive_user = await _create_user(db, "p_regtest_driver_inactive")
    other_tenant_user = await _create_user(db, "p_regtest_driver_other_tenant", tenant_id=OTHER_TENANT_ID)
    await _deactivate(db, inactive_user.id, TENANT_ID)

    service = TransportService(db)
    try:
        result = await service.list_drivers(TENANT_ID, skip=0, limit=1000)
        ids = {u.id for u in result}
        assert active_user.id in ids
        assert inactive_user.id not in ids
        assert other_tenant_user.id not in ids
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(User).where(User.id.in_([active_user.id, inactive_user.id, other_tenant_user.id])))
            await cleanup_db.commit()
    await _revoke_transport_saas_access()
