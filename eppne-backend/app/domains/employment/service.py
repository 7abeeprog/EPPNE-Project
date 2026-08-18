# app/domains/employment/service.py
"""
خدمات قطاع التوظيف والموارد البشرية - الإصدار الذهبي للإنتاج
يدعم: Idempotency, Audit, SaaS, Affiliate, Invoicing, AI, Celery
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, cast

import bleach
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_log
from app.core.errors import (
    InsufficientBalanceError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.core.event_bus import EventBus
from app.core.idempotency import get_idempotency_result, store_idempotency_result
from app.core.logging_conf import logger
from app.core.redis_client import redis_client
from app.domains.academy.repository import AcademyRepository
from app.domains.affiliate.service import AffiliateService
from app.domains.ai_agents.service import AIAgentsService
from app.domains.employment.models import (
    AttendanceRecord,
    AttendanceStatus,
    EmploymentContract,
    EmploymentStatus,
    JobApplication,
    JobListing,
    LeaveRequest,
    LeaveType,
    PayrollRecord,
    PayrollStatus,
)
from app.domains.employment.repository import EmploymentRepository
from app.domains.finance.service import FinanceService
from app.domains.identity.models import User
from app.domains.invoicing.service import InvoicingService
from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService


class EmploymentService:
    """
    خدمة شاملة لإدارة الموارد البشرية والتوظيف.
    تعتمد على حقن التبعية (Dependency Injection) لضمان قابلية الاختبار.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = EmploymentRepository(db)
        self.academy = AcademyRepository(db)
        self.event_bus = EventBus(redis_client)
        self.redis = redis_client

    # ============================================================
    # أدوات مساعدة داخلية (Private Helpers)
    # ============================================================

    async def _check_saas_limits(self, tenant_id: int, feature: str = "hr_management") -> dict:
        """
        التحقق من أن المستأجر لديه اشتراك فعال يتضمن الميزة المطلوبة.
        """
        saas_service = SaaSSubscriptionService(self.db, tenant_id)
        subscription = await saas_service.get_active_subscription(tenant_id)
        if not subscription:
            raise PermissionDeniedError("No active subscription found for this entity.")
        if not subscription.plan:
            raise PermissionDeniedError("No valid subscription plan found.")
        features = subscription.plan.features or []
        if feature not in features:
            raise PermissionDeniedError(
                f"Feature '{feature}' is not included in your current plan."
            )
        return subscription, features

    async def _get_user(self, user_id: int) -> Optional[User]:
        """جلب بيانات المستخدم."""
        from app.domains.identity.repository import UserRepository
        return await UserRepository(self.db).get_user(user_id)

    async def _get_user_email(self, user_id: int) -> str:
        """جلب البريد الإلكتروني للمستخدم."""
        user = await self._get_user(user_id)
        return user.email if user else f"user_{user_id}@eppne.com"

    async def _register_affiliate_commission(
        self, user_id: int, tenant_id: int, action_type: str, amount: Decimal
    ) -> None:
        """تسجيل عمولة إحالة للوكيل إن وجد."""
        affiliate_service = AffiliateService(self.db, tenant_id)
        try:
            user = await self._get_user(user_id)
            if user and user.referred_by:
                commission = (
                    Decimal("2.00")
                    if action_type == "JOB_CREATED"
                    else amount * Decimal("0.02")
                )
                await affiliate_service.register_commission(
                    affiliate_id=user.referred_by,
                    user_id=user_id,
                    amount=commission,
                    description=f"Affiliate commission for {action_type}",
                    status="PENDING",
                )
        except Exception as e:
            logger.error(f"Failed to register affiliate commission: {e}")

    @staticmethod
    def _count_working_days(start: datetime, end: datetime) -> int:
        """حساب عدد أيام العمل (من الإثنين إلى الجمعة)."""
        days = 0
        current = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = end.replace(hour=0, minute=0, second=0, microsecond=0)
        while current < end_date:
            if current.weekday() < 5:  # الإثنين=0, الجمعة=4
                days += 1
            current += timedelta(days=1)
        return days

    async def _calculate_ai_match_score(self, applicant_id: int, job: JobListing) -> Decimal:
        """حساب نسبة التوافق بين المتقدم والوظيفة باستخدام الذكاء الاصطناعي."""
        try:
            user = await self._get_user(applicant_id)
            user_skills = getattr(user, "skills", [])
            prompt = f"""
            قم بتحليل التوافق بين المتقدم للوظيفة والوظيفة المعلنة.
            المهارات المطلوبة: {job.required_skills}
            المهارات المتوفرة لدى المتقدم: {user_skills}
            قم بحساب نسبة التوافق كرقم بين 0 و 100. أعد الرقم فقط بدون أي نص إضافي.
            """
            idempotency_key = f"ai_match_{applicant_id}_{job.id}_{uuid.uuid4().hex[:8]}"
            ai_service = AIAgentsService(self.db, cast(int, job.tenant_id))
            result = await ai_service.execute_agent_action(
                agent_id=1,
                action_type="ANALYZE_SENSOR",
                payload={"prompt": prompt},
                executor_user_id=applicant_id,
                idempotency_key=idempotency_key,
            )
            response = result.get("result", {}).get("response", "50")
            score = float(response.strip())
            return Decimal(max(0, min(100, score)))
        except Exception as e:
            logger.error(f"AI match score calculation failed: {e}")
            return Decimal(50.0)

    # ============================================================
    # 1. إدارة الوظائف (Job Management)
    # ============================================================

    async def create_job(self, employer_id: int, tenant_id: int, data: Dict[str, Any]) -> JobListing:
        """إنشاء وظيفة جديدة."""
        await self._check_saas_limits(tenant_id, "hr_management")
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
            "tenant_id": tenant_id,
        }
        job = await self.repo.create_job_listing(employer_id=employer_id, **sanitized_data)
        await self._register_affiliate_commission(employer_id, tenant_id, "JOB_CREATED", Decimal(0))
        await audit_log(
            user_id=employer_id,
            tenant_id=tenant_id,
            action="JOB_CREATED",
            resource_id=job.id,
            details={"title": job.title},
        )
        return job

    async def list_open_jobs(
        self,
        tenant_id: int,
        employment_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[JobListing]:
        """عرض الوظائف النشطة المتاحة."""
        return await self.repo.list_active_jobs(tenant_id, skip, limit, employment_type)

    async def get_my_jobs(self, employer_id: int, skip: int = 0, limit: int = 50) -> List[JobListing]:
        """عرض وظائف صاحب العمل."""
        return await self.repo.list_employer_jobs(employer_id, skip, limit)

    async def update_job(self, employer_id: int, job_id: int, data: Dict[str, Any]) -> JobListing:
        """تحديث بيانات وظيفة."""
        job = await self.repo.get_job_listing_by_employer(job_id, employer_id)
        if not job:
            raise PermissionDeniedError("لا تملك صلاحية تعديل هذه الوظيفة")
        sanitized = {}
        for k, v in data.items():
            if k in ("title", "description", "location"):
                sanitized[k] = bleach.clean(v, tags=[], strip=True) if v else v
            else:
                sanitized[k] = v
        return await self.repo.update_job_listing(job_id, **sanitized)

    async def close_job(self, employer_id: int, job_id: int) -> JobListing:
        """إغلاق وظيفة (وقف التقديم عليها)."""
        job = await self.repo.get_job_listing_by_employer(job_id, employer_id)
        if not job:
            raise PermissionDeniedError("لا تملك صلاحية إغلاق هذه الوظيفة")
        return await self.repo.update_job_listing(job_id, is_active=False)

    # ============================================================
    # 2. طلبات التوظيف (Job Applications)
    # ============================================================

    async def apply_for_job(
        self,
        applicant_id: int,
        tenant_id: int,
        job_id: int,
        cover_letter: Optional[str] = None,
        resume_url: Optional[str] = None,
    ) -> JobApplication:
        """تقديم طلب لوظيفة."""
        job = await self.repo.get_job_listing(job_id, tenant_id)
        if not job or not job.is_active:
            raise NotFoundError("الوظيفة غير موجودة أو غير نشطة")
        existing = await self.repo.get_application_by_job_and_applicant(job_id, applicant_id)
        if existing:
            raise PermissionDeniedError("لقد تقدمت لهذه الوظيفة مسبقاً")
        if job.required_certificate_ids:
            certificates = await self.academy.get_user_certificates(applicant_id)
            cert_course_ids = [c.course_id for c in certificates]
            missing = set(job.required_certificate_ids) - set(cert_course_ids)
            if missing:
                raise PermissionDeniedError(f"أنت لا تمتلك الشهادات المطلوبة: {missing}")
        ai_score = await self._calculate_ai_match_score(applicant_id, job)
        application = await self.repo.create_application(
            job_id=job_id,
            applicant_id=applicant_id,
            cover_letter=bleach.clean(cover_letter, tags=[], strip=True) if cover_letter else None,
            resume_url=resume_url,
            ai_match_score=ai_score,
            status="PENDING",
        )
        return application

    async def get_my_applications(self, applicant_id: int, skip: int = 0, limit: int = 50) -> List[JobApplication]:
        """عرض طلبات التوظيف الخاصة بالمستخدم."""
        return await self.repo.list_applications_for_applicant(applicant_id, skip, limit)

    async def get_job_applications(
        self, employer_id: int, job_id: int, skip: int = 0, limit: int = 50
    ) -> List[JobApplication]:
        """عرض طلبات التوظيف لوظيفة محددة (لصاحب العمل)."""
        job = await self.repo.get_job_listing_by_employer(job_id, employer_id)
        if not job:
            raise PermissionDeniedError("ليس لديك صلاحية لعرض هذه الطلبات")
        return await self.repo.list_applications_for_job(job_id, skip, limit)

    async def review_application(self, employer_id: int, application_id: int, status: str) -> JobApplication:
        """مراجعة طلب توظيف (قبول/رفض/مراجعة)."""
        app = await self.repo.get_application(application_id)
        if not app:
            raise NotFoundError("الطلب غير موجود")
        job = await self.repo.get_job_listing(app.job_id)
        if not job or job.employer_id != employer_id:
            raise PermissionDeniedError("لا تملك صلاحية مراجعة هذا الطلب")
        if status not in ["APPROVED", "REJECTED", "REVIEWING"]:
            raise ValueError("حالة غير صالحة")
        return await self.repo.update_application_status(application_id, status, employer_id)

    # ============================================================
    # 3. عقود العمل (Contracts) مع Idempotency
    # ============================================================

    async def create_contract(
        self,
        employer_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> EmploymentContract:
        """إنشاء عقد عمل جديد مع دعم Idempotency."""
        await self._check_saas_limits(tenant_id, "hr_management")

        if idempotency_key:
            cached = await get_idempotency_result(idempotency_key)
            if cached is not None:
                contract_id = cached.get("contract_id")
                if contract_id:
                    contract = await self.repo.get_contract(contract_id, tenant_id)
                    if contract:
                        return contract
                raise ValidationError("Idempotency record exists but contract not found.")

        application = await self.repo.get_application(data["application_id"])
        if not application:
            raise NotFoundError("طلب التوظيف غير موجود")
        if application.status != "APPROVED":
            raise PermissionDeniedError("لا يمكن إنشاء عقد إلا لطلب مقبول")
        job = await self.repo.get_job_listing(application.job_id)
        if not job or job.employer_id != employer_id:
            raise PermissionDeniedError("لا تملك صلاحية إنشاء عقد لهذه الوظيفة")

        async with self.db.begin_nested():
            contract = await self.repo.create_contract(
                tenant_id=tenant_id,
                application_id=application.id,
                employee_id=application.applicant_id,
                employer_id=employer_id,
                job_title=bleach.clean(data.get("job_title", job.title), tags=[], strip=True),
                base_salary=data["base_salary"],
                allowances=data.get("allowances", {}),
                currency=data.get("currency", "MR_USDT"),
                start_date=data["start_date"],
                end_date=data.get("end_date"),
                probation_days=data.get("probation_days", 90),
                annual_leave_days=data.get("annual_leave_days", 21),
                status=EmploymentStatus.WAITING_SIGNATURE,
                idempotency_key=idempotency_key,
            )

        await self.db.commit()

        await self._register_affiliate_commission(employer_id, tenant_id, "CONTRACT_CREATED", data["base_salary"])
        await audit_log(
            user_id=employer_id,
            tenant_id=tenant_id,
            action="CONTRACT_CREATED",
            resource_id=contract.id,
            details={"employee_id": application.applicant_id, "salary": float(data["base_salary"])},
        )
        await self.event_bus.publish(
            "contract.created",
            {
                "contract_id": contract.id,
                "tenant_id": tenant_id,
                "employee_id": application.applicant_id,
                "employer_id": employer_id,
            },
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, {"contract_id": contract.id})

        return contract

    async def get_my_active_contract(self, user_id: int) -> Optional[EmploymentContract]:
        """الحصول على العقد النشط للمستخدم."""
        return await self.repo.get_contract_by_employee(user_id, active_only=True)

    async def sign_contract(
        self,
        user_id: int,
        contract_id: int,
        signature_tx_hash: str,
        is_employee: bool = True,
    ) -> EmploymentContract:
        """توقيع العقد (من قبل الموظف أو صاحب العمل)."""
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

        if contract.signature_tx_hash and contract.employer_signature_tx:
            contract = await self.repo.update_contract(contract_id, status=EmploymentStatus.PROBATION)

        return contract

    # ============================================================
    # 4. الحضور والانصراف (Attendance)
    # ============================================================

    async def check_in(
        self,
        user_id: int,
        contract_id: int,
        latitude: float,
        longitude: float,
        device_fingerprint: Optional[str] = None,
    ) -> AttendanceRecord:
        """تسجيل حضور الموظف."""
        contract = await self.repo.get_contract(contract_id)
        if not contract or contract.employee_id != user_id:
            raise PermissionDeniedError("هذا العقد لا يخصك")
        if contract.status not in [EmploymentStatus.ACTIVE, EmploymentStatus.PROBATION]:
            raise PermissionDeniedError("العقد غير نشط")

        today_record = await self.repo.get_today_attendance(contract_id)
        if today_record and today_record.check_in:
            raise PermissionDeniedError("تم تسجيل الحضور مسبقاً اليوم")

        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValidationError("إحداثيات غير صالحة")

        now = datetime.now(timezone.utc)
        if today_record:
            today_record.check_in = now
            today_record.check_in_location = {"lat": latitude, "lng": longitude}
            today_record.status = AttendanceStatus.PRESENT
            await self.db.commit()
            await self.db.refresh(today_record)
            return today_record

        return await self.repo.create_attendance(
            contract_id=contract_id,
            date=now.date(),
            check_in=now,
            check_in_location={"lat": latitude, "lng": longitude},
            status=AttendanceStatus.PRESENT,
        )

    async def check_out(
        self,
        user_id: int,
        contract_id: int,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> AttendanceRecord:
        """تسجيل انصراف الموظف."""
        contract = await self.repo.get_contract(contract_id)
        if not contract or contract.employee_id != user_id:
            raise PermissionDeniedError("هذا العقد لا يخصك")

        today_record = await self.repo.get_today_attendance(contract_id)
        if not today_record or not today_record.check_in:
            raise PermissionDeniedError("لم يتم تسجيل حضور اليوم")
        if today_record.check_out:
            raise PermissionDeniedError("تم تسجيل الانصراف مسبقاً")

        location = {"lat": latitude, "lng": longitude} if latitude is not None else None
        return await self.repo.update_attendance_check_out(
            record_id=cast(int, today_record.id),
            check_out=datetime.now(timezone.utc),
            check_out_location=location,
        )

    async def get_my_attendance(
        self, user_id: int, contract_id: int, skip: int = 0, limit: int = 30
    ) -> List[AttendanceRecord]:
        """عرض سجل الحضور الخاص بالموظف."""
        contract = await self.repo.get_contract(contract_id)
        if not contract or contract.employee_id != user_id:
            raise PermissionDeniedError("لا تملك صلاحية الاطلاع على هذا السجل")
        now = datetime.now(timezone.utc)
        records = await self.repo.get_attendance_for_month(contract_id, now.year, now.month)
        return records[-limit:]

    # ============================================================
    # 5. الإجازات (Leave Requests)
    # ============================================================

    async def request_leave(
        self,
        user_id: int,
        contract_id: int,
        leave_type: str,
        start_date: datetime,
        end_date: datetime,
        reason: Optional[str] = None,
    ) -> LeaveRequest:
        """تقديم طلب إجازة."""
        contract = await self.repo.get_contract(contract_id)
        if not contract or contract.employee_id != user_id:
            raise PermissionDeniedError("هذا العقد لا يخصك")

        if leave_type == LeaveType.ANNUAL:
            used_days = await self.repo.get_used_annual_leave_days(contract_id, datetime.now(timezone.utc).year)
            requested_days = (end_date - start_date).days + 1
            if used_days + requested_days > contract.annual_leave_days:
                raise PermissionDeniedError(
                    f"لا يوجد رصيد كافٍ للإجازة السنوية. المتبقي: {contract.annual_leave_days - used_days} يوم"
                )

        return await self.repo.create_leave_request(
            contract_id=contract_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            status="PENDING",
        )

    async def get_pending_leaves_for_employer(self, employer_id: int) -> List[LeaveRequest]:
        """عرض طلبات الإجازات المعلقة لصاحب العمل."""
        return await self.repo.list_pending_leave_requests_for_employer(employer_id)

    async def approve_leave(self, employer_id: int, leave_id: int, approve: bool) -> LeaveRequest:
        """الموافقة على طلب إجازة أو رفضه."""
        leave = await self.repo.get_leave_request(leave_id)
        if not leave:
            raise NotFoundError("طلب الإجازة غير موجود")
        contract = await self.repo.get_contract(leave.contract_id)
        if not contract or contract.employer_id != employer_id:
            raise PermissionDeniedError("لا تملك صلاحية الموافقة على هذا الطلب")
        status = "APPROVED" if approve else "REJECTED"
        return await self.repo.update_leave_status(leave_id, status, employer_id)

    # ============================================================
    # 6. الرواتب (Payroll) - مع Idempotency و Celery
    # ============================================================

    async def generate_payroll(
        self,
        contract_id: int,
        month: str,
        employer_id: int,
        tenant_id: int,
        idempotency_key: Optional[str] = None,
    ) -> PayrollRecord:
        """
        إنشاء كشف راتب لشهر محدد.
        يتم تفويض الحساب الفعلي إلى مهمة Celery غير المتزامنة.
        """
        await self._check_saas_limits(tenant_id, "payroll")

        # التحقق من Idempotency
        if idempotency_key:
            cached = await get_idempotency_result(idempotency_key)
            if cached is not None:
                payroll_id = cached.get("payroll_id")
                if payroll_id:
                    payroll = await self.repo.get_payroll(payroll_id)
                    if payroll:
                        return payroll
                raise ValidationError("Idempotency record exists but payroll not found.")

        # التحقق من الصلاحية والعقد
        contract = await self.repo.get_contract_with_tenant(contract_id, tenant_id)
        if not contract or contract.employer_id != employer_id:
            raise PermissionDeniedError("لا تملك صلاحية إنشاء كشف راتب لهذا العقد")

        existing = await self.repo.get_payroll_by_month(contract_id, month, tenant_id)
        if existing:
            raise PermissionDeniedError(f"تم إنشاء كشف راتب لشهر {month} مسبقاً")

        # 🔥 الاستيراد المحلي لكسر الدائرة (Circular Import)
        from app.tasks.employment import generate_payroll_task

        # تشغيل المهمة في الخلفية
        task = generate_payroll_task.delay(
            contract_id=contract_id,
            month=month,
            employer_id=employer_id,
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
        )

        # إنشاء سجل أولي في قاعدة البيانات
        payroll = await self.repo.create_payroll(
            tenant_id=tenant_id,
            contract_id=contract_id,
            month=month,
            base_salary=cast(Decimal, contract.base_salary),
            bonuses=Decimal(0),
            overtime_pay=Decimal(0),
            deductions={},
            net_salary=Decimal(0),
            status=PayrollStatus.DRAFT,
            idempotency_key=idempotency_key,
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, {"task_id": task.id, "payroll_id": payroll.id})

        return payroll

    async def approve_payroll(self, payroll_id: int, employer_id: int) -> PayrollRecord:
        """اعتماد كشف الراتب من قبل صاحب العمل."""
        payroll = await self.repo.get_payroll(payroll_id)
        if not payroll:
            raise NotFoundError("كشف الراتب غير موجود")
        contract = await self.repo.get_contract(payroll.contract_id)
        if not contract or contract.employer_id != employer_id:
            raise PermissionDeniedError("لا تملك صلاحية اعتماد هذا الكشف")
        return await self.repo.update_payroll_status(payroll_id, PayrollStatus.APPROVED)

    async def pay_payroll(
        self,
        payroll_id: int,
        employer_id: int,
        tenant_id: int,
        idempotency_key: Optional[str] = None,
    ) -> PayrollRecord:
        """
        تنفيذ عملية صرف الراتب.
        يتم تفويض عملية الصرف الفعلية إلى مهمة Celery غير المتزامنة.
        """
        await self._check_saas_limits(tenant_id, "payroll")

        if idempotency_key:
            cached = await get_idempotency_result(idempotency_key)
            if cached is not None:
                payroll_id_cached = cached.get("payroll_id")
                if payroll_id_cached:
                    payroll = await self.repo.get_payroll(payroll_id_cached)
                    if payroll:
                        return payroll
                raise ValidationError("Idempotency record exists but payroll not found.")

        payroll = await self.repo.get_payroll(payroll_id)
        if not payroll or payroll.status != PayrollStatus.APPROVED:
            raise PermissionDeniedError("كشف الراتب غير معتمد أو غير موجود")

        contract = await self.repo.get_contract_with_tenant(payroll.contract_id, tenant_id)
        if not contract or contract.employer_id != employer_id:
            raise PermissionDeniedError("لا تملك صلاحية الدفع")

        # 🔥 الاستيراد المحلي لكسر الدائرة (Circular Import)
        from app.tasks.employment import pay_payroll_task

        # تشغيل مهمة الصرف
        task = pay_payroll_task.delay(
            payroll_id=payroll_id,
            employer_id=employer_id,
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, {"task_id": task.id, "payroll_id": payroll_id})

        return payroll

    async def get_my_payrolls(self, user_id: int, skip: int = 0, limit: int = 12) -> List[PayrollRecord]:
        """عرض سجل الرواتب للموظف."""
        contract = await self.repo.get_contract_by_employee(user_id, active_only=False)
        if not contract:
            raise NotFoundError("لا يوجد عقد عمل مسجل")
        return await self.repo.list_payrolls_for_contract(
            contract_id=cast(int, contract.id),
            tenant_id=cast(int, contract.tenant_id),
            skip=skip,
            limit=limit,
        )