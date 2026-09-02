"""
regression test لجلسة `frontend-category-b-phase2-remaining-domains` (2026-09-02).
تقرير الجلسة: .claude/reports/frontend-category-b-phase2-session-log.md

السياق: `TransportRepository` كانت تملك `get_route`, `get_vehicle`,
`list_bookings`, `assign_delivery_to_trip` جاهزة بالكامل بدون service
wrapper ولا router endpoint (رغم استخدام بعضها داخليًا في مسارات أخرى).
هذا الاختبار يتحقق حيًا (DB حقيقية) من الإضافات الأربع الجديدة في
service.py، بما في ذلك تحقق عزل tenant_id لـ get_route/get_vehicle،
وتحقق صلاحية المُرسِل لـ assign_delivery_to_trip.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timedelta

import pytest
from sqlalchemy import delete

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.core.errors import NotFoundError, PermissionDeniedError

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.transport.service import TransportService
from app.domains.transport.repository import TransportRepository
from app.domains.transport.models import (
    TransportHub, Fleet, Vehicle, Route, Trip, TripBooking, DeliveryTask,
    TripCategory,
)

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


async def _setup_trip(db, *, driver_id: int):
    repo = TransportRepository(db)
    suffix = _suffix()
    hub1 = await repo.create_hub(
        tenant_id=TENANT_ID, name=f"REGTEST-HUB1-{suffix}", hub_type="LAND",
        gps_location={"lat": 0, "lng": 0},
    )
    hub2 = await repo.create_hub(
        tenant_id=TENANT_ID, name=f"REGTEST-HUB2-{suffix}", hub_type="LAND",
        gps_location={"lat": 1, "lng": 1},
    )
    fleet = await repo.create_fleet(tenant_id=TENANT_ID, entity_id=1, name=f"REGTEST-FLEET-{suffix}")
    vehicle = await repo.create_vehicle(
        tenant_id=TENANT_ID, fleet_id=fleet.id, license_plate=f"REGTEST-{suffix}",
        vehicle_type="CAR",
    )
    route = await repo.create_route(
        tenant_id=TENANT_ID, name=f"REGTEST-ROUTE-{suffix}",
        start_hub_id=hub1.id, end_hub_id=hub2.id, waypoints=[],
        distance_km=Decimal("10"), estimated_duration_minutes=30,
    )
    trip = await repo.create_trip(
        tenant_id=TENANT_ID, route_id=route.id, vehicle_id=vehicle.id, driver_id=driver_id,
        trip_category=TripCategory.PASSENGER,
        scheduled_start=datetime.utcnow(), scheduled_end=datetime.utcnow() + timedelta(hours=1),
    )
    return hub1, hub2, fleet, vehicle, route, trip


@pytest.mark.asyncio
async def test_get_route_real_record_and_tenant_isolation(db):
    driver = await _create_user(db, "p_regtest_transport_driver")
    hub1, hub2, fleet, vehicle, route, trip = await _setup_trip(db, driver_id=driver.id)

    service = TransportService(db)
    try:
        result = await service.get_route(route.id, TENANT_ID)
        assert result.id == route.id

        with pytest.raises(NotFoundError):
            await service.get_route(route.id, OTHER_TENANT_ID)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(Trip).where(Trip.id == trip.id))
            await cleanup_db.execute(delete(Route).where(Route.id == route.id))
            await cleanup_db.execute(delete(Vehicle).where(Vehicle.id == vehicle.id))
            await cleanup_db.execute(delete(Fleet).where(Fleet.id == fleet.id))
            await cleanup_db.execute(delete(TransportHub).where(TransportHub.id.in_([hub1.id, hub2.id])))
            await cleanup_db.execute(delete(User).where(User.id == driver.id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_get_vehicle_real_record_and_tenant_isolation(db):
    driver = await _create_user(db, "p_regtest_transport_driver2")
    hub1, hub2, fleet, vehicle, route, trip = await _setup_trip(db, driver_id=driver.id)

    service = TransportService(db)
    try:
        result = await service.get_vehicle(vehicle.id, TENANT_ID)
        assert result.id == vehicle.id

        with pytest.raises(NotFoundError):
            await service.get_vehicle(vehicle.id, OTHER_TENANT_ID)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(Trip).where(Trip.id == trip.id))
            await cleanup_db.execute(delete(Route).where(Route.id == route.id))
            await cleanup_db.execute(delete(Vehicle).where(Vehicle.id == vehicle.id))
            await cleanup_db.execute(delete(Fleet).where(Fleet.id == fleet.id))
            await cleanup_db.execute(delete(TransportHub).where(TransportHub.id.in_([hub1.id, hub2.id])))
            await cleanup_db.execute(delete(User).where(User.id == driver.id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_list_bookings_filters_by_trip(db):
    driver = await _create_user(db, "p_regtest_transport_driver3")
    passenger = await _create_user(db, "p_regtest_transport_passenger")
    hub1, hub2, fleet, vehicle, route, trip = await _setup_trip(db, driver_id=driver.id)

    repo = TransportRepository(db)
    booking = await repo.create_booking(
        tenant_id=TENANT_ID, trip_id=trip.id, passenger_id=passenger.id,
        booking_type="SEAT", seats_count=1, fare_paid_mrusdt=Decimal("5"),
    )
    await db.commit()

    service = TransportService(db)
    try:
        result = await service.list_bookings(TENANT_ID, trip_id=trip.id)
        assert any(b.id == booking.id for b in result)

        result_wrong_trip = await service.list_bookings(TENANT_ID, trip_id=999_999_999)
        assert not any(b.id == booking.id for b in result_wrong_trip)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(TripBooking).where(TripBooking.id == booking.id))
            await cleanup_db.execute(delete(Trip).where(Trip.id == trip.id))
            await cleanup_db.execute(delete(Route).where(Route.id == route.id))
            await cleanup_db.execute(delete(Vehicle).where(Vehicle.id == vehicle.id))
            await cleanup_db.execute(delete(Fleet).where(Fleet.id == fleet.id))
            await cleanup_db.execute(delete(TransportHub).where(TransportHub.id.in_([hub1.id, hub2.id])))
            await cleanup_db.execute(delete(User).where(User.id.in_([driver.id, passenger.id])))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_assign_delivery_to_trip_ownership_and_success(db):
    driver = await _create_user(db, "p_regtest_transport_driver4")
    sender = await _create_user(db, "p_regtest_transport_sender")
    other_user = await _create_user(db, "p_regtest_transport_other")
    receiver = await _create_user(db, "p_regtest_transport_receiver")
    hub1, hub2, fleet, vehicle, route, trip = await _setup_trip(db, driver_id=driver.id)

    repo = TransportRepository(db)
    task = await repo.create_delivery_task(
        tenant_id=TENANT_ID, sender_id=sender.id, receiver_id=receiver.id,
        pickup_address={"lat": 0, "lng": 0}, dropoff_address={"lat": 1, "lng": 1},
    )
    await db.commit()

    service = TransportService(db)
    try:
        with pytest.raises(PermissionDeniedError):
            await service.assign_delivery_to_trip(TENANT_ID, task.id, trip.id, other_user.id)

        result = await service.assign_delivery_to_trip(TENANT_ID, task.id, trip.id, sender.id)
        assert result.trip_id == trip.id
        assert result.status == "ASSIGNED"

        with pytest.raises(NotFoundError):
            await service.assign_delivery_to_trip(TENANT_ID, task.id, 999_999_999, sender.id)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(DeliveryTask).where(DeliveryTask.id == task.id))
            await cleanup_db.execute(delete(Trip).where(Trip.id == trip.id))
            await cleanup_db.execute(delete(Route).where(Route.id == route.id))
            await cleanup_db.execute(delete(Vehicle).where(Vehicle.id == vehicle.id))
            await cleanup_db.execute(delete(Fleet).where(Fleet.id == fleet.id))
            await cleanup_db.execute(delete(TransportHub).where(TransportHub.id.in_([hub1.id, hub2.id])))
            await cleanup_db.execute(delete(User).where(User.id.in_([driver.id, sender.id, other_user.id, receiver.id])))
            await cleanup_db.commit()
