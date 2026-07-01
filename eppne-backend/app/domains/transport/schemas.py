# app/domains/transport/schemas.py (الإصدار النهائي المتكامل)
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.transport.models import TransportType, TripCategory, TripStatus, VehicleStatus

# ========== Hubs ==========
class TransportHubCreate(BaseModel):
    name: str
    hub_type: str
    region: Optional[str] = None
    gps_location: Dict[str, float]

class TransportHubResponse(TransportHubCreate):
    id: int
    entity_id: Optional[int]
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Fleets & Vehicles ==========
class FleetCreate(BaseModel):
    name: str

class FleetResponse(FleetCreate):
    id: int
    entity_id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class VehicleCreate(BaseModel):
    license_plate: str
    vehicle_type: TransportType
    capacity_kg: Optional[Decimal] = None
    capacity_passengers: Optional[int] = None
    fuel_type: str = "ELECTRIC"
    carbon_per_km: Decimal = 0

class VehicleResponse(VehicleCreate):
    id: int
    fleet_id: int
    smart_asset_id: Optional[int]
    status: VehicleStatus
    current_location: Optional[Dict[str, float]]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Routes ==========
class RouteCreate(BaseModel):
    name: str
    start_hub_id: int
    end_hub_id: int
    waypoints: List[Dict[str, Any]] = []
    distance_km: Decimal
    estimated_duration_minutes: int

class RouteResponse(RouteCreate):
    id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Trips ==========
class TripCreate(BaseModel):
    route_id: int
    vehicle_id: int
    driver_id: int
    trip_category: TripCategory
    scheduled_start: datetime
    scheduled_end: datetime
    base_fare_mrusdt: Decimal = 0

class TripResponse(TripCreate):
    id: int
    actual_start: Optional[datetime]
    actual_end: Optional[datetime]
    status: TripStatus
    total_distance_km: Decimal
    carbon_footprint_kg: Decimal
    total_fare_mrusdt: Decimal
    payment_tx_hash: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TripStartRequest(BaseModel):
    actual_start: datetime

class TripCompleteRequest(BaseModel):
    actual_end: datetime
    total_distance_km: Decimal

# ========== Bookings (مع Idempotency) ==========
class TripBookingCreate(BaseModel):
    trip_id: int
    passenger_id: Optional[int] = None
    company_id: Optional[int] = None
    booking_type: str  # PASSENGER or FREIGHT
    seats_count: Optional[int] = None
    weight_kg: Optional[Decimal] = None
    idempotency_key: Optional[str] = None  # 🔥 جديد

class TripBookingResponse(TripBookingCreate):
    id: int
    fare_paid_mrusdt: Decimal
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Deliveries (مع Idempotency) ==========
class DeliveryTaskCreate(BaseModel):
    order_id: Optional[int] = None
    sender_id: int
    receiver_id: int
    pickup_address: Dict[str, Any]
    dropoff_address: Dict[str, Any]
    estimated_distance_km: Optional[Decimal] = None
    delivery_fee_mrusdt: Decimal = 0
    idempotency_key: Optional[str] = None  # 🔥 جديد

class DeliveryTaskResponse(DeliveryTaskCreate):
    id: int
    trip_id: Optional[int]
    status: str
    delivery_proof_hash: Optional[str]
    payment_tx_hash: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DeliveryProof(BaseModel):
    proof_hash: str