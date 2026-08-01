# app/domains/transport/models.py (الإصدار النهائي المُعدّل)
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, Enum as SQLEnum, Index, CheckConstraint, text
)
from sqlalchemy.dialects.postgresql import JSONB  # ✅ الاستيراد الصحيح
from sqlalchemy.sql import func
from app.core.database import Base
import enum

# ========== الأنواع المساعدة ==========
class TransportType(str, enum.Enum):
    BICYCLE = "BICYCLE"
    MOTORCYCLE = "MOTORCYCLE"
    CAR = "CAR"
    BUS = "BUS"
    TRUCK = "TRUCK"
    SHIP = "SHIP"
    AIRCRAFT = "AIRCRAFT"
    SPACECRAFT = "SPACECRAFT"
    TRAIN = "TRAIN"

class TripCategory(str, enum.Enum):
    PASSENGER = "PASSENGER"
    FREIGHT = "FREIGHT"
    MASS_TRANSIT = "MASS_TRANSIT"
    TOURISM = "TOURISM"
    MEDICAL = "MEDICAL"
    EDUCATIONAL = "EDUCATIONAL"

class TripStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    DELAYED = "DELAYED"

class VehicleStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    IN_TRIP = "IN_TRIP"
    MAINTENANCE = "MAINTENANCE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"

# ========== 1. المحطات (Hubs) ==========
class TransportHub(Base):
    __tablename__ = "transport_hubs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    hub_type = Column(String(50), nullable=False)
    region = Column(String(100), nullable=True)
    gps_location = Column(JSONB, nullable=False)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_transport_hub_tenant", "tenant_id"),
        Index("ix_transport_hub_created_at", "created_at"),
    )

# ========== 2. الأساطيل والمركبات ==========
class Fleet(Base):
    __tablename__ = "fleets"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_fleet_tenant", "tenant_id"),
        Index("ix_fleet_created_at", "created_at"),
    )

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    fleet_id = Column(Integer, ForeignKey("fleets.id"), nullable=False, index=True)
    smart_asset_id = Column(Integer, ForeignKey("smart_assets.id"), nullable=True)

    license_plate = Column(String(50), unique=True, nullable=False, index=True)
    vehicle_type = Column(SQLEnum(TransportType), nullable=False)
    capacity_kg = Column(Numeric(15, 2), nullable=True)
    capacity_passengers = Column(Integer, nullable=True)

    fuel_type = Column(String(50), default="ELECTRIC")
    carbon_per_km = Column(Numeric(10, 4), default=0)

    status = Column(SQLEnum(VehicleStatus), default=VehicleStatus.AVAILABLE)
    current_location = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_vehicle_tenant", "tenant_id"),
        Index("ix_vehicle_fleet", "fleet_id"),
        Index("ix_vehicle_created_at", "created_at"),
    )

# ========== 3. المسارات والرحلات ==========
class Route(Base):
    __tablename__ = "transport_routes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    start_hub_id = Column(Integer, ForeignKey("transport_hubs.id"), nullable=False)
    end_hub_id = Column(Integer, ForeignKey("transport_hubs.id"), nullable=False)
    waypoints = Column(JSONB, default=list)
    distance_km = Column(Numeric(10, 2), nullable=False)
    estimated_duration_minutes = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_route_tenant", "tenant_id"),
        Index("ix_route_created_at", "created_at"),
    )

class Trip(Base):
    __tablename__ = "transport_trips"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    route_id = Column(Integer, ForeignKey("transport_routes.id"), nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    trip_category = Column(SQLEnum(TripCategory), nullable=False)
    scheduled_start = Column(DateTime(timezone=True), nullable=False)
    scheduled_end = Column(DateTime(timezone=True), nullable=False)
    actual_start = Column(DateTime(timezone=True), nullable=True)
    actual_end = Column(DateTime(timezone=True), nullable=True)

    status = Column(SQLEnum(TripStatus), default=TripStatus.SCHEDULED)

    total_distance_km = Column(Numeric(10, 2), default=0)
    carbon_footprint_kg = Column(Numeric(15, 2), default=0)

    base_fare_mrusdt = Column(Numeric(30, 8), default=0)
    total_fare_mrusdt = Column(Numeric(30, 8), default=0)
    payment_tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_trips_driver_status", "driver_id", "status"),
        Index("ix_trips_schedule", "scheduled_start", "scheduled_end"),
        Index("ix_trips_created_at", "created_at"),
    )

# ========== 4. حجوزات الركاب والشحن (مع Idempotency) ==========
class TripBooking(Base):
    __tablename__ = "trip_bookings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    trip_id = Column(Integer, ForeignKey("transport_trips.id"), nullable=False, index=True)
    passenger_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    company_id = Column(Integer, nullable=True)
    booking_type = Column(String(20), nullable=False)

    seats_count = Column(Integer, nullable=True)
    weight_kg = Column(Numeric(15, 2), nullable=True)

    fare_paid_mrusdt = Column(Numeric(30, 8), default=0)
    status = Column(String(50), default="CONFIRMED")

    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "(passenger_id IS NOT NULL AND company_id IS NULL) OR (passenger_id IS NULL AND company_id IS NOT NULL)",
            name="check_booking_owner"
        ),
        Index("ix_trip_booking_tenant", "tenant_id"),
        Index("ix_trip_booking_trip", "trip_id"),
        Index("ix_trip_booking_created_at", "created_at"),
        Index("ix_trip_booking_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )

# ========== 5. مهام التوصيل (لوجستيات الطرود) مع Idempotency ==========
class DeliveryTask(Base):
    __tablename__ = "delivery_tasks"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    order_id = Column(Integer, nullable=True)
    trip_id = Column(Integer, ForeignKey("transport_trips.id"), nullable=True, index=True)

    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    pickup_address = Column(JSONB, nullable=False)
    dropoff_address = Column(JSONB, nullable=False)
    estimated_distance_km = Column(Numeric(10, 2), nullable=True)

    status = Column(String(50), default="PENDING")
    delivery_proof_hash = Column(String(100), nullable=True)

    delivery_fee_mrusdt = Column(Numeric(30, 8), default=0)
    payment_tx_hash = Column(String(100), nullable=True)

    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_delivery_task_tenant", "tenant_id"),
        Index("ix_delivery_task_trip", "trip_id"),
        Index("ix_delivery_task_status", "status"),
        Index("ix_delivery_task_created_at", "created_at"),
        Index("ix_delivery_task_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )