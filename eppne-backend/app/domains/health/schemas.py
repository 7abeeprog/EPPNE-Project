from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.health.models import FacilityCategory, ConsultationType, AppointmentStatus, RiskLevel, EmergencyType, DispatchStatus, BiometricSource

# ========== Facilities ==========
class HealthFacilityCreate(BaseModel):
    name: str
    facility_category: FacilityCategory
    specialties: List[str] = []
    facility_wallet_address: Optional[str] = Field(None, pattern="^0x[a-fA-F0-9]{40}$")

class HealthFacilityResponse(HealthFacilityCreate):
    id: int
    entity_id: Optional[int]
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Medical Profile ==========
class MedicalProfileCreate(BaseModel):
    blood_type: Optional[str] = None
    health_score: int = 100
    athletic_class: Optional[str] = None
    chronic_diseases: List[str] = []
    allergies: List[str] = []
    current_medications: List[str] = []
    emergency_contact: Optional[str] = None

class MedicalProfileResponse(MedicalProfileCreate):
    id: int
    user_id: int
    encrypted_ipfs_hash: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Biometric & AI ==========
class BiometricLogCreate(BaseModel):
    source: BiometricSource
    device_id: Optional[str] = None
    aggregated_metrics: Dict[str, Any]
    recorded_at: datetime

class BiometricLogResponse(BiometricLogCreate):
    id: int
    medical_profile_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AIHealthPrognosisResponse(BaseModel):
    id: int
    risk_level: RiskLevel
    predicted_condition: str
    confidence_score: float
    preventive_recommendations: Dict[str, Any]
    is_acknowledged: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Appointments ==========
class MedicalAppointmentCreate(BaseModel):
    doctor_id: int
    facility_id: int
    department_id: Optional[int] = None
    appointment_time: datetime
    appointment_type: str = "CHECKUP"

class MedicalAppointmentResponse(MedicalAppointmentCreate):
    id: int
    patient_user_id: int
    status: AppointmentStatus
    payment_tx_hash: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class HealthConsultationCreate(BaseModel):
    appointment_id: int
    doctor_notes: Optional[str] = None
    diagnosis: Optional[str] = None
    prescription_ref: Optional[str] = None

class HealthConsultationResponse(HealthConsultationCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PrescriptionCreate(BaseModel):
    consultation_id: int
    medications: List[Dict[str, Any]]
    doctor_notes: Optional[str] = None
    pharmacy_store_id: Optional[int] = None

class PrescriptionResponse(PrescriptionCreate):
    id: int
    patient_id: int
    status: str
    commerce_order_id: Optional[int]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Emergency ==========
class EmergencyDispatchCreate(BaseModel):
    patient_id: Optional[int] = None
    facility_id: Optional[int] = None
    emergency_type: EmergencyType
    gps_location: Dict[str, float]
    vital_signs_on_route: Optional[Dict[str, Any]] = None

class EmergencyDispatchResponse(EmergencyDispatchCreate):
    id: int
    dispatch_time: datetime
    arrival_time: Optional[datetime]
    status: DispatchStatus
    model_config = ConfigDict(from_attributes=True)