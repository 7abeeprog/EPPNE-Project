# app/domains/health/models.py
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, Enum as SQLEnum, CheckConstraint, Index, text
)
from sqlalchemy.dialects.postgresql import JSONB  # ✅ تم إضافة الاستيراد الصحيح
from sqlalchemy.sql import func
from app.core.database import Base
import enum

# ========== الأنواع المساعدة ==========
class TargetEntityType(str, enum.Enum):
    HUMAN = "HUMAN"
    ANIMAL = "ANIMAL"
    PLANT = "PLANT"
    ALGAE = "ALGAE"

class FacilityCategory(str, enum.Enum):
    HOSPITAL = "HOSPITAL"
    CLINIC = "CLINIC"
    LABORATORY = "LABORATORY"
    PHARMACY = "PHARMACY"
    VETERINARY = "VETERINARY"
    AGRICULTURAL_RESEARCH = "AGRICULTURAL_RESEARCH"
    MARINE_BIOLOGY = "MARINE_BIOLOGY"

class ConsultationType(str, enum.Enum):
    IN_PERSON = "IN_PERSON"
    VIDEO_CALL = "VIDEO_CALL"
    AI_DIAGNOSIS = "AI_DIAGNOSIS"

class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"

class RiskLevel(str, enum.Enum):
    SAFE = "SAFE"
    MONITOR = "MONITOR"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class EmergencyType(str, enum.Enum):
    MEDICAL_CRITICAL = "MEDICAL_CRITICAL"
    BIO_HAZARD = "BIO_HAZARD"
    ATHLETIC_INJURY = "ATHLETIC_INJURY"
    VETERINARY_EMERGENCY = "VETERINARY_EMERGENCY"
    AGRICULTURAL_PLAGUE = "AGRICULTURAL_PLAGUE"
    ALGAE_BLOOM = "ALGAE_BLOOM"

class DispatchStatus(str, enum.Enum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    ON_SCENE = "ON_SCENE"
    IN_TRANSIT = "IN_TRANSIT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class BiometricSource(str, enum.Enum):
    WEARABLE = "WEARABLE"
    OPTICAL_CAMERA = "OPTICAL_CAMERA"
    MEDICAL_DEVICE = "MEDICAL_DEVICE"
    IOT_SENSOR = "IOT_SENSOR"
    DRONE_IMAGERY = "DRONE_IMAGERY"
    SATELLITE = "SATELLITE"

# ========== 1. المنشآت الصحية (مع Multi-Tenancy) ==========
class HealthFacility(Base):
    __tablename__ = "health_facilities"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    facility_category = Column(SQLEnum(FacilityCategory), nullable=False)
    supported_targets = Column(JSONB, default=list)
    specialties = Column(JSONB, default=list)
    is_active = Column(Boolean, default=True)

    facility_wallet_address = Column(String(42), nullable=True)
    on_chain_identity = Column(String(255), unique=True, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_health_facility_tenant", "tenant_id", "is_active"),
        Index("ix_health_facility_category", "tenant_id", "facility_category"),
    )


class FacilityDepartment(Base):
    __tablename__ = "facility_departments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    facility_id = Column(Integer, ForeignKey("health_facilities.id"), nullable=False, index=True)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(255), nullable=False)
    department_type = Column(String(50))
    total_beds = Column(Integer, default=0)
    available_beds = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_facility_department_created_at", "created_at"),
    )


# ========== 2. الملفات الطبية ==========
class MedicalProfile(Base):
    __tablename__ = "medical_profiles"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    target_entity_type = Column(SQLEnum(TargetEntityType), nullable=False, default=TargetEntityType.HUMAN)

    species = Column(String(100), nullable=True)
    breed = Column(String(100), nullable=True)
    plant_variety = Column(String(100), nullable=True)
    scientific_name = Column(String(255), nullable=True)

    blood_type = Column(String(10), nullable=True)
    health_score = Column(Integer, default=100)
    athletic_class = Column(String(50), nullable=True)

    chronic_diseases = Column(JSONB, default=list)
    allergies = Column(JSONB, default=list)
    current_medications = Column(JSONB, default=list)

    encrypted_ipfs_hash = Column(String(100), nullable=True)
    emergency_contact = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("health_score >= 0 AND health_score <= 100", name="check_health_score"),
        Index("ix_medical_profile_tenant_type", "tenant_id", "target_entity_type"),
        Index("ix_medical_profile_created_at", "created_at"),
    )


# ========== 3. الرصد الحيوي ==========
class BiometricLog(Base):
    __tablename__ = "biometric_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    medical_profile_id = Column(Integer, ForeignKey("medical_profiles.id"), nullable=True, index=True)
    source = Column(SQLEnum(BiometricSource), nullable=False)
    device_id = Column(String(100), nullable=True)

    aggregated_metrics = Column(JSONB, nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_biometric_logs_tenant_time", "tenant_id", "recorded_at"),
        Index("ix_biometric_logs_profile_time", "medical_profile_id", "recorded_at"),
    )


# ========== 4. تشخيص الذكاء الاصطناعي ==========
class AIHealthPrognosis(Base):
    __tablename__ = "ai_health_prognosis"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    medical_profile_id = Column(Integer, ForeignKey("medical_profiles.id"), nullable=False, index=True)

    risk_level = Column(SQLEnum(RiskLevel), nullable=False)
    predicted_condition = Column(String(255), nullable=False)
    confidence_score = Column(Numeric(5, 2), nullable=False)
    preventive_recommendations = Column(JSONB, nullable=False)

    is_acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_ai_prognosis_tenant", "tenant_id"),
        Index("ix_ai_prognosis_created_at", "created_at"),
    )


# ========== 5. الحجوزات ==========
class MedicalAppointment(Base):
    __tablename__ = "medical_appointments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    patient_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    facility_id = Column(Integer, ForeignKey("health_facilities.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("facility_departments.id"), nullable=True)

    appointment_time = Column(DateTime(timezone=True), nullable=False)
    appointment_type = Column(String(50))
    status = Column(SQLEnum(AppointmentStatus), default=AppointmentStatus.SCHEDULED)

    invoice_id = Column(Integer, nullable=True)
    payment_tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_appointment_tenant_patient", "tenant_id", "patient_user_id"),
        Index("ix_appointment_created_at", "created_at"),
        Index("ix_appointment_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


# ========== 6. الطوارئ ==========
class EmergencyDispatch(Base):
    __tablename__ = "emergency_dispatches"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    patient_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    facility_id = Column(Integer, ForeignKey("health_facilities.id"), nullable=True)

    fleet_vehicle_id = Column(Integer, nullable=True)

    emergency_type = Column(SQLEnum(EmergencyType), nullable=False)
    gps_location = Column(JSONB, nullable=False)
    vital_signs_on_route = Column(JSONB, nullable=True)

    dispatch_time = Column(DateTime(timezone=True), server_default=func.now())
    arrival_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(SQLEnum(DispatchStatus), default=DispatchStatus.PENDING)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_dispatch_tenant_status", "tenant_id", "status"),
        Index("ix_dispatch_created_at", "created_at"),
        Index("ix_dispatch_idempotency_key", "idempotency_key", unique=True, postgresql_where=text("idempotency_key IS NOT NULL")),
    )


# ========== 7. الروشتات ==========
class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    consultation_id = Column(Integer, ForeignKey("health_consultations.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    medications = Column(JSONB, nullable=False)
    doctor_notes = Column(Text, nullable=True)

    pharmacy_store_id = Column(Integer, nullable=True)
    commerce_order_id = Column(Integer, nullable=True)

    status = Column(String(50), default="ISSUED")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_prescription_tenant_patient", "tenant_id", "patient_id"),
        Index("ix_prescription_created_at", "created_at"),
    )


# ========== 8. HealthConsultation ==========
class HealthConsultation(Base):
    __tablename__ = "health_consultations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    appointment_id = Column(Integer, ForeignKey("medical_appointments.id"), nullable=False, unique=True)
    doctor_notes = Column(Text, nullable=True)
    diagnosis = Column(Text, nullable=True)
    prescription_ref = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_consultation_tenant", "tenant_id"),
        Index("ix_consultation_created_at", "created_at"),
    )