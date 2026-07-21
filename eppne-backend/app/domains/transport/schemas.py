# app/domains/transport/schemas.py (الإصدار النهائي المتكامل)
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.transport.models import TransportType, TripCategory, TripStatus, VehicleStatus

# ========== Hubs ==========
class TransportHubCreate(BaseModel):
    name: str = Field(description="اسم المحطة")
    hub_type: str = Field(description="نوع المحطة (BUS_STATION, PORT, AIRPORT, SPACE_PORT)")
    region: Optional[str] = Field(default=None, description="المنطقة")
    gps_location: Dict[str, float] = Field(description="موقع GPS (lat, lng)")
    entity_id: Optional[int] = Field(default=None, description="معرف الكيان المرتبط")

class TransportHubResponse(TransportHubCreate):
    id: int = Field(description="معرف المحطة")
    is_active: bool = Field(description="نشطة")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

# ========== Fleets & Vehicles ==========
class FleetCreate(BaseModel):
    name: str = Field(description="اسم الأسطول")
    entity_id: Optional[int] = Field(default=None, description="معرف الكيان المرتبط")

class FleetResponse(FleetCreate):
    id: int = Field(description="معرف الأسطول")
    # ✅ تم إزالة إعادة تعريف entity_id لأنها موروثة من FleetCreate
    is_active: bool = Field(description="نشط")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

class VehicleCreate(BaseModel):
    fleet_id: int = Field(description="معرف الأسطول")
    license_plate: str = Field(description="لوحة الترخيص")
    vehicle_type: TransportType = Field(description="نوع المركبة")
    capacity_kg: Optional[Decimal] = Field(default=None, description="السعة بالكيلوغرام")
    capacity_passengers: Optional[int] = Field(default=None, description="السعة بالركاب")
    fuel_type: str = Field(default="ELECTRIC", description="نوع الوقود")
    carbon_per_km: Decimal = Field(default=Decimal('0.0'), description="انبعاثات الكربون لكل كم")
    smart_asset_id: Optional[int] = Field(default=None, description="معرف الأصل الذكي من IoT")

class VehicleResponse(VehicleCreate):
    id: int = Field(description="معرف المركبة")
    status: VehicleStatus = Field(description="الحالة")
    current_location: Optional[Dict[str, float]] = Field(default=None, description="الموقع الحالي")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

# ========== Routes ==========
class RouteCreate(BaseModel):
    name: str = Field(description="اسم المسار")
    start_hub_id: int = Field(description="معرف محطة البداية")
    end_hub_id: int = Field(description="معرف محطة النهاية")
    waypoints: List[Dict[str, Any]] = Field(default=[], description="نقاط وسيطة")
    distance_km: Decimal = Field(description="المسافة بالكيلومترات")
    estimated_duration_minutes: int = Field(description="المدة التقديرية بالدقائق")

class RouteResponse(RouteCreate):
    id: int = Field(description="معرف المسار")
    is_active: bool = Field(description="نشط")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

# ========== Trips ==========
class TripCreate(BaseModel):
    route_id: int = Field(description="معرف المسار")
    vehicle_id: int = Field(description="معرف المركبة")
    driver_id: int = Field(description="معرف السائق")
    trip_category: TripCategory = Field(description="فئة الرحلة")
    scheduled_start: datetime = Field(description="وقت البدء المقرر")
    scheduled_end: datetime = Field(description="وقت الانتهاء المقرر")
    base_fare_mrusdt: Decimal = Field(default=Decimal('0.0'), description="الأجرة الأساسية")

class TripResponse(TripCreate):
    id: int = Field(description="معرف الرحلة")
    actual_start: Optional[datetime] = Field(default=None, description="وقت البدء الفعلي")
    actual_end: Optional[datetime] = Field(default=None, description="وقت الانتهاء الفعلي")
    status: TripStatus = Field(description="الحالة")
    total_distance_km: Decimal = Field(description="المسافة الإجمالية")
    carbon_footprint_kg: Decimal = Field(description="البصمة الكربونية")
    total_fare_mrusdt: Decimal = Field(description="الأجرة الإجمالية")
    payment_tx_hash: Optional[str] = Field(default=None, description="هاش معاملة الدفع")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

class TripStartRequest(BaseModel):
    actual_start: datetime = Field(description="وقت البدء الفعلي")

class TripCompleteRequest(BaseModel):
    actual_end: datetime = Field(description="وقت الانتهاء الفعلي")
    total_distance_km: Decimal = Field(description="المسافة الإجمالية بالكيلومترات")

# ========== Bookings ==========
class TripBookingCreate(BaseModel):
    trip_id: int = Field(description="معرف الرحلة")
    passenger_id: Optional[int] = Field(default=None, description="معرف الراكب")
    company_id: Optional[int] = Field(default=None, description="معرف الشركة")
    booking_type: str = Field(description="نوع الحجز (PASSENGER, FREIGHT)")
    seats_count: Optional[int] = Field(default=None, description="عدد المقاعد")
    weight_kg: Optional[Decimal] = Field(default=None, description="الوزن بالكيلوغرام (للشحن)")

class TripBookingResponse(TripBookingCreate):
    id: int = Field(description="معرف الحجز")
    fare_paid_mrusdt: Decimal = Field(description="الأجرة المدفوعة")
    status: str = Field(description="الحالة")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

# ========== Deliveries ==========
class DeliveryTaskCreate(BaseModel):
    order_id: Optional[int] = Field(default=None, description="معرف الطلب من قطاع التجارة")
    sender_id: int = Field(description="معرف المرسل")
    receiver_id: int = Field(description="معرف المستلم")
    pickup_address: Dict[str, Any] = Field(description="عنوان الاستلام")
    dropoff_address: Dict[str, Any] = Field(description="عنوان التسليم")
    estimated_distance_km: Optional[Decimal] = Field(default=None, description="المسافة التقديرية")
    delivery_fee_mrusdt: Decimal = Field(default=Decimal('0.0'), description="رسوم التوصيل")

class DeliveryTaskResponse(DeliveryTaskCreate):
    id: int = Field(description="معرف المهمة")
    trip_id: Optional[int] = Field(default=None, description="معرف الرحلة المرتبطة")
    status: str = Field(description="الحالة")
    delivery_proof_hash: Optional[str] = Field(default=None, description="هاش إثبات التسليم")
    payment_tx_hash: Optional[str] = Field(default=None, description="هاش معاملة الدفع")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

class DeliveryProof(BaseModel):
    proof_hash: str = Field(description="هاش إثبات التسليم (صورة، توقيع، إلخ)")