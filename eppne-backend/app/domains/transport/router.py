# app/domains/transport/router.py (الإصدار النهائي المتكامل)
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, List, cast
from decimal import Decimal

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser
from app.domains.identity.models import User
from app.domains.transport.service import TransportService
from app.domains.transport.schemas import *
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/transport", tags=["Sovereign Transport & Logistics"])

# ========== Hubs ==========
@router.post("/hubs", response_model=TransportHubResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_hub(
    data: TransportHubCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    hub = await service.create_hub(cast(int, current_user.tenant_id), data.model_dump())  # ✅ cast
    return hub

@router.get("/hubs", response_model=list[TransportHubResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_hubs(
    hub_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    hubs = await service.list_hubs(cast(int, current_user.tenant_id), hub_type, skip, limit)  # ✅ cast
    return hubs

# ========== Fleets & Vehicles ==========
@router.post("/fleets", response_model=FleetResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_fleet(
    data: FleetCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    fleet = await service.create_fleet(cast(int, current_user.tenant_id), data.model_dump())  # ✅ cast
    return fleet

@router.post("/vehicles", response_model=VehicleResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_vehicle(
    data: VehicleCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    vehicle = await service.create_vehicle(cast(int, current_user.tenant_id), data.model_dump())  # ✅ cast
    return vehicle

@router.patch("/vehicles/{vehicle_id}/location")
@rate_limit(max_requests=30, window_seconds=60)
async def update_vehicle_location(
    vehicle_id: int,
    location: Dict[str, float],
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    vehicle = await service.update_vehicle_location(cast(int, current_user.tenant_id), vehicle_id, location)  # ✅ cast
    return {"status": "updated", "vehicle_id": vehicle.id}

@router.get("/vehicles/available", response_model=list[VehicleResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_available_vehicles(
    fleet_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    vehicles = await service.get_available_vehicles(cast(int, current_user.tenant_id), fleet_id)  # ✅ cast
    return vehicles

@router.get("/vehicles", response_model=list[VehicleResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_vehicles(
    fleet_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    vehicles = await service.list_vehicles(cast(int, current_user.tenant_id), fleet_id, status, skip, limit)
    return vehicles

@router.get("/vehicles/{vehicle_id}", response_model=VehicleResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_vehicle(
    vehicle_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    vehicle = await service.get_vehicle(vehicle_id, cast(int, current_user.tenant_id))
    return vehicle

@router.patch("/vehicles/{vehicle_id}", response_model=VehicleResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_vehicle(
    vehicle_id: int,
    data: VehicleUpdate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    vehicle = await service.update_vehicle(cast(int, current_user.tenant_id), vehicle_id, data.model_dump(exclude_unset=True))
    return vehicle

@router.delete("/vehicles/{vehicle_id}", status_code=204)
@rate_limit(max_requests=10, window_seconds=60)
async def delete_vehicle(
    vehicle_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    await service.delete_vehicle(cast(int, current_user.tenant_id), vehicle_id)

# ========== Fleets (list/update/delete) ==========
@router.get("/fleets", response_model=list[FleetResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_fleets(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    fleets = await service.list_fleets(cast(int, current_user.tenant_id), skip, limit)
    return fleets

@router.patch("/fleets/{fleet_id}", response_model=FleetResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_fleet(
    fleet_id: int,
    data: FleetUpdate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    fleet = await service.update_fleet(cast(int, current_user.tenant_id), fleet_id, data.name)
    return fleet

@router.delete("/fleets/{fleet_id}", status_code=204)
@rate_limit(max_requests=10, window_seconds=60)
async def delete_fleet(
    fleet_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    await service.delete_fleet(cast(int, current_user.tenant_id), fleet_id)

# ========== Drivers (سرد مستخدمين نشطين — بدون كيان/دور منفصل) ==========
@router.get("/drivers", response_model=list[DriverResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_drivers(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    drivers = await service.list_drivers(cast(int, current_user.tenant_id), skip, limit)
    return drivers

# ========== Routes ==========
@router.post("/routes", response_model=RouteResponse, status_code=201)
@rate_limit(max_requests=5, window_seconds=60)
async def create_route(
    data: RouteCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    route = await service.create_route(cast(int, current_user.tenant_id), data.model_dump())  # ✅ cast
    return route

@router.get("/routes/{route_id}", response_model=RouteResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_route(
    route_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    route = await service.get_route(route_id, cast(int, current_user.tenant_id))
    return route

# ========== Trips ==========
@router.post("/trips", response_model=TripResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_trip(
    data: TripCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    trip = await service.create_trip(cast(int, current_user.tenant_id), data.model_dump())  # ✅ cast
    return trip

@router.patch("/trips/{trip_id}/start", response_model=TripResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def start_trip(
    trip_id: int,
    data: TripStartRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    user_id = cast(int, current_user.id)
    trip = await service.start_trip(cast(int, current_user.tenant_id), trip_id, user_id, data.actual_start)  # ✅ cast
    return trip

@router.patch("/trips/{trip_id}/complete", response_model=TripResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def complete_trip(
    trip_id: int,
    data: TripCompleteRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    user_id = cast(int, current_user.id)
    trip = await service.complete_trip(
        cast(int, current_user.tenant_id), trip_id, user_id, data.actual_end, float(data.total_distance_km)  # ✅ cast
    )
    return trip

@router.get("/trips/my", response_model=list[TripResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_my_trips(
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    user_id = cast(int, current_user.id)
    trips = await service.get_my_trips(cast(int, current_user.tenant_id), user_id, status_filter, skip, limit)  # ✅ cast
    return trips

@router.get("/trips/{trip_id}", response_model=TripResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_trip(
    trip_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    trip = await service.get_trip(trip_id, cast(int, current_user.tenant_id))
    return trip

# ========== Bookings ==========
@router.post("/bookings", response_model=TripBookingResponse, status_code=201)
@rate_limit(max_requests=20, window_seconds=60)
async def book_trip(
    data: TripBookingCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    user_id = cast(int, current_user.id)
    booking = await service.book_trip(
        tenant_id=cast(int, current_user.tenant_id),  # ✅ cast
        passenger_id=user_id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return booking

@router.get("/bookings/my", response_model=list[TripBookingResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_my_bookings(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    user_id = cast(int, current_user.id)
    bookings = await service.get_my_bookings(cast(int, current_user.tenant_id), user_id)  # ✅ cast
    return bookings

@router.get("/bookings", response_model=list[TripBookingResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_bookings(
    passenger_id: Optional[int] = None,
    trip_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    bookings = await service.list_bookings(cast(int, current_user.tenant_id), passenger_id, trip_id)
    return bookings

# ========== Deliveries ==========
@router.post("/deliveries", response_model=DeliveryTaskResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_delivery(
    data: DeliveryTaskCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    user_id = cast(int, current_user.id)
    task = await service.create_delivery(
        tenant_id=cast(int, current_user.tenant_id),  # ✅ cast
        sender_id=user_id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return task

@router.post("/deliveries/{task_id}/pay", response_model=DeliveryTaskResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def pay_delivery(
    task_id: int,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    user_id = cast(int, current_user.id)
    task = await service.pay_delivery(
        tenant_id=cast(int, current_user.tenant_id),  # ✅ cast
        task_id=task_id,
        payer_id=user_id,
        idempotency_key=idempotency_key
    )
    return task

@router.post("/deliveries/{task_id}/complete", response_model=DeliveryTaskResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def complete_delivery(
    task_id: int,
    proof: DeliveryProof,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    user_id = cast(int, current_user.id)
    task = await service.complete_delivery(cast(int, current_user.tenant_id), task_id, user_id, proof.proof_hash)  # ✅ cast
    return task


@router.post("/deliveries/{task_id}/assign", response_model=DeliveryTaskResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def assign_delivery_to_trip(
    task_id: int,
    data: AssignDeliveryRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    user_id = cast(int, current_user.id)
    task = await service.assign_delivery_to_trip(cast(int, current_user.tenant_id), task_id, data.trip_id, user_id)
    return task

@router.post("/deliveries/{task_id}/cancel", response_model=DeliveryTaskResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def cancel_delivery(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    user_id = cast(int, current_user.id)
    task = await service.cancel_delivery(cast(int, current_user.tenant_id), task_id, user_id)
    return task


# ========== Booking cancellation ==========
@router.patch("/bookings/{booking_id}/cancel", response_model=TripBookingResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def cancel_booking(
    booking_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    user_id = cast(int, current_user.id)
    booking = await service.cancel_booking(cast(int, current_user.tenant_id), booking_id, user_id)
    return booking