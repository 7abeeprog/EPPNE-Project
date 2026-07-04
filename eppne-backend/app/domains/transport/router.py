# app/domains/transport/router.py (الإصدار النهائي المتكامل)
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict
from decimal import Decimal

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, get_current_tenant
from app.domains.identity.models import User
from app.domains.academy.models import AcademyTenant
from app.domains.transport.service import TransportService
from app.domains.transport.repository import TransportRepository
from app.domains.transport.schemas import *
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/transport", tags=["Sovereign Transport & Logistics"])

# ========== Hubs ==========
@router.post("/hubs", response_model=TransportHubResponse, status_code=201)
async def create_hub(
    data: TransportHubCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    repo = TransportRepository(db)
    hub = await repo.create_hub(tenant_id=tenant.id, **data.model_dump())
    return hub

@router.get("/hubs", response_model=list[TransportHubResponse])
async def list_hubs(
    hub_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = TransportRepository(db)
    hubs = await repo.list_hubs(tenant.id, hub_type, skip, limit)
    return hubs

# ========== Fleets & Vehicles ==========
@router.post("/fleets", response_model=FleetResponse, status_code=201)
async def create_fleet(
    data: FleetCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    repo = TransportRepository(db)
    fleet = await repo.create_fleet(tenant.id, entity_id=1, name=data.name)  # entity_id مؤقت
    return fleet

@router.post("/vehicles", response_model=VehicleResponse, status_code=201)
async def create_vehicle(
    data: VehicleCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    repo = TransportRepository(db)
    vehicle = await repo.create_vehicle(tenant.id, **data.model_dump())
    return vehicle

@router.patch("/vehicles/{vehicle_id}/location")
@rate_limit(max_requests=30, window_seconds=60)
async def update_vehicle_location(
    vehicle_id: int,
    location: Dict[str, float],
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    repo = TransportRepository(db)
    vehicle = await repo.update_vehicle_location(vehicle_id, tenant.id, location)
    return {"status": "updated", "vehicle_id": vehicle.id}

@router.get("/vehicles/available", response_model=list[VehicleResponse])
async def get_available_vehicles(
    fleet_id: Optional[int] = None,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = TransportRepository(db)
    vehicles = await repo.list_available_vehicles(tenant.id, fleet_id)
    return vehicles

# ========== Routes (مع Rate Limiting واستخدام الخدمة) ==========
@router.post("/routes", response_model=RouteResponse, status_code=201)
@rate_limit(max_requests=5, window_seconds=60)
async def create_route(
    data: RouteCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    route = await service.create_route(tenant.id, data.model_dump())
    return route

# ========== Trips ==========
@router.post("/trips", response_model=TripResponse, status_code=201)
async def create_trip(
    data: TripCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    repo = TransportRepository(db)
    trip = await repo.create_trip(tenant.id, **data.model_dump())
    return trip

@router.patch("/trips/{trip_id}/start", response_model=TripResponse)
async def start_trip(
    trip_id: int,
    data: TripStartRequest,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    trip = await service.start_trip(tenant.id, trip_id, current_user.id, data.actual_start)
    return trip

@router.patch("/trips/{trip_id}/complete", response_model=TripResponse)
async def complete_trip(
    trip_id: int,
    data: TripCompleteRequest,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    trip = await service.complete_trip(tenant.id, trip_id, current_user.id, data.actual_end, data.total_distance_km)
    return trip

@router.get("/trips/my", response_model=list[TripResponse])
async def get_my_trips(
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = TransportRepository(db)
    trips = await repo.list_trips(tenant.id, driver_id=current_user.id, status_filter=status_filter, skip=skip, limit=limit)
    return trips

# ========== Bookings (مع Idempotency و Rate Limiting) ==========
@router.post("/bookings", response_model=TripBookingResponse, status_code=201)
@rate_limit(max_requests=20, window_seconds=60)
async def book_trip(
    data: TripBookingCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    booking = await service.book_trip(
        tenant_id=tenant.id,
        passenger_id=current_user.id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return booking

@router.get("/bookings/my", response_model=list[TripBookingResponse])
async def get_my_bookings(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = TransportRepository(db)
    bookings = await repo.list_bookings(tenant.id, passenger_id=current_user.id)
    return bookings

# ========== Deliveries (مع Idempotency و Rate Limiting) ==========
@router.post("/deliveries", response_model=DeliveryTaskResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_delivery(
    data: DeliveryTaskCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    task = await service.create_delivery(
        tenant_id=tenant.id,
        sender_id=current_user.id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return task

@router.post("/deliveries/{task_id}/pay", response_model=DeliveryTaskResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def pay_delivery(
    task_id: int,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TransportService(db)
    task = await service.pay_delivery(
        tenant_id=tenant.id,
        task_id=task_id,
        payer_id=current_user.id,
        idempotency_key=idempotency_key
    )
    return task

@router.post("/deliveries/{task_id}/complete", response_model=DeliveryTaskResponse)
async def complete_delivery(
    task_id: int,
    proof: DeliveryProof,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = TransportRepository(db)
    task = await repo.complete_delivery(task_id, tenant.id, proof.proof_hash)
    return task