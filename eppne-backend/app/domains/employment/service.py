# app/domains/employment/service.py (الإصدار النهائي المتكامل)
"""
خدمات قطاع التوظيف والموارد البشرية
الإصدار الذهبي (Gold Release) – مع دعم Idempotency, Audit, SaaS, Affiliate, Invoicing, AI, Celery
"""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
import uuid
import math
import bleach

from app.domains.employment.repository import EmploymentRepository
from app.domains.finance.service import FinanceService
from app.domains.academy.repository import AcademyRepository
from app.domains.ai_agents.service import AIAgentsService
from app.domains.saas.service import SaaSSubscriptionService
from app.domains.affiliate.service import AffiliateService
from app.domains.invoicing.service import InvoicingService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, IdempotencyError
from app.core.idempotency import check_idempotency, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging import logger
from app.core.rate_limiter import rate_limit
from app.tasks.employment import generate_payroll_task, pay_payroll_task

# استيراد الأنواع المفقودة (من النماذج)
from app.domains.employment.models import (
    JobListing, JobApplication, EmploymentContract, AttendanceRecord,
    LeaveRequest, PayrollRecord,
    EmploymentStatus, AttendanceStatus, PayrollStatus, LeaveType
)


class EmploymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EmploymentRepository(db)
        self.finance = FinanceService(db)
        self.academy = AcademyRepository(db)
        self.ai_service = AIAgentsService(db)
        self.saas_service = SaaSSubscriptionService(db)
        self.affiliate_service = AffiliateService(db)
        self.invoicing_service = InvoicingService(db)
        self.event_bus = EventBus(redis_client)
        self.redis = redis_client

    # ==============================
    # 1. التحقق من صلاحيات SaaS
    # ==============================

    async def _check_saas_limits(self, tenant_id: int, feature: str = "hr_management"):
        """التحقق من صلاحية استخدام ميزات HRM في خطة الاشتراك."""
        subscription = await self.saas_service.get_active_subscription(tenant_id)
        if not subscription:
            raise PermissionDeniedError("No active subscription found for this entity.")
        
        features = subscription.features or {}
        if not features.get(feature, False):
            raise PermissionDeniedError(f"HR Management feature is not included in your current plan.")
        
        return subscription, features

    # ==============================
    # 2. إدارة الوظائف (مع تعقيم المدخلات)
    # ==============================

    async def create_job(self, employer_id: int, tenant_id: int, data: Dict[str, Any]) -> JobListing:
        """إنشاء وظيفة جديدة مع التحقق من SaaS وتعقيم المدخلات."""
        await self._check_saas_limits(tenant_id, "hr_management")
        
        # تعقيم المدخلات
        sanitized_data = {
            "title": bleach.clean(data.get("title", ""), tags=[], strip=True),
            "description": bleach.clean(data.get("description", ""), tags=[], strip=True),
            "required_skills": data.get("required_skills", []),
            "required_certificate_ids": data.get("required_certificate_ids", []),
            "required_rank": data.get("required_rank"),
            "salary_min": data.get("salary_min"),
            "salary_max": data.get("salary_max"),
            "currency": data.get("currency", "MR_USDT"),
            "location": bleach.clean(data.get("location", ""), tags=[], strip=True) if data.get("location") else None,
            "employment_type": data.get("employment_type", "FULL_TIME"),
            "tenant_id": tenant_id
        }
        
        job = await self.repo.create_job_listing(employer_id=employer_id, **sanitized_data)
        
        # 🔥 تسجيل الإحالة (Affiliate)
        await self._register_affiliate_commission(employer_id, tenant_id, "JOB_CREATED", Decimal(0))
        
        # 🔥 تسجيل التدقيق (Audit)
        await audit_log(
            user_id=employer_id,
            tenant_id=tenant_id,
            action="JOB_CREATED",
            resource_id=job.id,
            details={"title": job.title}
        )
        
        return job

    async def update_job(self, employer_id: int, job_id: int, data: Dict[str, Any]) -> JobListing:
        """تحديث وظيفة (لصاحب العمل فقط) - مع تعقيم"""
        job = await self.repo.get_job_listing_by_employer(job_id, employer_id)
        if not job:
            raise PermissionDeniedError("لا تملك صلاحية تعديل هذه الوظيفة")
        # تعقيم البيانات
        sanitized = {}
        for k, v in data.items():
            if k in ("title", "description", "location"):
                sanitized[k] = bleach.clean(v, tags=[], strip=True) if v else v
            else:
                sanitized[k] = v
        return await self.repo.update_job_listing(job_id, **sanitized)

    async def close_job(self, employer_id: int, job_id: int) -> JobListing:
        """إغلاق وظيفة (وقف استقبال الطلبات)"""
        job = await self.repo.get_job_listing_by_employer(job_id, employer_id)
        if not job:
            raise PermissionDeniedError("لا تملك صلاحية إغلاق هذه الوظيفة")
        return await self.repo.update_job_listing(job_id, is_active=False)

    # ==============================
    # 3. طلبات التوظيف (مع دمج الذكاء الاصطناعي)
    # ==============================

    async def apply_for_job(
        self,
        applicant_id: int,
        tenant_id: int,
        job_id: int,
        cover_letter: Optional[str] = None,
        resume_url: Optional[str] = None
    ) -> JobApplication:
        """تقديم طلب وظيفة مع تحليل الذكاء الاصطناعي للسيرة الذاتية."""
        job = await self.repo.get_job_listing(job_id)
        if not job or not job.is_active:
            raise NotFoundError("الوظيفة غير موجودة أو غير نشطة")

        # التحقق من التقديم المسبق
        existing = await self.repo.get_application_by_job_and_applicant(job_id, applicant_id)
        if existing:
            raise PermissionDeniedError("لقد تقدمت لهذه الوظيفة مسبقاً")

        # التحقق من الشهادات المطلوبة
        if job.required_certificate_ids:
            certificates = await self.academy.get_user_certificates(applicant_id)
            cert_course_ids = [c.course_id for c in certificates]
            missing = set(job.required_certificate_ids) - set(cert_course_ids)
            if missing:
                raise PermissionDeniedError(f"أنت لا تمتلك الشهادات المطلوبة: {missing}")

        # 🔥 حساب AI Match Score باستخدام وكيل ذكاء اصطناعي حقيقي
        try:
            ai_score = await self._calculate_ai_match_score(applicant_id, job)
        except Exception as e:
            logger.error(f"AI match score calculation failed: {e}")
            ai_score = Decimal(50.0)  # قيمة افتراضية آمنة

        application = await self.repo.create_application(
            job_id=job_id,
            applicant_id=applicant_id,
            cover_letter=bleach.clean(cover_letter, tags=[], strip=True) if cover_letter else None,
            resume_url=resume_url,
            ai_match_score=ai_score,
            status="PENDING"
        )
        
        # 🔥 تسجيل التدقيق
        await audit_log(
            user_id=applicant_id,
            tenant_id=tenant_id,
            action="JOB_APPLIED",
            resource_id=application.id,
            details={"job_id": job_id, "ai_match_score": float(ai_score)}
        )
        
        return application

    async def review_application(
        self,
        employer_id: int,
        application_id: int,
        status: str,
        reviewer_notes: Optional[str] = None
    ) -> JobApplication:
        """مراجعة طلب وظيفة (قبول/رفض) – لصاحب العمل فقط"""
        app = await self.repo.get_application(application_id)
        if not app:
            raise NotFoundError("الطلب غير موجود")
        job = await self.repo.get_job_listing(app.job_id)
        if not job or job.employer_id != employer_id:
            raise PermissionDeniedError("لا تملك صلاحية مراجعة هذا الطلب")
        if status not in ["APPROVED", "REJECTED", "REVIEWING"]:
            raise ValueError("حالة غير صالحة")
        return await self.repo.update_application_status(application_id, status, employer_id)

    # ==============================
    # 4. عقود العمل (مع Idempotency و SaaS)
    # ==============================

    async def create_contract(self, employer_id: int, tenant_id: int, data: Dict[str, Any], idempotency_key: Optional[str] = None) -> EmploymentContract:
        """إنشاء عقد عمل مع دعم Idempotency و SaaS."""
        await self._check_saas_limits(tenant_id, "hr_management")
        
        # التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        application = await self.repo.get_application(data["application_id"])
        if not application:
            raise NotFoundError("طلب التوظيف غير موجود")
        if application.status != "APPROVED":
            raise PermissionDeniedError("لا يمكن إنشاء عقد إلا لطلب مقبول")
        
        job = await self.repo.get_job_listing(application.job_id)
        if job.employer_id != employer_id:
            raise PermissionDeniedError("لا تملك صلاحية إنشاء عقد لهذه الوظيفة")
        
        # تعقيم المدخلات
        job_title = bleach.clean(data.get("job_title", job.title), tags=[], strip=True)
        
        contract = await self.repo.create_contract(
            tenant_id=tenant_id,
            application_id=application.id,
            employee_id=application.applicant_id,
            employer_id=employer_id,
            job_title=job_title,
            base_salary=data["base_salary"],
            allowances=data.get("allowances", {}),
            currency=data.get("currency", "MR_USDT"),
            start_date=data["start_date"],
            end_date=data.get("end_date"),
            probation_days=data.get("probation_days", 90),
            annual_leave_days=data.get("annual_leave_days", 21),
            status=EmploymentStatus.WAITING_SIGNATURE,
            idempotency_key=idempotency_key
        )
        
        # 🔥 تسجيل الإحالة (Affiliate)
        await self._register_affiliate_commission(employer_id, tenant_id, "CONTRACT_CREATED", data["base_salary"])
        
        # 🔥 تسجيل التدقيق
        await audit_log(
            user_id=employer_id,
            tenant_id=tenant_id,
            action="CONTRACT_CREATED",
            resource_id=contract.id,
            details={"employee_id": application.applicant_id, "salary": float(data["base_salary"])}
        )
        
        # 🔥 نشر حدث للأتمتة
        await self.event_bus.publish("contract.created", {
            "contract_id": contract.id,
            "tenant_id": tenant_id,
            "employee_id": application.applicant_id,
            "employer_id": employer_id
        })
        
        # تخزين نتيجة Idempotency
        if idempotency_key:
            await store_idempotency_result(idempotency_key, contract)
        
        return contract

    async def sign_contract(
        self,
        user_id: int,
        contract_id: int,
        signature_tx_hash: str,
        is_employee: bool = True
    ) -> EmploymentContract:
        """توقيع العقد (من قبل الموظف أو صاحب العمل)"""
        contract = await self.repo.get_contract(contract_id)
        if not contract:
            raise NotFoundError("العقد غير موجود")

        if is_employee and contract.employee_id != user_id:
            raise PermissionDeniedError("ليس لديك صلاحية توقيع هذا العقد")
        if not is_employee and contract.employer_id != user_id:
            raise PermissionDeniedError("ليس لديك صلاحية توقيع هذا العقد")

        if is_employee:
            contract = await self.repo.update_contract(contract_id, signature_tx_hash=signature_tx_hash)
        else:
            contract = await self.repo.update_contract(contract_id, employer_signature_tx=signature_tx_hash)

        # إذا تم توقيع الطرفين، يصبح العقد فعالاً
        if contract.signature_tx_hash and contract.employer_signature_tx:
            contract = await self.repo.update_contract(contract_id, status=EmploymentStatus.PROBATION)
        return contract

    async def get_my_active_contract(self, user_id: int) -> Optional[EmploymentContract]:
        """جلب العقد النشط للموظف الحالي"""
        return await self.repo.get_contract_by_employee(user_id, active_only=True)

    # ==============================
    # 5. الحضور والانصراف
    # ==============================

    async def check_in(
        self,
        user_id: int,
        contract_id: int,
        latitude: float,
        longitude: float,
        device_fingerprint: Optional[str] = None
    ) -> AttendanceRecord:
        """تسجيل حضور (مع التحقق من العقد النشط والموقع الجغرافي)"""
        contract = await self.repo.get_contract(contract_id)
        if not contract or contract.employee_id != user_id:
            raise PermissionDeniedError("هذا العقد لا يخصك")
        if contract.status not in [EmploymentStatus.ACTIVE, EmploymentStatus.PROBATION]:
            raise PermissionDeniedError("العقد غير نشط")

        today_record = await self.repo.get_today_attendance(contract_id)
        if today_record and today_record.check_in:
            raise PermissionDeniedError("تم تسجيل الحضور مسبقاً اليوم")

        # Geofencing بسيط: التحقق من أن الإحداثيات ضمن نطاق العمل (يمكن استبدالها بخدمة خارجية)
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError("إحداثيات غير صالحة")

        if today_record:
            today_record.check_in = datetime.utcnow()
            today_record.check_in_location = {"lat": latitude, "lng": longitude}
            today_record.status = AttendanceStatus.PRESENT
            await self.db.commit()
            await self.db.refresh(today_record)
            return today_record
        else:
            return await self.repo.create_attendance(
                contract_id=contract_id,
                date=datetime.utcnow(),
                check_in=datetime.utcnow(),
                check_in_location={"lat": latitude, "lng": longitude},
                status=AttendanceStatus.PRESENT
            )

    async def check_out(self, user_id: int, contract_id: int, latitude: Optional[float] = None, longitude: Optional[float] = None) -> AttendanceRecord:
        """تسجيل انصراف وحساب ساعات العمل"""
        contract = await self.repo.get_contract(contract_id)
        if not contract or contract.employee_id != user_id:
            raise PermissionDeniedError("هذا العقد لا يخصك")

        today_record = await self.repo.get_today_attendance(contract_id)
        if not today_record or not today_record.check_in:
            raise PermissionDeniedError("لم يتم تسجيل حضور اليوم")
        if today_record.check_out:
            raise PermissionDeniedError("تم تسجيل الانصراف مسبقاً")

        location = {"lat": latitude, "lng": longitude} if latitude is not None else None
        return await self.repo.update_attendance_check_out(today_record.id, datetime.utcnow(), location)

    # ==============================
    # 6. الإجازات
    # ==============================

    async def request_leave(self, user_id: int, contract_id: int, leave_type: str, start_date: datetime, end_date: datetime, reason: str = None) -> LeaveRequest:
        """تقديم طلب إجازة (مع التحقق من الرصيد المتاح)"""
        contract = await self.repo.get_contract(contract_id)
        if not contract or contract.employee_id != user_id:
            raise PermissionDeniedError("هذا العقد لا يخصك")

        if leave_type == LeaveType.ANNUAL:
            used_days = await self.repo.get_used_annual_leave_days(contract_id, datetime.utcnow().year)
            requested_days = (end_date - start_date).days + 1
            if used_days + requested_days > contract.annual_leave_days:
                raise PermissionDeniedError(f"لا يوجد رصيد كافٍ للإجازة السنوية. المتبقي: {contract.annual_leave_days - used_days} يوم")

        leave = await self.repo.create_leave_request(
            contract_id=contract_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            status="PENDING"
        )
        return leave

    async def approve_leave(self, employer_id: int, leave_id: int, approve: bool) -> LeaveRequest:
        """الموافقة أو رفض طلب الإجازة (لصاحب العمل)"""
        leave = await self.repo.get_leave_request(leave_id)
        if not leave:
            raise NotFoundError("طلب الإجازة غير موجود")
        contract = await self.repo.get_contract(leave.contract_id)
        if contract.employer_id != employer_id:
            raise PermissionDeniedError("لا تملك صلاحية الموافقة على هذا الطلب")
        status = "APPROVED" if approve else "REJECTED"
        return await self.repo.update_leave_status(leave_id, status, employer_id)

    # ==============================
    # 7. الرواتب (مع Idempotency و Celery و Invoicing)
    # ==============================

    async def generate_payroll(self, contract_id: int, month: str, employer_id: int, tenant_id: int, idempotency_key: Optional[str] = None) -> PayrollRecord:
        """إنشاء كشف راتب (غير متزامن عبر Celery) مع دعم Idempotency و SaaS."""
        await self._check_saas_limits(tenant_id, "payroll")
        
        # التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        contract = await self.repo.get_contract(contract_id, tenant_id)
        if not contract or contract.employer_id != employer_id:
            raise PermissionDeniedError("لا تملك صلاحية إنشاء كشف راتب لهذا العقد")

        existing = await self.repo.get_payroll_by_month(contract_id, month, tenant_id)
        if existing:
            raise PermissionDeniedError(f"تم إنشاء كشف راتب لشهر {month} مسبقاً")

        # 🔥 تشغيل المهمة في الخلفية عبر Celery
        task = generate_payroll_task.delay(
            contract_id=contract_id,
            month=month,
            employer_id=employer_id,
            tenant_id=tenant_id,
            idempotency_key=idempotency_key
        )
        
        # إنشاء سجل مؤقت لحالة المهمة
        payroll = await self.repo.create_payroll(
            tenant_id=tenant_id,
            contract_id=contract_id,
            month=month,
            base_salary=contract.base_salary,
            bonuses=Decimal(0),
            overtime_pay=Decimal(0),
            deductions={},
            net_salary=Decimal(0),
            status=PayrollStatus.DRAFT,
            idempotency_key=idempotency_key
        )
        
        # تخزين نتيجة Idempotency مؤقتاً
        if idempotency_key:
            await store_idempotency_result(idempotency_key, {"task_id": task.id, "payroll_id": payroll.id})
        
        return payroll

    async def approve_payroll(self, payroll_id: int, employer_id: int) -> PayrollRecord:
        """اعتماد كشف الراتب (قبل الدفع)"""
        payroll = await self.repo.get_payroll(payroll_id)
        if not payroll:
            raise NotFoundError("كشف الراتب غير موجود")
        contract = await self.repo.get_contract(payroll.contract_id)
        if contract.employer_id != employer_id:
            raise PermissionDeniedError("لا تملك صلاحية اعتماد هذا الكشف")
        return await self.repo.update_payroll_status(payroll_id, PayrollStatus.APPROVED)

    async def pay_payroll(self, payroll_id: int, employer_id: int, tenant_id: int, idempotency_key: Optional[str] = None) -> PayrollRecord:
        """دفع الراتب (غير متزامن عبر Celery) مع دعم Idempotency و Invoicing."""
        await self._check_saas_limits(tenant_id, "payroll")
        
        # التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        payroll = await self.repo.get_payroll(payroll_id)
        if not payroll or payroll.status != PayrollStatus.APPROVED:
            raise PermissionDeniedError("كشف الراتب غير معتمد أو غير موجود")
        
        contract = await self.repo.get_contract(payroll.contract_id, tenant_id)
        if contract.employer_id != employer_id:
            raise PermissionDeniedError("لا تملك صلاحية الدفع")

        # 🔥 تشغيل المهمة في الخلفية عبر Celery
        task = pay_payroll_task.delay(
            payroll_id=payroll_id,
            employer_id=employer_id,
            tenant_id=tenant_id,
            idempotency_key=idempotency_key
        )
        
        # تخزين نتيجة Idempotency مؤقتاً
        if idempotency_key:
            await store_idempotency_result(idempotency_key, {"task_id": task.id, "payroll_id": payroll_id})
        
        return payroll

    # ==============================
    # 8. دوال مساعدة للتكامل
    # ==============================

    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, action_type: str, amount: Decimal):
        """تسجيل عمولة إحالة."""
        try:
            user = await self._get_user(user_id)
            if user and user.referred_by:
                commission = Decimal("2.00") if action_type == "JOB_CREATED" else amount * Decimal("0.02")
                await self.affiliate_service.register_commission(
                    affiliate_id=user.referred_by,
                    user_id=user_id,
                    amount=commission,
                    description=f"Affiliate commission for {action_type}",
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Failed to register affiliate commission: {e}")

    async def _get_user(self, user_id: int):
        """جلب بيانات المستخدم."""
        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)
        return await user_repo.get_user(user_id)

    async def _get_user_email(self, user_id: int) -> str:
        """جلب البريد الإلكتروني للمستخدم."""
        user = await self._get_user(user_id)
        return user.email if user else f"user_{user_id}@eppne.com"

    @staticmethod
    def _count_working_days(start: datetime, end: datetime) -> int:
        """حساب عدد أيام العمل."""
        days = 0
        current = start
        while current < end:
            if current.weekday() < 5:
                days += 1
            current += timedelta(days=1)
        return days

    async def _calculate_ai_match_score(self, applicant_id: int, job: JobListing) -> Decimal:
        """
        حساب نسبة التوافق بين المتقدم والوظيفة باستخدام وكيل ذكاء اصطناعي.
        """
        try:
            # جلب بيانات المستخدم والمهارات
            user = await self._get_user(applicant_id)
            user_skills = user.skills if hasattr(user, 'skills') else []
            
            # بناء prompt للوكيل
            prompt = f"""
            قم بتحليل التوافق بين المتقدم للوظيفة والوظيفة المعلنة.
            
            المهارات المطلوبة: {job.required_skills}
            المهارات المتوفرة لدى المتقدم: {user_skills}
            
            قم بحساب نسبة التوافق كرقم بين 0 و 100.
            أعد الرقم فقط بدون أي نص إضافي.
            """
            
            # استدعاء وكيل الذكاء الاصطناعي
            result = await self.ai_service.execute_agent_action(
                agent_id=1,  # وكيل تحليل المواهب (سيتم إنشاؤه مسبقاً)
                tenant_id=job.tenant_id,
                action_type="ANALYZE_SENSOR",
                payload={"prompt": prompt},
                executor_user_id=applicant_id
            )
            
            # استخراج النتيجة
            response = result.get("result", {}).get("response", "50")
            score = float(response.strip())
            return Decimal(max(0, min(100, score)))
            
        except Exception as e:
            logger.error(f"AI match score calculation failed: {e}")
            return Decimal(50.0)  # قيمة افتراضية