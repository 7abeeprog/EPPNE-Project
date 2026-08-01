# app/domains/transport/repository.py (الإصدار النهائي المُعدّل)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime

# ✅ استيراد صريح لجميع النماذج من الملف المُعدّل
from app.domains.transport.models import (
    TransportHub,
    Fleet,
    Vehicle,
    Route,
    Trip,
    TripBooking,
    DeliveryTask,
    VehicleStatus,
    TripStatus
)

from app.core.errors import NotFoundError


class TransportRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- Hubs ----------
    async def create_hub(self, tenant_id: int, **kwargs) -> TransportHub:
        hub = TransportHub(tenant_id=tenant_id, **kwargs)
        self.db.add(hub)
        await self.db.commit()
        await self.db.refresh(hub)
        return hub

    async def get_hub(self, hub_id: int, tenant_id: int) -> Optional[TransportHub]:
        result = await self.db.execute(
            select(TransportHub).where(TransportHub.id == hub_id, TransportHub.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list_hubs(self, tenant_id: int, hub_type: Optional[str] = None, skip=0, limit=100):
        query = select(TransportHub).where(TransportHub.tenant_id == tenant_id)
        if hub_type:
            query = query.where(TransportHub.hub_type == hub_type)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    # ---------- Fleets & Vehicles ----------
    async def create_fleet(self, tenant_id: int, **kwargs) -> Fleet:
        fleet = Fleet(tenant_id=tenant_id, **kwargs)
        self.db.add(fleet)
        await self.db.commit()
        await self.db.refresh(fleet)
        return fleet

    async def get_fleet(self, fleet_id: int, tenant_id: int) -> Optional[Fleet]:
        result = await self.db.execute(
            select(Fleet).where(Fleet.id == fleet_id, Fleet.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def create_vehicle(self, tenant_id: int, **kwargs) -> Vehicle:
        vehicle = Vehicle(tenant_id=tenant_id, **kwargs)
        self.db.add(vehicle)
        await self.db.commit()
        await self.db.refresh(vehicle)
        return vehicle

    async def get_vehicle(self, vehicle_id: int, tenant_id: int) -> Optional[Vehicle]:
        result = await self.db.execute(
            select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def update_vehicle_location(self, vehicle_id: int, tenant_id: int, location: dict) -> Vehicle:
        await self.db.execute(
            update(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.tenant_id == tenant_id)
            .values(current_location=location)
        )
        await self.db.commit()
        return await self.get_vehicle(vehicle_id, tenant_id)

    async def list_available_vehicles(self, tenant_id: int, fleet_id: Optional[int] = None):
        query = select(Vehicle).where(Vehicle.status == VehicleStatus.AVAILABLE, Vehicle.tenant_id == tenant_id)
        if fleet_id:
            query = query.where(Vehicle.fleet_id == fleet_id)
        result = await self.db.execute(query)
        return result.scalars().all()

    # ---------- Routes ----------
    async def create_route(self, tenant_id: int, **kwargs) -> Route:
        route = Route(tenant_id=tenant_id, **kwargs)
        self.db.add(route)
        await self.db.commit()
        await self.db.refresh(route)
        return route

    async def get_route(self, route_id: int, tenant_id: int) -> Optional[Route]:
        result = await self.db.execute(
            select(Route).where(Route.id == route_id, Route.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    # ---------- Trips ----------
    async def create_trip(self, tenant_id: int, **kwargs) -> Trip:
        trip = Trip(tenant_id=tenant_id, **kwargs)
        self.db.add(trip)
        await self.db.commit()
        await self.db.refresh(trip)
        return trip

    async def get_trip(self, trip_id: int, tenant_id: int) -> Optional[Trip]:
        result = await self.db.execute(
            select(Trip).where(Trip.id == trip_id, Trip.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def start_trip(self, trip_id: int, tenant_id: int, actual_start: datetime) -> Trip:
        await self.db.execute(
            update(Trip).where(Trip.id == trip_id, Trip.tenant_id == tenant_id).values(
                actual_start=actual_start,
                status=TripStatus.ONGOING
            )
        )
        await self.db.commit()
        trip = await self.get_trip(trip_id, tenant_id)
        if trip:
            await self.db.execute(
                update(Vehicle).where(Vehicle.id == trip.vehicle_id, Vehicle.tenant_id == tenant_id)
                .values(status=VehicleStatus.IN_TRIP)
            )
            await self.db.commit()
        return await self.get_trip(trip_id, tenant_id)

    async def complete_trip(self, trip_id: int, tenant_id: int, actual_end: datetime,
                            total_distance_km: float, carbon: float) -> Trip:
        await self.db.execute(
            update(Trip).where(Trip.id == trip_id, Trip.tenant_id == tenant_id).values(
                actual_end=actual_end,
                total_distance_km=total_distance_km,
                carbon_footprint_kg=carbon,
                status=TripStatus.COMPLETED
            )
        )
        await self.db.commit()
        trip = await self.get_trip(trip_id, tenant_id)
        if trip:
            await self.db.execute(
                update(Vehicle).where(Vehicle.id == trip.vehicle_id, Vehicle.tenant_id == tenant_id)
                .values(status=VehicleStatus.AVAILABLE)
            )
            await self.db.commit()
        return await self.get_trip(trip_id, tenant_id)

    async def list_trips(self, tenant_id: int, driver_id: Optional[int] = None,
                         status_filter: Optional[str] = None, skip=0, limit=100):
        query = select(Trip).options(
            selectinload(Trip.vehicle),
            selectinload(Trip.driver),
            selectinload(Trip.route)
        ).where(Trip.tenant_id == tenant_id)
        if driver_id:
            query = query.where(Trip.driver_id == driver_id)
        if status_filter:
            query = query.where(Trip.status == status_filter)
        query = query.order_by(Trip.scheduled_start.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    # ---------- Bookings ----------
    async def create_booking(self, tenant_id: int, **kwargs) -> TripBooking:
        booking = TripBooking(tenant_id=tenant_id, **kwargs)
        self.db.add(booking)
        await self.db.commit()
        await self.db.refresh(booking)
        return booking

    async def get_booking(self, booking_id: int, tenant_id: int) -> Optional[TripBooking]:
        result = await self.db.execute(
            select(TripBooking).where(TripBooking.id == booking_id, TripBooking.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list_bookings(self, tenant_id: int, passenger_id: Optional[int] = None, trip_id: Optional[int] = None):
        query = select(TripBooking).options(
            selectinload(TripBooking.trip)
        ).where(TripBooking.tenant_id == tenant_id)
        if passenger_id:
            query = query.where(TripBooking.passenger_id == passenger_id)
        if trip_id:
            query = query.where(TripBooking.trip_id == trip_id)
        result = await self.db.execute(query)
        return result.scalars().all()

    # ---------- Deliveries ----------
    async def create_delivery_task(self, tenant_id: int, **kwargs) -> DeliveryTask:
        task = DeliveryTask(tenant_id=tenant_id, **kwargs)
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_delivery_task(self, task_id: int, tenant_id: int) -> Optional[DeliveryTask]:
        result = await self.db.execute(
            select(DeliveryTask).where(DeliveryTask.id == task_id, DeliveryTask.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def assign_delivery_to_trip(self, task_id: int, tenant_id: int, trip_id: int) -> DeliveryTask:
        await self.db.execute(
            update(DeliveryTask).where(DeliveryTask.id == task_id, DeliveryTask.tenant_id == tenant_id)
            .values(trip_id=trip_id, status="ASSIGNED")
        )
        await self.db.commit()
        return await self.get_delivery_task(task_id, tenant_id)

    async def complete_delivery(self, task_id: int, tenant_id: int, proof_hash: str) -> DeliveryTask:
        await self.db.execute(
            update(DeliveryTask).where(DeliveryTask.id == task_id, DeliveryTask.tenant_id == tenant_id)
            .values(status="DELIVERED", delivery_proof_hash=proof_hash)
        )
        await self.db.commit()
        return await self.get_delivery_task(task_id, tenant_id)

    # ========== دوال Idempotency ==========
    async def get_booking_by_idempotency(self, idempotency_key: str) -> Optional[TripBooking]:
        result = await self.db.execute(
            select(TripBooking).where(TripBooking.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def get_delivery_by_idempotency(self, idempotency_key: str) -> Optional[DeliveryTask]:
        result = await self.db.execute(
            select(DeliveryTask).where(DeliveryTask.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    # ========== التحقق من صلاحية المركبة ==========
    async def check_vehicle_availability(self, vehicle_id: int, tenant_id: int) -> bool:
        vehicle = await self.get_vehicle(vehicle_id, tenant_id)
        return vehicle and vehicle.status == VehicleStatus.AVAILABLE