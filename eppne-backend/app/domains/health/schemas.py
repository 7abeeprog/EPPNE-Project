# app/domains/health/schemas.py
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.health.models import (
    FacilityCategory, ConsultationType, AppointmentStatus, RiskLevel,
    EmergencyType, DispatchStatus, BiometricSource, TargetEntityType
)


# ============================================================
# المنشآت الصحية (Facilities)
# ============================================================

class HealthFacilityCreate(BaseModel):
    name: str = Field(description="اسم المنشأة")
    facility_category: FacilityCategory = Field(description="تصنيف المنشأة")
    specialties: List[str] = Field(default_factory=list, description="التخصصات")
    facility_wallet_address: Optional[str] = Field(
        default=None,
        pattern="^0x[a-fA-F0-9]{40}$",
        description="عنوان المحفظة"
    )


class HealthFacilityResponse(HealthFacilityCreate):
    id: int
    entity_id: Optional[int]
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# الملف الطبي (Medical Profile)
# ============================================================

class MedicalProfileCreate(BaseModel):
    blood_type: Optional[str] = Field(default=None, description="فصيلة الدم")
    health_score: int = Field(default=100, ge=0, le=100, description="النقاط الصحية")
    athletic_class: Optional[str] = Field(default=None, description="الفئة الرياضية")
    chronic_diseases: List[str] = Field(default_factory=list, description="الأمراض المزمنة")
    allergies: List[str] = Field(default_factory=list, description="الحساسية")
    current_medications: List[str] = Field(default_factory=list, description="الأدوية الحالية")
    emergency_contact: Optional[str] = Field(default=None, description="جهة الاتصال في الطوارئ")


class MedicalProfileResponse(MedicalProfileCreate):
    id: int
    user_id: int
    encrypted_ipfs_hash: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# البيانات الحيوية والذكاء الاصطناعي
# ============================================================

class BiometricLogCreate(BaseModel):
    source: BiometricSource = Field(description="مصدر البيانات")
    device_id: Optional[str] = Field(default=None, description="معرف الجهاز")
    aggregated_metrics: Dict[str, Any] = Field(description="المقاييس المجمعة")
    recorded_at: datetime = Field(description="وقت التسجيل")


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


# ============================================================
# المواعيد الطبية (Appointments)
# ============================================================

class MedicalAppointmentCreate(BaseModel):
    doctor_id: int = Field(description="معرف الطبيب")
    facility_id: int = Field(description="معرف المنشأة")
    department_id: Optional[int] = Field(default=None, description="معرف القسم")
    appointment_time: datetime = Field(description="وقت الموعد")
    appointment_type: str = Field(default="CHECKUP", description="نوع الموعد")


class MedicalAppointmentResponse(MedicalAppointmentCreate):
    id: int
    patient_user_id: int
    status: AppointmentStatus
    payment_tx_hash: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class HealthConsultationCreate(BaseModel):
    appointment_id: int = Field(description="معرف الموعد")
    doctor_notes: Optional[str] = Field(default=None, description="ملاحظات الطبيب")
    diagnosis: Optional[str] = Field(default=None, description="التشخيص")
    prescription_ref: Optional[str] = Field(default=None, description="مرجع الروشتة")


class HealthConsultationResponse(HealthConsultationCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PrescriptionCreate(BaseModel):
    consultation_id: int = Field(description="معرف الاستشارة")
    medications: List[Dict[str, Any]] = Field(description="قائمة الأدوية")
    doctor_notes: Optional[str] = Field(default=None, description="ملاحظات الطبيب")
    pharmacy_store_id: Optional[int] = Field(default=None, description="معرف الصيدلية")


class PrescriptionResponse(PrescriptionCreate):
    id: int
    patient_id: int
    status: str
    commerce_order_id: Optional[int]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# الطوارئ (Emergency)
# ============================================================

class EmergencyDispatchCreate(BaseModel):
    patient_id: Optional[int] = Field(default=None, description="معرف المريض")
    facility_id: Optional[int] = Field(default=None, description="معرف المنشأة المستهدفة")
    emergency_type: EmergencyType = Field(description="نوع الطوارئ")
    gps_location: Dict[str, float] = Field(description="الموقع الجغرافي")
    vital_signs_on_route: Optional[Dict[str, Any]] = Field(default=None, description="العلامات الحيوية")


class EmergencyDispatchResponse(EmergencyDispatchCreate):
    id: int
    dispatch_time: datetime
    arrival_time: Optional[datetime]
    status: DispatchStatus
    model_config = ConfigDict(from_attributes=True)