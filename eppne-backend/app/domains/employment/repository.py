"""
مستودع قطاع التوظيف والموارد البشرية
يدير: الوظائف، طلبات التوظيف، العقود، الحضور، الإجازات، الرواتب
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta

from app.domains.employment.models import (
    JobListing, JobApplication, EmploymentContract, AttendanceRecord,
    LeaveRequest, PayrollRecord, PayrollAdjustment,
    EmploymentStatus, LeaveType, PayrollStatus, AttendanceStatus
)
from app.core.errors import NotFoundError


class EmploymentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # 1. الوظائف (Job Listings)
    # ============================================================

    async def create_job_listing(self, **kwargs) -> JobListing:
        """إنشاء وظيفة جديدة"""
        job = JobListing(**kwargs)
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get_job_listing(self, job_id: int) -> Optional[JobListing]:
        """جلب وظيفة بواسطة ID"""
        result = await self.db.execute(select(JobListing).where(JobListing.id == job_id))
        return result.scalar_one_or_none()

    async def get_job_listing_by_employer(self, job_id: int, employer_id: int) -> Optional[JobListing]:
        """جلب وظيفة مع التأكد من أن صاحب العمل هو المالك"""
        result = await self.db.execute(
            select(JobListing).where(JobListing.id == job_id, JobListing.employer_id == employer_id)
        )
        return result.scalar_one_or_none()

    async def list_active_jobs(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 50,
        employment_type: Optional[str] = None
    ) -> List[JobListing]:
        """قائمة الوظائف النشطة مع فلترة حسب النوع"""
        query = select(JobListing).where(
            JobListing.tenant_id == tenant_id,
            JobListing.is_active == True,
            JobListing.is_deleted == False
        )
        if employment_type:
            query = query.where(JobListing.employment_type == employment_type)
        query = query.order_by(JobListing.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def list_employer_jobs(self, employer_id: int, skip: int = 0, limit: int = 50) -> List[JobListing]:
        """قائمة الوظائف الخاصة بصاحب عمل معين"""
        result = await self.db.execute(
            select(JobListing).where(JobListing.employer_id == employer_id, JobListing.is_deleted == False)
            .order_by(JobListing.created_at.desc()).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def update_job_listing(self, job_id: int, **kwargs) -> JobListing:
        """تحديث بيانات الوظيفة"""
        await self.db.execute(update(JobListing).where(JobListing.id == job_id).values(**kwargs))
        await self.db.commit()
        job = await self.get_job_listing(job_id)
        if not job:
            raise NotFoundError("الوظيفة غير موجودة")
        return job

    async def delete_job_listing(self, job_id: int, soft: bool = True) -> None:
        """حذف وظيفة (منطقي أو دائم)"""
        if soft:
            await self.db.execute(update(JobListing).where(JobListing.id == job_id).values(is_deleted=True, deleted_at=func.now()))
        else:
            await self.db.execute(delete(JobListing).where(JobListing.id == job_id))
        await self.db.commit()

    # ============================================================
    # 2. طلبات التوظيف (Applications)
    # ============================================================

    async def create_application(self, **kwargs) -> JobApplication:
        """تقديم طلب وظيفة جديد"""
        app = JobApplication(**kwargs)
        self.db.add(app)
        await self.db.commit()
        await self.db.refresh(app)
        return app

    async def get_application(self, app_id: int) -> Optional[JobApplication]:
        """جلب طلب بواسطة ID"""
        result = await self.db.execute(select(JobApplication).where(JobApplication.id == app_id))
        return result.scalar_one_or_none()

    async def get_application_by_job_and_applicant(self, job_id: int, applicant_id: int) -> Optional[JobApplication]:
        """التحقق من تقدم مسبق لنفس المستخدم لنفس الوظيفة"""
        result = await self.db.execute(
            select(JobApplication).where(
                JobApplication.job_id == job_id,
                JobApplication.applicant_id == applicant_id
            )
        )
        return result.scalar_one_or_none()

    async def list_applications_for_job(self, job_id: int, skip: int = 0, limit: int = 50) -> List[JobApplication]:
        """قائمة طلبات التوظيف لوظيفة معينة (لصاحب العمل)"""
        result = await self.db.execute(
            select(JobApplication).where(JobApplication.job_id == job_id)
            .order_by(JobApplication.created_at.desc()).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def list_applications_for_applicant(self, applicant_id: int, skip: int = 0, limit: int = 50) -> List[JobApplication]:
        """قائمة طلبات التوظيف الخاصة بمستخدم معين"""
        result = await self.db.execute(
            select(JobApplication).where(JobApplication.applicant_id == applicant_id)
            .order_by(JobApplication.created_at.desc()).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def update_application_status(
        self,
        app_id: int,
        status: str,
        reviewer_id: int,
        ai_match_score: Optional[float] = None
    ) -> JobApplication:
        """تحديث حالة الطلب (قبول/رفض/مراجعة)"""
        values = {"status": status, "reviewed_by_id": reviewer_id, "reviewed_at": func.now()}
        if ai_match_score is not None:
            values["ai_match_score"] = ai_match_score
        await self.db.execute(update(JobApplication).where(JobApplication.id == app_id).values(**values))
        await self.db.commit()
        app = await self.get_application(app_id)
        if not app:
            raise NotFoundError("الطلب غير موجود")
        return app

    # ============================================================
    # 3. عقود العمل (Contracts) – مع دعم Multi-Tenancy
    # ============================================================

    async def create_contract(self, **kwargs) -> EmploymentContract:
        """إنشاء عقد عمل جديد"""
        contract = EmploymentContract(**kwargs)
        self.db.add(contract)
        await self.db.commit()
        await self.db.refresh(contract)
        return contract

    async def get_contract(self, contract_id: int) -> Optional[EmploymentContract]:
        """جلب عقد بواسطة ID (بدون tenant_id – للإصدارات السابقة)"""
        result = await self.db.execute(select(EmploymentContract).where(EmploymentContract.id == contract_id))
        return result.scalar_one_or_none()

    async def get_contract(self, contract_id: int, tenant_id: int) -> Optional[EmploymentContract]:
        """جلب عقد مع التأكد من tenant_id"""
        result = await self.db.execute(
            select(EmploymentContract).where(
                EmploymentContract.id == contract_id,
                EmploymentContract.tenant_id == tenant_id,
                EmploymentContract.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def get_contract_by_employee(self, employee_id: int, active_only: bool = True) -> Optional[EmploymentContract]:
        """جلب عقد الموظف الحالي (بدون tenant_id – للإصدارات السابقة)"""
        query = select(EmploymentContract).where(EmploymentContract.employee_id == employee_id)
        if active_only:
            query = query.where(EmploymentContract.status == EmploymentStatus.ACTIVE)
        query = query.order_by(EmploymentContract.created_at.desc())
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_contract_by_employee(self, employee_id: int, tenant_id: int, active_only: bool = True) -> Optional[EmploymentContract]:
        """جلب عقد الموظف الحالي مع التأكد من tenant_id"""
        query = select(EmploymentContract).where(
            EmploymentContract.employee_id == employee_id,
            EmploymentContract.tenant_id == tenant_id
        )
        if active_only:
            query = query.where(EmploymentContract.status == EmploymentStatus.ACTIVE)
        query = query.order_by(EmploymentContract.created_at.desc())
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_contracts_for_employer(self, employer_id: int, skip: int = 0, limit: int = 50) -> List[EmploymentContract]:
        """قائمة عقود صاحب العمل (بدون tenant_id – للإصدارات السابقة)"""
        result = await self.db.execute(
            select(EmploymentContract).where(EmploymentContract.employer_id == employer_id)
            .order_by(EmploymentContract.created_at.desc()).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def list_contracts_for_employer(
        self,
        employer_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[EmploymentContract]:
        """قائمة عقود صاحب العمل مع التأكد من tenant_id وتحسين الأداء (selectinload)"""
        result = await self.db.execute(
            select(EmploymentContract)
            .options(selectinload(EmploymentContract.employee))
            .where(
                EmploymentContract.employer_id == employer_id,
                EmploymentContract.tenant_id == tenant_id
            )
            .order_by(EmploymentContract.created_at.desc())
            .offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def update_contract(
        self,
        contract_id: int,
        status: Optional[str] = None,
        signature_tx_hash: Optional[str] = None,
        employer_signature_tx: Optional[str] = None
    ) -> EmploymentContract:
        """تحديث حالة العقد أو التوقيعات"""
        values = {}
        if status is not None:
            values["status"] = status
        if signature_tx_hash is not None:
            values["signature_tx_hash"] = signature_tx_hash
        if employer_signature_tx is not None:
            values["employer_signature_tx"] = employer_signature_tx
        if values:
            await self.db.execute(update(EmploymentContract).where(EmploymentContract.id == contract_id).values(**values))
            await self.db.commit()
        return await self.get_contract(contract_id)

    async def terminate_contract(self, contract_id: int, end_date: datetime) -> EmploymentContract:
        """إنهاء العقد (تحديد تاريخ النهاية والحالة)"""
        await self.db.execute(
            update(EmploymentContract).where(EmploymentContract.id == contract_id).values(
                end_date=end_date, status=EmploymentStatus.TERMINATED
            )
        )
        await self.db.commit()
        return await self.get_contract(contract_id)

    # ============================================================
    # 4. الحضور (Attendance) – مع Idempotency
    # ============================================================

    async def create_attendance(self, **kwargs) -> AttendanceRecord:
        """تسجيل حضور جديد"""
        record = AttendanceRecord(**kwargs)
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def get_attendance(self, attendance_id: int) -> Optional[AttendanceRecord]:
        result = await self.db.execute(select(AttendanceRecord).where(AttendanceRecord.id == attendance_id))
        return result.scalar_one_or_none()

    async def get_today_attendance(self, contract_id: int) -> Optional[AttendanceRecord]:
        """جلب سجل حضور اليوم لعقد معين"""
        today = date.today()
        result = await self.db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.contract_id == contract_id,
                func.date(AttendanceRecord.date) == today
            )
        )
        return result.scalar_one_or_none()

    async def get_attendance_for_month(self, contract_id: int, year: int, month: int) -> List[AttendanceRecord]:
        """جلب سجلات الحضور لشهر محدد"""
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        result = await self.db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.contract_id == contract_id,
                AttendanceRecord.date >= start_date,
                AttendanceRecord.date < end_date
            ).order_by(AttendanceRecord.date)
        )
        return result.scalars().all()

    async def update_attendance_check_out(self, attendance_id: int, check_out: datetime, location: dict = None) -> AttendanceRecord:
        """تحديث وقت الخروج وحساب ساعات العمل"""
        record = await self.get_attendance(attendance_id)
        if not record:
            raise NotFoundError("سجل الحضور غير موجود")
        record.check_out = check_out
        if location:
            record.check_out_location = location
        # حساب ساعات العمل
        if record.check_in:
            delta = check_out - record.check_in
            record.hours_worked = round(delta.total_seconds() / 3600, 2)
            # حساب العمل الإضافي (إذا تجاوز 8 ساعات)
            if record.hours_worked > 8:
                record.overtime_hours = record.hours_worked - 8
            record.status = AttendanceStatus.PRESENT
        await self.db.commit()
        await self.db.refresh(record)
        return record

    # ============================================================
    # 5. الإجازات (Leave Requests)
    # ============================================================

    async def create_leave_request(self, **kwargs) -> LeaveRequest:
        leave = LeaveRequest(**kwargs)
        self.db.add(leave)
        await self.db.commit()
        await self.db.refresh(leave)
        return leave

    async def get_leave_request(self, leave_id: int) -> Optional[LeaveRequest]:
        result = await self.db.execute(select(LeaveRequest).where(LeaveRequest.id == leave_id))
        return result.scalar_one_or_none()

    async def list_leave_requests_for_contract(self, contract_id: int, status: Optional[str] = None) -> List[LeaveRequest]:
        query = select(LeaveRequest).where(LeaveRequest.contract_id == contract_id)
        if status:
            query = query.where(LeaveRequest.status == status)
        query = query.order_by(LeaveRequest.start_date.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def list_pending_leave_requests_for_employer(self, employer_id: int) -> List[LeaveRequest]:
        """جلب طلبات الإجازات المعلقة لجميع عقود صاحب العمل"""
        subquery = select(EmploymentContract.id).where(EmploymentContract.employer_id == employer_id)
        result = await self.db.execute(
            select(LeaveRequest).where(
                LeaveRequest.contract_id.in_(subquery),
                LeaveRequest.status == "PENDING"
            ).order_by(LeaveRequest.created_at)
        )
        return result.scalars().all()

    async def update_leave_status(self, leave_id: int, status: str, approver_id: int) -> LeaveRequest:
        await self.db.execute(
            update(LeaveRequest).where(LeaveRequest.id == leave_id).values(
                status=status, approved_by_id=approver_id, approved_at=func.now()
            )
        )
        await self.db.commit()
        return await self.get_leave_request(leave_id)

    async def get_used_annual_leave_days(self, contract_id: int, year: int) -> float:
        """حساب عدد أيام الإجازة السنوية المستخدمة في سنة معينة"""
        start_date = datetime(year, 1, 1)
        end_date = datetime(year + 1, 1, 1)
        result = await self.db.execute(
            select(func.sum(func.extract('epoch', LeaveRequest.end_date - LeaveRequest.start_date) / 86400))
            .where(
                LeaveRequest.contract_id == contract_id,
                LeaveRequest.leave_type == LeaveType.ANNUAL,
                LeaveRequest.status == "APPROVED",
                LeaveRequest.start_date >= start_date,
                LeaveRequest.start_date < end_date
            )
        )
        return result.scalar() or 0.0

    # ============================================================
    # 6. الرواتب (Payroll) – مع Idempotency و Multi-Tenancy
    # ============================================================

    async def create_payroll(self, **kwargs) -> PayrollRecord:
        payroll = PayrollRecord(**kwargs)
        self.db.add(payroll)
        await self.db.commit()
        await self.db.refresh(payroll)
        return payroll

    async def get_payroll(self, payroll_id: int) -> Optional[PayrollRecord]:
        result = await self.db.execute(select(PayrollRecord).where(PayrollRecord.id == payroll_id))
        return result.scalar_one_or_none()

    async def get_payroll_by_month(self, contract_id: int, month: str) -> Optional[PayrollRecord]:
        """جلب كشف راتب لشهر محدد (بدون tenant_id – للإصدارات السابقة)"""
        result = await self.db.execute(
            select(PayrollRecord).where(
                PayrollRecord.contract_id == contract_id,
                PayrollRecord.month == month
            )
        )
        return result.scalar_one_or_none()

    async def get_payroll_by_month(self, contract_id: int, month: str, tenant_id: int) -> Optional[PayrollRecord]:
        """جلب كشف راتب لشهر محدد مع التأكد من tenant_id"""
        result = await self.db.execute(
            select(PayrollRecord).where(
                PayrollRecord.contract_id == contract_id,
                PayrollRecord.month == month,
                PayrollRecord.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def list_payrolls_for_contract(self, contract_id: int, skip: int = 0, limit: int = 12) -> List[PayrollRecord]:
        """قائمة كشوف الرواتب لعقد (بدون tenant_id – للإصدارات السابقة)"""
        result = await self.db.execute(
            select(PayrollRecord).where(PayrollRecord.contract_id == contract_id)
            .order_by(PayrollRecord.month.desc()).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def list_payrolls_for_contract(
        self,
        contract_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 12
    ) -> List[PayrollRecord]:
        """قائمة كشوف الرواتب مع التأكد من tenant_id وتحسين الأداء (selectinload)"""
        result = await self.db.execute(
            select(PayrollRecord)
            .options(selectinload(PayrollRecord.contract))
            .where(
                PayrollRecord.contract_id == contract_id,
                PayrollRecord.tenant_id == tenant_id
            )
            .order_by(PayrollRecord.month.desc())
            .offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def update_payroll_status(self, payroll_id: int, status: str, payment_tx_hash: Optional[str] = None) -> PayrollRecord:
        values = {"status": status}
        if payment_tx_hash:
            values["payment_tx_hash"] = payment_tx_hash
        await self.db.execute(update(PayrollRecord).where(PayrollRecord.id == payroll_id).values(**values))
        await self.db.commit()
        return await self.get_payroll(payroll_id)

    async def create_payroll_adjustment(self, **kwargs) -> PayrollAdjustment:
        adjustment = PayrollAdjustment(**kwargs)
        self.db.add(adjustment)
        await self.db.commit()
        await self.db.refresh(adjustment)
        return adjustment

    async def get_payroll_adjustments_for_contract(self, contract_id: int) -> List[PayrollAdjustment]:
        result = await self.db.execute(
            select(PayrollAdjustment).where(PayrollAdjustment.contract_id == contract_id)
            .order_by(PayrollAdjustment.created_at.desc())
        )
        return result.scalars().all()

    # ============================================================
    # 🆕 7. دوال Idempotency
    # ============================================================

    async def get_payroll_by_idempotency(self, idempotency_key: str) -> Optional[PayrollRecord]:
        """جلب كشف راتب باستخدام idempotency_key"""
        result = await self.db.execute(
            select(PayrollRecord).where(PayrollRecord.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def get_attendance_by_idempotency(self, idempotency_key: str) -> Optional[AttendanceRecord]:
        """جلب سجل حضور باستخدام idempotency_key"""
        result = await self.db.execute(
            select(AttendanceRecord).where(AttendanceRecord.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    # ============================================================
    # 🆕 8. دوال Multi-Tenancy الإضافية
    # ============================================================

    async def list_active_jobs_for_tenant(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 50,
        employment_type: Optional[str] = None,
        min_salary: Optional[float] = None,
        max_salary: Optional[float] = None
    ) -> List[JobListing]:
        """قائمة الوظائف النشطة مع فلترة متقدمة حسب المستأجر"""
        query = select(JobListing).where(
            JobListing.tenant_id == tenant_id,
            JobListing.is_active == True,
            JobListing.is_deleted == False
        )
        if employment_type:
            query = query.where(JobListing.employment_type == employment_type)
        if min_salary is not None:
            query = query.where(JobListing.salary_min >= min_salary)
        if max_salary is not None:
            query = query.where(JobListing.salary_max <= max_salary)
        query = query.order_by(JobListing.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def list_applications_for_job_with_tenant(
        self,
        job_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[JobApplication]:
        """قائمة طلبات التوظيف لوظيفة مع التأكد من tenant_id"""
        result = await self.db.execute(
            select(JobApplication)
            .join(JobListing, JobApplication.job_id == JobListing.id)
            .where(
                JobApplication.job_id == job_id,
                JobListing.tenant_id == tenant_id
            )
            .order_by(JobApplication.created_at.desc())
            .offset(skip).limit(limit)
        )
        return result.scalars().all()