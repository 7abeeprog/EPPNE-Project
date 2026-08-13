from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from typing import Optional, List
from datetime import datetime

from app.domains.health.models import *
from app.core.errors import NotFoundError

class HealthRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- Facilities ----------
    async def create_facility(self, **kwargs) -> HealthFacility:
        facility = HealthFacility(**kwargs)
        self.db.add(facility)
        await self.db.flush()
        await self.db.refresh(facility)
        return facility

    async def get_facility(self, facility_id: int) -> Optional[HealthFacility]:
        result = await self.db.execute(select(HealthFacility).where(HealthFacility.id == facility_id))
        return result.scalar_one_or_none()

    async def list_facilities(self, category: Optional[str] = None, skip=0, limit=100):
        query = select(HealthFacility).where(HealthFacility.is_active == True)
        if category:
            query = query.where(HealthFacility.facility_category == category)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    # ---------- Medical Profiles ----------
    async def get_medical_profile(self, user_id: int) -> Optional[MedicalProfile]:
        result = await self.db.execute(select(MedicalProfile).where(MedicalProfile.user_id == user_id))
        return result.scalar_one_or_none()

    async def create_medical_profile(self, user_id: int, **kwargs) -> MedicalProfile:
        profile = MedicalProfile(user_id=user_id, **kwargs)
        self.db.add(profile)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    async def update_medical_profile(self, user_id: int, **kwargs) -> MedicalProfile:
        profile = await self.get_medical_profile(user_id)
        if not profile:
            raise NotFoundError("Medical profile not found")
        for key, value in kwargs.items():
            setattr(profile, key, value)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    # ---------- Biometric & AI ----------
    async def create_biometric_log(self, **kwargs) -> BiometricLog:
        log = BiometricLog(**kwargs)
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log

    async def list_biometric_logs(self, medical_profile_id: int, limit=100):
        result = await self.db.execute(
            select(BiometricLog).where(BiometricLog.medical_profile_id == medical_profile_id)
            .order_by(BiometricLog.recorded_at.desc()).limit(limit)
        )
        return result.scalars().all()

    async def create_prognosis(self, **kwargs) -> AIHealthPrognosis:
        prognosis = AIHealthPrognosis(**kwargs)
        self.db.add(prognosis)
        await self.db.flush()
        await self.db.refresh(prognosis)
        return prognosis

    async def list_prognoses(self, medical_profile_id: int):
        result = await self.db.execute(
            select(AIHealthPrognosis).where(AIHealthPrognosis.medical_profile_id == medical_profile_id)
            .order_by(AIHealthPrognosis.created_at.desc())
        )
        return result.scalars().all()

    # ---------- Appointments & Consultations ----------
    async def create_appointment(self, **kwargs) -> MedicalAppointment:
        appointment = MedicalAppointment(**kwargs)
        self.db.add(appointment)
        await self.db.flush()
        await self.db.refresh(appointment)
        return appointment

    async def get_appointment(self, appointment_id: int) -> Optional[MedicalAppointment]:
        result = await self.db.execute(select(MedicalAppointment).where(MedicalAppointment.id == appointment_id))
        return result.scalar_one_or_none()

    async def list_appointments(self, user_id: int, status: Optional[str] = None):
        query = select(MedicalAppointment).where(MedicalAppointment.patient_user_id == user_id)
        if status:
            query = query.where(MedicalAppointment.status == status)
        query = query.order_by(MedicalAppointment.appointment_time)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_appointment_status(self, appointment_id: int, status: str) -> MedicalAppointment:
        await self.db.execute(update(MedicalAppointment).where(MedicalAppointment.id == appointment_id).values(status=status))
        await self.db.commit()
        return await self.get_appointment(appointment_id)

    async def create_consultation(self, **kwargs) -> HealthConsultation:
        consultation = HealthConsultation(**kwargs)
        self.db.add(consultation)
        await self.db.flush()
        await self.db.refresh(consultation)
        return consultation

    async def get_consultation(self, consultation_id: int) -> Optional[HealthConsultation]:
        result = await self.db.execute(select(HealthConsultation).where(HealthConsultation.id == consultation_id))
        return result.scalar_one_or_none()

    # ---------- Prescriptions ----------
    async def create_prescription(self, **kwargs) -> Prescription:
        prescription = Prescription(**kwargs)
        self.db.add(prescription)
        await self.db.flush()
        await self.db.refresh(prescription)
        return prescription

    # ---------- Emergency ----------
    async def create_dispatch(self, **kwargs) -> EmergencyDispatch:
        dispatch = EmergencyDispatch(**kwargs)
        self.db.add(dispatch)
        await self.db.flush()
        await self.db.refresh(dispatch)
        return dispatch

    async def get_dispatch(self, dispatch_id: int) -> Optional[EmergencyDispatch]:
        result = await self.db.execute(select(EmergencyDispatch).where(EmergencyDispatch.id == dispatch_id))
        return result.scalar_one_or_none()

    async def update_dispatch_status(self, dispatch_id: int, status: str, arrival_time: datetime = None) -> EmergencyDispatch:
        values = {"status": status}
        if arrival_time:
            values["arrival_time"] = arrival_time
        await self.db.execute(update(EmergencyDispatch).where(EmergencyDispatch.id == dispatch_id).values(**values))
        await self.db.commit()
        return await self.get_dispatch(dispatch_id)