# app/domains/health/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
import hashlib
import httpx
import asyncio
from decimal import Decimal

from app.domains.health.repository import HealthRepository
from app.domains.health.models import (
    MedicalProfile, BiometricLog, AIHealthPrognosis, MedicalAppointment,
    HealthConsultation, Prescription, EmergencyDispatch,
    AppointmentStatus, DispatchStatus, RiskLevel, EmergencyType, TargetEntityType
)
from app.domains.health.schemas import (
    MedicalProfileCreate, BiometricLogCreate, MedicalAppointmentCreate,
    EmergencyDispatchCreate, HealthConsultationCreate, PrescriptionCreate,
    AIHealthPrognosisResponse
)
from app.core.errors import (
    NotFoundError, ValidationError, InsufficientBalanceError,
    IdempotencyError, SovereignError
)
from app.core.redis_client import redis_client
from app.core.config import settings
from app.domains.finance.service import FinanceService
from app.domains.iot.service import IoTService  # للبصمة الكربونية
from app.domains.identity.models import User


class HealthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = HealthRepository(db)
        self.finance = FinanceService(db)
        self.iot = IoTService(db)

    # ==========================================================
    # المساعدات الخاصة
    # ==========================================================
    async def _get_idempotency(self, key: str, table_model) -> Optional[Dict]:
        """التحقق من وجود مفتاح Idempotency في قاعدة البيانات"""
        if not key:
            return None
        # نبحث في الجدول المحدد عن سجل بنفس المفتاح
        result = await self.db.execute(
            select(table_model).where(table_model.idempotency_key == key)
        )
        record = result.scalar_one_or_none()
        if record:
            # نعيد البيانات كمصفوفة (dict) مع حذف المفتاح
            return {c.name: getattr(record, c.name) for c in record.__table__.columns}
        return None

    async def _save_idempotency(self, key: str, instance):
        """حفظ مفتاح Idempotency (يُضاف تلقائياً عند إنشاء السجل)"""
        # المفتاح يُحفظ عبر الـ repository في حقل idempotency_key
        pass  # يتم التعامل معه ضمن إنشاء السجل

    # ==========================================================
    # 1. الملف الطبي الشخصي (Medical Profile)
    # ==========================================================
    async def get_or_create_profile(self, user_id: int) -> MedicalProfile:
        """الحصول على الملف الطبي للمستخدم، وإنشاء ملف افتراضي إذا لم يكن موجوداً"""
        profile = await self.repo.get_medical_profile(user_id)
        if not profile:
            # إنشاء ملف طبي افتراضي
            async with self.db.begin():
                profile = await self.repo.create_medical_profile(
                    user_id=user_id,
                    target_entity_type=TargetEntityType.HUMAN,
                    health_score=100,
                    chronic_diseases=[],
                    allergies=[],
                    current_medications=[]
                )
        return profile

    async def update_profile(self, user_id: int, data: MedicalProfileCreate) -> MedicalProfile:
        """تحديث الملف الطبي"""
        async with self.db.begin():
            profile = await self.repo.update_medical_profile(user_id, **data.model_dump())
            return profile

    # ==========================================================
    # 2. البيانات الحيوية والذكاء الاصطناعي
    # ==========================================================
    async def process_biometric_data(self, user_id: int, data: Dict[str, Any]) -> Dict:
        """
        معالجة البيانات الحيوية الواردة من الأجهزة أو التطبيقات.
        - تخزين السجل.
        - تحديث النقاط الصحية (Health Score).
        - استدعاء نموذج الذكاء الاصطناعي (Gemini) لتوقع المخاطر.
        """
        # الحصول على الملف الطبي
        profile = await self.get_or_create_profile(user_id)

        async with self.db.begin():
            # 1. تخزين السجل الحيوي
            log_data = {
                "medical_profile_id": profile.id,
                "source": data.get("source"),
                "device_id": data.get("device_id"),
                "aggregated_metrics": data.get("aggregated_metrics"),
                "recorded_at": data.get("recorded_at", datetime.utcnow())
            }
            log = await self.repo.create_biometric_log(**log_data)

            # 2. تحديث النقاط الصحية (معادلة بسيطة)
            # يمكننا تحليل المقاييس مثل معدل ضربات القلب، الضغط، النشاط
            metrics = data.get("aggregated_metrics", {})
            heart_rate = metrics.get("heart_rate", 70)
            # مثال: إذا كان معدل الضربات خارج النطاق الطبيعي (60-100) نخفض النقاط
            health_delta = 0
            if heart_rate < 50 or heart_rate > 110:
                health_delta = -5
            elif 50 <= heart_rate <= 60 or 100 <= heart_rate <= 110:
                health_delta = -2
            else:
                health_delta = 1  # تحسن طفيف

            new_score = max(0, min(100, profile.health_score + health_delta))
            await self.repo.update_medical_profile(user_id, health_score=new_score)

            # 3. استدعاء الذكاء الاصطناعي لتوقع المخاطر (إذا توفرت بيانات كافية)
            prognosis = None
            if len(metrics) >= 3:  # على الأقل 3 مقاييس
                prognosis = await self._call_ai_prognosis(profile.id, metrics)

            return {
                "status": "success",
                "log_id": log.id,
                "new_health_score": new_score,
                "prognosis_id": prognosis.id if prognosis else None
            }

    async def _call_ai_prognosis(self, profile_id: int, metrics: Dict) -> Optional[AIHealthPrognosis]:
        """استدعاء Gemini أو نموذج مفتوح المصدر لتوقع المخاطر الصحية"""
        # محاكاة بسيطة - يمكن استبدالها بـ Gemini أو LLaMA
        try:
            # بناء الطلب
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
            # هنا نستدعي Gemini (نستخدم نفس الكود من قطاع الترجمة)
            gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{gemini_url}?key={settings.GOOGLE_API_KEY}",
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
                    }
                )
                response.raise_for_status()
                data = response.json()
                result_text = data["candidates"][0]["content"]["parts"][0]["text"]
                result = json.loads(result_text)

                # حفظ التوقع
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
            # في حالة فشل الذكاء الاصطناعي، نستمر دون توقع
            print(f"AI prognosis failed: {str(e)}")
            return None

    # ==========================================================
    # 3. حجز المواعيد (مع Idempotency)
    # ==========================================================
    async def book_appointment(
        self,
        patient_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> MedicalAppointment:
        """
        حجز موعد طبي مع دعم Idempotency ومنع التكرار.
        """
        # 1. التحقق من Idempotency
        if idempotency_key:
            existing = await self._get_idempotency(idempotency_key, MedicalAppointment)
            if existing:
                # إعادة السجل المخزن سابقاً (نحوله إلى كائن MedicalAppointment)
                return await self.repo.get_appointment(existing["id"])

        # 2. التحقق من صحة البيانات (وجود الطبيب والمنشأة)
        doctor_id = data.get("doctor_id")
        facility_id = data.get("facility_id")
        appointment_time = data.get("appointment_time")

        # يمكننا التحقق من وجود الطبيب والمنشأة في قاعدة البيانات (نفترض وجودهما)

        # 3. خصم الرسوم (إذا كانت هناك رسوم)
        fee = Decimal("10.00")  # مثال: 10 MRUSDT رسوم الحجز
        try:
            await self.finance.debit(
                user_id=patient_id,
                currency="MR_USDT",
                amount=fee,
                description=f"رسوم حجز موعد طبي (دكتور ID: {doctor_id})"
            )
        except InsufficientBalanceError:
            raise ValidationError("الرصيد غير كافٍ لدفع رسوم الحجز")
        except Exception as e:
            raise SovereignError(f"فشل الخصم المالي: {str(e)}")

        # 4. إنشاء الموعد في معاملة ذرية
        async with self.db.begin():
            appointment_data = {
                "tenant_id": tenant_id,
                "patient_user_id": patient_id,
                "doctor_id": doctor_id,
                "facility_id": facility_id,
                "department_id": data.get("department_id"),
                "appointment_time": appointment_time,
                "appointment_type": data.get("appointment_type", "CHECKUP"),
                "status": AppointmentStatus.SCHEDULED,
                "idempotency_key": idempotency_key  # حفظ المفتاح
            }
            appointment = await self.repo.create_appointment(**appointment_data)

            # تسجيل التدقيق (يمكن إضافته)
            return appointment

    # ==========================================================
    # 4. الطوارئ (مع Idempotency)
    # ==========================================================
    async def trigger_emergency(
        self,
        caller_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> EmergencyDispatch:
        """
        استدعاء الطوارئ مع دعم Idempotency.
        """
        # 1. التحقق من Idempotency
        if idempotency_key:
            existing = await self._get_idempotency(idempotency_key, EmergencyDispatch)
            if existing:
                return await self.repo.get_dispatch(existing["id"])

        # 2. إنشاء بلاغ الطوارئ
        async with self.db.begin():
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

            # 3. إرسال إشعارات للمسعفين (يمكن تنفيذها عبر WebSocket أو RabbitMQ)
            # ...

            return dispatch

    # ==========================================================
    # 5. الاستشارات والوصفات
    # ==========================================================
    async def create_consultation(self, data: Dict[str, Any]) -> HealthConsultation:
        """إنشاء استشارة طبية بعد الموعد"""
        async with self.db.begin():
            consultation = await self.repo.create_consultation(**data)
            return consultation

    async def create_prescription(self, data: Dict[str, Any]) -> Prescription:
        """إنشاء روشتة طبية"""
        async with self.db.begin():
            # التحقق من وجود الاستشارة
            consultation = await self.repo.get_consultation(data.get("consultation_id"))
            if not consultation:
                raise NotFoundError("الاستشارة غير موجودة")

            # إنشاء الروشتة
            prescription_data = {
                "tenant_id": consultation.tenant_id,  # نأخذ من الاستشارة
                "consultation_id": consultation.id,
                "patient_id": data.get("patient_id"),
                "medications": data.get("medications"),
                "doctor_notes": data.get("doctor_notes"),
                "pharmacy_store_id": data.get("pharmacy_store_id"),
                "status": "ISSUED"
            }
            prescription = await self.repo.create_prescription(**prescription_data)

            # ربط الروشتة بقطاع التجارة (لطلب الأدوية)
            # يمكن استدعاء CommerceService لإنشاء طلب شراء
            # ...

            return prescription

    # ==========================================================
    # 6. دمج البصمة الكربونية (مع قطاع IoT)
    # ==========================================================
    async def get_health_carbon_footprint(self, user_id: int) -> Dict:
        """
        حساب البصمة الكربونية للخدمات الصحية المستخدمة من قبل المستخدم.
        (مثال: عدد المواعيد، العمليات، الأدوية)
        """
        profile = await self.get_or_create_profile(user_id)

        # الحصول على عدد المواعيد والاستشارات
        appointments = await self.repo.list_appointments(user_id)
        total_appointments = len(appointments)

        # كل موعد ينتج بصمة كربونية تقريبية (0.5 كجم CO2)
        estimated_emissions = total_appointments * 0.5

        return {
            "user_id": user_id,
            "total_appointments": total_appointments,
            "estimated_carbon_emissions_kg": estimated_emissions,
            "equivalent_trees": round(estimated_emissions / 20, 2)  # شجرة تمتص 20 كجم سنوياً
        }

    # ==========================================================
    # 7. التكامل مع المساعد الصوتي (Voice Commands)
    # ==========================================================
    async def process_voice_command(self, tenant_id: int, user_id: int, text: str) -> Dict:
        """
        تحليل الأوامر الصوتية المتعلقة بالصحة (تُستدعى من قطاع Voice Assistant).
        """
        text_lower = text.lower()
        if "موعد" in text_lower or "حجز" in text_lower:
            # استخراج بيانات الموعد من النص (يمكن استخدام Gemini لتحليل أكثر دقة)
            # محاكاة بسيطة
            return {
                "intent": "CREATE_APPOINTMENT",
                "sector": "health",
                "action": "book_appointment",
                "payload": {
                    "doctor_id": 1,  # سيتم استخراجه
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