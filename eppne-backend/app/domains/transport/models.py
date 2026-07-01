# app/domains/transport/models.py (الإصدار النهائي المتكامل)
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, JSON, Enum as SQLEnum, Index, CheckConstraint
)
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
    hub_type = Column(String(50), nullable=False)  # BUS_STATION, PORT, AIRPORT, SPACE_PORT
    region = Column(String(100), nullable=True)
    gps_location = Column(JSON, nullable=False)  # {"lat": 30.0, "lng": 31.0}

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

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


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    fleet_id = Column(Integer, ForeignKey("fleets.id"), nullable=False, index=True)
    smart_asset_id = Column(Integer, ForeignKey("smart_assets.id"), nullable=True)  # من قطاع IoT

    license_plate = Column(String(50), unique=True, nullable=False, index=True)
    vehicle_type = Column(SQLEnum(TransportType), nullable=False)
    capacity_kg = Column(Numeric(15, 2), nullable=True)   # حمولة بالكيلو
    capacity_passengers = Column(Integer, nullable=True)

    fuel_type = Column(String(50), default="ELECTRIC")    # ELECTRIC, FUEL, HYBRID
    carbon_per_km = Column(Numeric(10, 4), default=0)     # جرام CO2 لكل كم

    status = Column(SQLEnum(VehicleStatus), default=VehicleStatus.AVAILABLE)
    current_location = Column(JSON, nullable=True)        # تتبع فوري

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# ========== 3. المسارات والرحلات ==========
class Route(Base):
    __tablename__ = "transport_routes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    start_hub_id = Column(Integer, ForeignKey("transport_hubs.id"), nullable=False)
    end_hub_id = Column(Integer, ForeignKey("transport_hubs.id"), nullable=False)
    waypoints = Column(JSON, default=list)                # قائمة محطات وسيطة
    distance_km = Column(Numeric(10, 2), nullable=False)
    estimated_duration_minutes = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


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

    # بيانات التتبع والكربون
    total_distance_km = Column(Numeric(10, 2), default=0)
    carbon_footprint_kg = Column(Numeric(15, 2), default=0)

    # ربط بالمالية
    base_fare_mrusdt = Column(Numeric(30, 8), default=0)
    total_fare_mrusdt = Column(Numeric(30, 8), default=0)
    payment_tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_trips_driver_status", "driver_id", "status"),
        Index("ix_trips_schedule", "scheduled_start", "scheduled_end"),
    )

# ========== 4. حجوزات الركاب والشحن (مع Idempotency) ==========
class TripBooking(Base):
    __tablename__ = "trip_bookings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    trip_id = Column(Integer, ForeignKey("transport_trips.id"), nullable=False, index=True)
    passenger_id = Column(Integer, ForeignKey("users.id"), nullable=True)   # راكب
    company_id = Column(Integer, nullable=True)  
    booking_type = Column(String(20), nullable=False)  # PASSENGER, FREIGHT

    seats_count = Column(Integer, nullable=True)
    weight_kg = Column(Numeric(15, 2), nullable=True)

    fare_paid_mrusdt = Column(Numeric(30, 8), default=0)
    status = Column(String(50), default="CONFIRMED")   # CONFIRMED, CHECKED_IN, CANCELLED

    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "(passenger_id IS NOT NULL AND company_id IS NULL) OR (passenger_id IS NULL AND company_id IS NOT NULL)",
            name="check_booking_owner"
        ),
    )

# ========== 5. مهام التوصيل (لوجستيات الطرود) مع Idempotency ==========
class DeliveryTask(Base):
    __tablename__ = "delivery_tasks"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    order_id = Column(Integer, nullable=True)                     # من قطاع التجارة
    trip_id = Column(Integer, ForeignKey("transport_trips.id"), nullable=True, index=True)

    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    pickup_address = Column(JSON, nullable=False)                # {"address": "...", "lat": , "lng": }
    dropoff_address = Column(JSON, nullable=False)
    estimated_distance_km = Column(Numeric(10, 2), nullable=True)

    status = Column(String(50), default="PENDING")               # PENDING, ASSIGNED, PICKED_UP, DELIVERED
    delivery_proof_hash = Column(String(100), nullable=True)     # صورة توقيع مشفرة

    delivery_fee_mrusdt = Column(Numeric(30, 8), default=0)
    payment_tx_hash = Column(String(100), nullable=True)

    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())