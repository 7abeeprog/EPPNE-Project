# app/tasks/employment.py
"""
مهام Celery لقطاع التوظيف – معالجة الرواتب غير المتزامنة
"""
from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session
from app.domains.employment.service import EmploymentService
from app.domains.finance.service import FinanceService
from app.core.logging import logger
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from app.domains.employment.models import AttendanceStatus, PayrollStatus

celery_app = Celery("employment", broker="redis://localhost:6379/0")

@celery_app.task(bind=True, max_retries=3)
def generate_payroll_task(self, contract_id: int, month: str, employer_id: int, tenant_id: int, idempotency_key: str = None):
    """مهمة حساب كشف الراتب (غير متزامن)"""
    try:
        asyncio.run(_generate_payroll_internal(contract_id, month, employer_id, tenant_id, idempotency_key))
    except Exception as e:
        logger.error(f"Payroll generation failed for contract {contract_id}: {e}")
        self.retry(countdown=60, exc=e)

async def _generate_payroll_internal(contract_id: int, month: str, employer_id: int, tenant_id: int, idempotency_key: str = None):
    """المنطق الفعلي لحساب كشف الراتب."""
    async with async_session() as db:
        service = EmploymentService(db)
        repo = service.repo
        finance = FinanceService(db)
        
        # التحقق من Idempotency
        if idempotency_key:
            existing = await repo.get_payroll_by_idempotency(idempotency_key)
            if existing:
                return

        contract = await repo.get_contract(contract_id, tenant_id)
        if not contract or contract.employer_id != employer_id:
            return

        # حساب عدد أيام العمل في الشهر
        year, month_num = map(int, month.split('-'))
        start_date = datetime(year, month_num, 1)
        if month_num == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month_num + 1, 1)
        working_days = service._count_working_days(start_date, end_date)

        # جلب سجلات الحضور للشهر
        attendance_records = await repo.get_attendance_for_month(contract_id, year, month_num)

        # حساب ساعات العمل الفعلية والعمل الإضافي
        total_hours = sum(r.hours_worked or 0 for r in attendance_records)
        overtime_hours = sum(r.overtime_hours or 0 for r in attendance_records)

        # حساب عدد أيام الغياب غير المدفوع
        absent_days = working_days - len([r for r in attendance_records if r.status == AttendanceStatus.PRESENT])

        # الراتب الأساسي والبدلات
        base_salary = contract.base_salary
        allowances_sum = sum(Decimal(v) for v in contract.allowances.values()) if contract.allowances else Decimal(0)

        # العمل الإضافي (1.5 × الأجر اليومي / 8 ساعات)
        daily_rate = base_salary / Decimal(working_days) if working_days > 0 else Decimal(0)
        hourly_rate = daily_rate / Decimal(8)
        overtime_pay = hourly_rate * Decimal(overtime_hours) * Decimal(1.5)

        # خصم أيام الغياب
        absence_deduction = daily_rate * Decimal(absent_days)

        # الخصومات القانونية
        social_insurance = base_salary * Decimal(0.11)
        taxable_income = base_salary - social_insurance
        tax = Decimal(0)
        if taxable_income > Decimal(20000):
            tax = (taxable_income - Decimal(20000)) * Decimal(0.1)

        deductions = {
            "social_insurance": social_insurance,
            "income_tax": tax,
            "absence_deduction": absence_deduction
        }

        net_salary = base_salary + allowances_sum + overtime_pay - sum(deductions.values())

        # تحديث كشف الراتب بالنتائج
        payroll = await repo.get_payroll_by_month(contract_id, month, tenant_id)
        if payroll:
            await repo.update_payroll(
                payroll.id,
                base_salary=base_salary,
                bonuses=Decimal(0),
                overtime_pay=overtime_pay,
                deductions=deductions,
                net_salary=net_salary,
                status=PayrollStatus.APPROVED  # معتمد تلقائياً
            )
        
        logger.info(f"Payroll generated for contract {contract_id}, month {month}: net_salary={net_salary}")

@celery_app.task(bind=True, max_retries=3)
def pay_payroll_task(self, payroll_id: int, employer_id: int, tenant_id: int, idempotency_key: str = None):
    """مهمة دفع الراتب (غير متزامن)"""
    try:
        asyncio.run(_pay_payroll_internal(payroll_id, employer_id, tenant_id, idempotency_key))
    except Exception as e:
        logger.error(f"Payroll payment failed for payroll {payroll_id}: {e}")
        self.retry(countdown=60, exc=e)

async def _pay_payroll_internal(payroll_id: int, employer_id: int, tenant_id: int, idempotency_key: str = None):
    """المنطق الفعلي لدفع الراتب."""
    async with async_session() as db:
        service = EmploymentService(db)
        repo = service.repo
        finance = FinanceService(db)
        
        # التحقق من Idempotency
        if idempotency_key:
            existing = await repo.get_payroll_by_idempotency(idempotency_key)
            if existing:
                return

        payroll = await repo.get_payroll(payroll_id)
        if not payroll or payroll.status != PayrollStatus.APPROVED:
            return

        contract = await repo.get_contract(payroll.contract_id, tenant_id)
        if contract.employer_id != employer_id:
            return

        # تحويل المبلغ
        try:
            tx_hash = await finance.transfer(
                sender_id=employer_id,
                receiver_email=await service._get_user_email(contract.employee_id),
                currency=payroll.currency if hasattr(payroll, 'currency') else "MR_USDT",
                amount=payroll.net_salary,
                notes=f"Salary payment for {payroll.month}",
                idempotency_key=idempotency_key
            )
        except InsufficientBalanceError as e:
            raise PermissionDeniedError(f"Insufficient balance: {e}")

        # تحديث حالة كشف الراتب
        await repo.update_payroll_status(payroll_id, PayrollStatus.PAID, payment_tx_hash=tx_hash)
        
        # 🔥 إنشاء فاتورة (Invoicing)
        await service.invoicing_service.create_invoice(
            entity_id=tenant_id,
            amount=payroll.net_salary,
            description=f"Salary payment for contract {contract.id} - {payroll.month}",
            due_date=datetime.utcnow() + timedelta(days=30)
        )
        
        logger.info(f"Payroll {payroll_id} paid: tx_hash={tx_hash}")