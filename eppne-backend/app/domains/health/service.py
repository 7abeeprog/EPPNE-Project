# app/domains/health/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, cast
import json
import hashlib
import httpx
import asyncio
from decimal import Decimal
import uuid

from app.domains.health.repository import HealthRepository
from app.domains.health.models import (
    MedicalProfile, BiometricLog, AIHealthPrognosis, MedicalAppointment,
    HealthConsultation, Prescription, EmergencyDispatch,
    AppointmentStatus, DispatchStatus, RiskLevel, EmergencyType, TargetEntityType,
    HealthFacility
)
from app.domains.health.schemas import (
    MedicalProfileCreate, BiometricLogCreate, MedicalAppointmentCreate,
    EmergencyDispatchCreate, HealthConsultationCreate, PrescriptionCreate,
    AIHealthPrognosisResponse
)
from app.core.errors import (
    NotFoundError, ValidationError, InsufficientBalanceError,
    IdempotencyError, SovereignError, PermissionDeniedError
)
from app.core.redis_client import redis_client
from app.core.config import settings
from app.domains.finance.service import FinanceService
from app.domains.iot.service import IoTService
from app.domains.identity.models import User
from app.core.idempotency import check_idempotency, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus


class HealthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = HealthRepository(db)
        self.finance = FinanceService(db)
        self.iot = IoTService(db)
        self.event_bus = EventBus(cast(Any, redis_client))

    # ============================================================
    # دوال مساعدة
    # ============================================================

    async def _get_user_email(self, user_id: int) -> str:
        """جلب البريد الإلكتروني للمستخدم."""
        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)
        user = await user_repo.get_user(user_id)  # type: ignore
        return user.email if user else f"user_{user_id}@eppne.com"  # type: ignore

    async def _validate_idempotency(self, idempotency_key: str, model_class) -> Optional[Any]:
        """التحقق من Idempotency وإرجاع السجل المخزن إن وجد."""
        if not idempotency_key:
            return None
        cached = await check_idempotency(idempotency_key)
        if cached:
            # نحاول جلب الكائن من قاعدة البيانات إذا كان cached يحتوي على ID
            if isinstance(cached, dict) and "id" in cached:
                return await self.repo.get_appointment(cached["id"]) if model_class == MedicalAppointment else None
            return cached
        return None

    async def _store_idempotency(self, idempotency_key: str, result: Any):
        """تخزين نتيجة Idempotency."""
        if idempotency_key:
            await store_idempotency_result(idempotency_key, result)

    # ============================================================
    # 1. الملف الطبي الشخصي (Medical Profile)
    # ============================================================

    async def get_or_create_profile(self, user_id: int, tenant_id: Optional[int] = None) -> MedicalProfile:
        """الحصول على الملف الطبي للمستخدم، وإنشاء ملف افتراضي إذا لم يكن موجوداً."""
        profile = await self.repo.get_medical_profile(user_id)
        if not profile:
            async with self.db.begin_nested():
                profile = await self.repo.create_medical_profile(
                    user_id=user_id,
                    tenant_id=tenant_id or 1,
                    target_entity_type=TargetEntityType.HUMAN,
                    health_score=100,
                    chronic_diseases=[],
                    allergies=[],
                    current_medications=[]
                )
            await self.db.commit()
        return profile

    async def update_profile(self, user_id: int, data: Dict[str, Any]) -> MedicalProfile:
        """تحديث الملف الطبي."""
        async with self.db.begin_nested():
            profile = await self.repo.update_medical_profile(user_id, **data)
        await self.db.commit()
        return profile

    # ============================================================
    # 2. البيانات الحيوية والذكاء الاصطناعي
    # ============================================================

    async def process_biometric_data(self, user_id: int, data: Dict[str, Any]) -> Dict:
        """معالجة البيانات الحيوية الواردة من الأجهزة أو التطبيقات."""
        profile = await self.get_or_create_profile(user_id)

        async with self.db.begin_nested():
            log_data = {
                "medical_profile_id": profile.id,
                "source": data.get("source"),
                "device_id": data.get("device_id"),
                "aggregated_metrics": data.get("aggregated_metrics"),
                "recorded_at": data.get("recorded_at", datetime.utcnow())
            }
            log = await self.repo.create_biometric_log(**log_data)

            metrics = data.get("aggregated_metrics", {})
            heart_rate = metrics.get("heart_rate", 70)
            health_delta = 0
            if heart_rate < 50 or heart_rate > 110:
                health_delta = -5
            elif 50 <= heart_rate <= 60 or 100 <= heart_rate <= 110:
                health_delta = -2
            else:
                health_delta = 1

            new_score = max(0, min(100, profile.health_score + health_delta))  # type: ignore
            await self.repo.update_medical_profile(user_id, health_score=new_score)

            prognosis = None
            if len(metrics) >= 3:
                prognosis = await self._call_ai_prognosis(cast(int, profile.id), metrics)

        await self.db.commit()

        return {
            "status": "success",
            "log_id": log.id,
            "new_health_score": new_score,
            "prognosis_id": prognosis.id if prognosis else None
        }

    async def _call_ai_prognosis(self, profile_id: int, metrics: Dict) -> Optional[AIHealthPrognosis]:
        """استدعاء Gemini أو نموذج مفتوح المصدر لتوقع المخاطر الصحية."""
        try:
            prompt = f"""
            بناءً على البيانات الحيوية التالية:
            {json.dumps(metrics, indent=2)}

            قم بتحديد مستوى الخطر (SAFE, MONITOR, WARNING, CRITICAL) والمرض المحتمل والتوصيات.
            أخرج JSON فقط:
            {{
                "risk_level": "SAFE|MONITOR|WARNING|CRITICAL",
                "predicted_condition": "اسم المرض أو الحالة",
                "confidence_score": 0.0-1.0,
                "preventive_recommendations": ["توصية1", "توصية2"]
            }}
            """
            gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{gemini_url}?key={settings.GOOGLE_API_KEY}",  # type: ignore
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
                    }
                )
                response.raise_for_status()
                data = response.json()
                result_text = data["candidates"][0]["content"]["parts"][0]["text"]
                result = json.loads(result_text)

                prognosis_data = {
                    "medical_profile_id": profile_id,
                    "risk_level": result.get("risk_level", RiskLevel.SAFE),
                    "predicted_condition": result.get("predicted_condition", "لا يوجد"),
                    "confidence_score": result.get("confidence_score", 0.5),
                    "preventive_recommendations": result.get("preventive_recommendations", [])
                }
                prognosis = await self.repo.create_prognosis(**prognosis_data)
                return prognosis
        except Exception as e:
            print(f"AI prognosis failed: {str(e)}")
            return None

    async def get_biometric_history(self, user_id: int, limit: int = 100) -> List[BiometricLog]:
        """جلب تاريخ البيانات الحيوية للمستخدم."""
        profile = await self.get_or_create_profile(user_id)
        return list(await self.repo.list_biometric_logs(cast(int, profile.id), limit))

    async def get_ai_prognosis(self, user_id: int) -> List[AIHealthPrognosis]:
        """جلب توقعات الذكاء الاصطناعي للمستخدم."""
        profile = await self.get_or_create_profile(user_id)
        return list(await self.repo.list_prognoses(cast(int, profile.id)))

    # ============================================================
    # 3. حجز المواعيد (Appointments)
    # ============================================================

    async def book_appointment(
        self,
        patient_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> MedicalAppointment:
        """حجز موعد طبي مع دعم Idempotency."""
        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key, MedicalAppointment)
            if cached:
                return cached

        doctor_id = data.get("doctor_id")
        facility_id = data.get("facility_id")
        appointment_time = data.get("appointment_time")

        # 2. خصم الرسوم (مع Idempotency للدفع)
        fee = Decimal("10.00")
        payment_idempotency = f"appointment_fee_{idempotency_key or uuid.uuid4().hex[:12]}"
        try:
            await self.finance.transfer(
                sender_id=patient_id,
                receiver_email="health@eppne.com",
                currency="MR_USDT",
                amount=fee,
                idempotency_key=payment_idempotency,
                notes=f"رسوم حجز موعد طبي (دكتور ID: {doctor_id})"
            )
        except InsufficientBalanceError:
            raise ValidationError("الرصيد غير كافٍ لدفع رسوم الحجز")
        except Exception as e:
            raise SovereignError(f"فشل الخصم المالي: {str(e)}")

        # 3. إنشاء الموعد في معاملة ذرية
        async with self.db.begin_nested():
            appointment_data = {
                "tenant_id": tenant_id,
                "patient_user_id": patient_id,
                "doctor_id": doctor_id,
                "facility_id": facility_id,
                "department_id": data.get("department_id"),
                "appointment_time": appointment_time,
                "appointment_type": data.get("appointment_type", "CHECKUP"),
                "status": AppointmentStatus.SCHEDULED,
                "idempotency_key": idempotency_key
            }
            appointment = await self.repo.create_appointment(**appointment_data)

            # تسجيل التدقيق
            await audit_log(
            user_id=patient_id,
            tenant_id=tenant_id,  # type: ignore
            action="JOB_CREATED",
            resource_id=job.id,  # type: ignore
            details={"title": job.title}  # type: ignore
        )

        await self.db.commit()

        # تخزين Idempotency
        if idempotency_key:
            await self._store_idempotency(idempotency_key, appointment)

        return appointment

    async def get_my_appointments(self, user_id: int, status_filter: Optional[str] = None) -> List[MedicalAppointment]:
        """جلب مواعيد المستخدم."""
        return list(await self.repo.list_appointments(user_id, status_filter))

    async def cancel_appointment(self, user_id: int, appointment_id: int) -> MedicalAppointment:
        """إلغاء موعد (مع التحقق من الملكية)."""
        appointment = await self.repo.get_appointment(appointment_id)
        if not appointment or appointment.patient_user_id != user_id:  # type: ignore
            raise NotFoundError("الموعد غير موجود")
        return await self.repo.update_appointment_status(appointment_id, AppointmentStatus.CANCELLED.value)

    # ============================================================
    # 4. الاستشارات والوصفات
    # ============================================================

    async def create_consultation(self, data: Dict[str, Any]) -> HealthConsultation:
        """إنشاء استشارة طبية بعد الموعد."""
        async with self.db.begin_nested():
            consultation = await self.repo.create_consultation(**data)
        await self.db.commit()
        return consultation

    async def get_consultation(self, consultation_id: int) -> Optional[HealthConsultation]:
        """جلب تفاصيل الاستشارة."""
        return await self.repo.get_consultation(consultation_id)

    async def create_prescription(self, data: Dict[str, Any]) -> Prescription:
        """إنشاء روشتة طبية."""
        async with self.db.begin_nested():
            consultation = await self.repo.get_consultation(cast(int, data.get("consultation_id")))
            if not consultation:
                raise NotFoundError("الاستشارة غير موجودة")

            prescription_data = {
                "tenant_id": consultation.tenant_id,  # type: ignore
                "consultation_id": consultation.id,
                "patient_id": data.get("patient_id"),
                "medications": data.get("medications"),
                "doctor_notes": data.get("doctor_notes"),
                "pharmacy_store_id": data.get("pharmacy_store_id"),
                "status": "ISSUED"
            }
            prescription = await self.repo.create_prescription(**prescription_data)
        await self.db.commit()
        return prescription

    # ============================================================
    # 5. الطوارئ (Emergency)
    # ============================================================

    async def trigger_emergency(
        self,
        caller_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> EmergencyDispatch:
        """استدعاء الطوارئ مع دعم Idempotency."""
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                # نحاول جلب الكائن من قاعدة البيانات
                if isinstance(cached, dict) and "id" in cached:
                    dispatch = await self.repo.get_dispatch(cached["id"])
                    if dispatch:
                        return dispatch
                return cast(EmergencyDispatch, cached)

        async with self.db.begin_nested():
            dispatch_data = {
                "tenant_id": tenant_id,
                "patient_id": data.get("patient_id") or caller_id,
                "facility_id": data.get("facility_id"),
                "emergency_type": data.get("emergency_type"),
                "gps_location": data.get("gps_location"),
                "vital_signs_on_route": data.get("vital_signs_on_route"),
                "status": DispatchStatus.PENDING,
                "idempotency_key": idempotency_key
            }
            dispatch = await self.repo.create_dispatch(**dispatch_data)

            await audit_log(
            user_id=caller_id,
            tenant_id=tenant_id,  # type: ignore
            action="JOB_CREATED",
            resource_id=job.id,  # type: ignore
            details={"title": job.title}  # type: ignore
        )

        await self.db.commit()

        if idempotency_key:
            await self._store_idempotency(idempotency_key, dispatch)

        return dispatch

    async def get_emergency_status(self, dispatch_id: int, user_id: int) -> Optional[EmergencyDispatch]:
        """جلب حالة بلاغ الطوارئ مع التحقق من الصلاحية."""
        dispatch = await self.repo.get_dispatch(dispatch_id)
        if not dispatch:
            return None
        if dispatch.patient_id and dispatch.patient_id != user_id:  # type: ignore
            raise PermissionDeniedError("ليس لديك صلاحية الاطلاع على هذا البلاغ")
        return dispatch

    # ============================================================
    # 6. المنشآت الصحية (Facilities)
    # ============================================================

    async def create_facility(self, user_id: int, data: Dict[str, Any]) -> HealthFacility:
        """إنشاء منشأة صحية جديدة (للمشرفين فقط)."""
        async with self.db.begin_nested():
            facility = await self.repo.create_facility(**data)
            await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="JOB_CREATED",
            resource_id=job.id,  # type: ignore
            details={"title": job.title}  # type: ignore
        )
        await self.db.commit()
        return facility

    async def list_facilities(
        self,
        tenant_id: int,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[HealthFacility]:
        """جلب قائمة المنشآت الصحية للمستأجر."""
        # نحتاج إلى تعديل دالة list_facilities في الـ Repository لتقبل tenant_id
        # لكن حالياً نمررها بدون tenant_id، سنقوم بتحسينها
        facilities = await self.repo.list_facilities(category, skip, limit)
        # تصفية حسب tenant_id (مؤقت حتى يتم تحديث الـ Repository)
        return [f for f in facilities if f.tenant_id == tenant_id]  # type: ignore

    async def get_facility(self, facility_id: int, tenant_id: int) -> Optional[HealthFacility]:
        """جلب تفاصيل منشأة صحية."""
        facility = await self.repo.get_facility(facility_id)
        if facility and facility.tenant_id != tenant_id:  # type: ignore
            raise PermissionDeniedError("ليس لديك صلاحية الاطلاع على هذه المنشأة")
        return facility

    # ============================================================
    # 7. البصمة الكربونية
    # ============================================================

    async def get_health_carbon_footprint(self, user_id: int) -> Dict:
        """حساب البصمة الكربونية للخدمات الصحية المستخدمة من قبل المستخدم."""
        profile = await self.get_or_create_profile(user_id)
        appointments = await self.repo.list_appointments(user_id)
        total_appointments = len(appointments)
        estimated_emissions = total_appointments * 0.5

        return {
            "user_id": user_id,
            "total_appointments": total_appointments,
            "estimated_carbon_emissions_kg": estimated_emissions,
            "equivalent_trees": round(estimated_emissions / 20, 2)
        }

    # ============================================================
    # 8. معالجة الأوامر الصوتية
    # ============================================================

    async def process_voice_command(self, tenant_id: int, user_id: int, text: str) -> Dict:
        """تحليل الأوامر الصوتية المتعلقة بالصحة."""
        text_lower = text.lower()
        if "موعد" in text_lower or "حجز" in text_lower:
            return {
                "intent": "CREATE_APPOINTMENT",
                "sector": "health",
                "action": "book_appointment",
                "payload": {
                    "doctor_id": 1,
                    "facility_id": 1,
                    "appointment_time": datetime.utcnow() + timedelta(days=2)
                }
            }
        elif "قراءة" in text_lower and "كربون" in text_lower:
            return {
                "intent": "READ_CARBON_FOOTPRINT",
                "sector": "health",
                "action": "get_health_carbon_footprint",
                "payload": {}
            }
        elif "طوارئ" in text_lower:
            return {
                "intent": "CREATE_EMERGENCY",
                "sector": "health",
                "action": "trigger_emergency",
                "payload": {
                    "emergency_type": EmergencyType.MEDICAL_CRITICAL,
                    "gps_location": {"lat": 30.0, "lng": 31.0}
                }
            }
        else:
            return {"intent": "UNKNOWN", "sector": "health", "action": "unknown", "payload": {}}