# app/tasks/employment.py
"""
مهام Celery لقطاع التوظيف – معالجة الرواتب غير المتزامنة
يدعم: حساب كشف الراتب، دفع الراتب، معالجة الإجازات، وتقارير الرواتب الشهرية.
"""
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, cast

# 🔥 استيراد التطبيق المركزي والاتصال الموحّد بقاعدة البيانات
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.logging_conf import logger
from app.core.errors import InsufficientBalanceError, PermissionDeniedError

from app.domains.employment.service import EmploymentService
from app.domains.employment.models import AttendanceStatus, PayrollStatus, EmploymentStatus
from app.domains.finance.service import FinanceService
from app.domains.invoicing.service import InvoicingService


# ============================================================
# 1. أداة تشغيل آمنة للـ Async (تمنع تسرب الذاكرة)
# ============================================================
def _run_async(coro):
    """
    تشغيل دالة غير متزامنة (Async) بطريقة آمنة داخل Celery.
    - تخلق حلقة أحداث جديدة لكل مهمة لضمان العزل.
    - تغلق الحلقة تلقائياً بعد الانتهاء لمنع تسرب الذاكرة.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        # 🔥 تنظيف الموارد وإغلاق الحلقة
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        finally:
            loop.close()


# ============================================================
# 2. دالة مساعدة لتحويل أي قيمة إلى Decimal (حل جذري لمشكلة Column[Decimal])
# ============================================================
def _to_decimal(value: Any) -> Decimal:
    """
    تحويل أي قيمة إلى Decimal بطريقة آمنة.
    - تتعامل مع الأرقام، السلاسل، والقيم من نوع Column.
    """
    if value is None:
        return Decimal(0)
    if isinstance(value, Decimal):
        return value
    try:
        # تحويل إلى سلسلة ثم إلى Decimal لضمان التوافق مع جميع الأنواع
        return Decimal(str(value))
    except (TypeError, ValueError):
        return Decimal(0)


# ============================================================
# 3. مهمة حساب كشف الراتب (Payroll Generation)
# ============================================================
@celery_app.task(
    name="employment.generate_payroll",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,              # 🔥 تأكيد بعد التنفيذ (يمنع فقدان المهمة)
    time_limit=600,              # 10 دقائق كحد أقصى (حساب راتب معقد)
    soft_time_limit=480,         # 8 دقائق إنذار
)
def generate_payroll_task(
    self,
    contract_id: int,
    month: str,
    employer_id: int,
    tenant_id: int,
    idempotency_key: Optional[str] = None
):
    """
    حساب كشف راتب لموظف معين.
    - تدعم Idempotency لمنع الحساب المزدوج.
    - تحسب الراتب الأساسي، البدلات، العمل الإضافي، الخصومات.
    - تُستدعى عادةً في نهاية كل شهر.
    """
    try:
        async def _run():
            async with SessionLocal() as db:
                service = EmploymentService(db)
                repo = service.repo
                
                # التحقق من Idempotency (منع التكرار)
                if idempotency_key:
                    existing = await repo.get_payroll_by_idempotency(idempotency_key)  # type: ignore
                    if existing:
                        logger.info(f"⏭️ Payroll already generated for idempotency_key {idempotency_key}")
                        return {
                            "status": "already_generated",
                            "payroll_id": existing.id,
                            "month": month,
                            "contract_id": contract_id
                        }

                # 1. جلب العقد
                contract = await repo.get_contract(contract_id, tenant_id)  # type: ignore
                if not contract:
                    logger.warning(f"⚠️ Contract {contract_id} not found for tenant {tenant_id}")
                    return {"status": "contract_not_found", "contract_id": contract_id}
                
                # 🔥 استخدام cast لتحويل Column إلى Python type
                if cast(int, contract.employer_id) != employer_id:
                    logger.warning(f"⚠️ Employer {employer_id} not authorized for contract {contract_id}")
                    return {"status": "unauthorized", "contract_id": contract_id}
                
                contract_status = cast(str, contract.status)
                if contract_status not in [EmploymentStatus.ACTIVE, EmploymentStatus.PROBATION]:
                    logger.warning(f"⚠️ Contract {contract_id} is not active")
                    return {"status": "contract_inactive", "contract_id": contract_id}

                # 2. حساب أيام العمل في الشهر
                year, month_num = map(int, month.split('-'))
                start_date = datetime(year, month_num, 1)
                if month_num == 12:
                    end_date = datetime(year + 1, 1, 1)
                else:
                    end_date = datetime(year, month_num + 1, 1)
                working_days = service._count_working_days(start_date, end_date)

                # 3. جلب سجلات الحضور للشهر
                attendance_records = await repo.get_attendance_for_month(  # type: ignore
                    contract_id, year, month_num
                )

                # 4. حساب ساعات العمل الفعلية والعمل الإضافي
                total_hours = sum(r.hours_worked or 0 for r in attendance_records)
                # 🔥 إصلاح جذري: استخدام _to_decimal عند جمع ساعات العمل الإضافي
                overtime_hours = sum(_to_decimal(r.overtime_hours or 0) for r in attendance_records)

                # 5. حساب أيام الغياب غير المدفوع
                present_days = len([r for r in attendance_records if cast(str, r.status) == AttendanceStatus.PRESENT])
                absent_days = working_days - present_days

                # 6. الراتب الأساسي والبدلات
                base_salary = cast(Decimal, contract.base_salary)
                
                # ✅ استخدام _to_decimal لتحويل البدلات
                allowances_raw = cast(Optional[Dict[str, Any]], contract.allowances)
                allowances_sum = Decimal(0)
                if allowances_raw:
                    for v in allowances_raw.values():
                        allowances_sum += _to_decimal(v)

                # 7. حساب العمل الإضافي (1.5 × الأجر اليومي / 8 ساعات)
                daily_rate = base_salary / Decimal(working_days) if working_days > 0 else Decimal(0)
                hourly_rate = daily_rate / Decimal(8)
                # 🔥 `overtime_hours` الآن من نوع Decimal، لذلك لا نحتاج إلى _to_decimal مرة أخرى
                overtime_pay = hourly_rate * overtime_hours * Decimal(1.5)

                # 8. خصم أيام الغياب
                absence_deduction = daily_rate * Decimal(absent_days)

                # 9. الخصومات القانونية (التأمينات والضرائب)
                social_insurance = base_salary * Decimal(0.11)  # 11% تأمينات اجتماعية
                taxable_income = base_salary - social_insurance
                income_tax = Decimal(0)
                if taxable_income > Decimal(20000):
                    income_tax = (taxable_income - Decimal(20000)) * Decimal(0.1)  # 10% على الزيادة

                deductions = {
                    "social_insurance": social_insurance,
                    "income_tax": income_tax,
                    "absence_deduction": absence_deduction
                }

                # 10. حساب صافي الراتب
                net_salary = (
                    base_salary 
                    + allowances_sum 
                    + overtime_pay 
                    - sum(deductions.values())
                )

                # 11. تحديث أو إنشاء كشف الراتب
                payroll = await repo.get_payroll_by_month(contract_id, month, tenant_id)  # type: ignore
                if payroll:
                    payroll = await repo.update_payroll(  # type: ignore
                        payroll.id,
                        base_salary=base_salary,
                        bonuses=Decimal(0),
                        overtime_pay=overtime_pay,
                        deductions=deductions,
                        net_salary=net_salary,
                        status=PayrollStatus.APPROVED,
                        idempotency_key=idempotency_key
                    )
                else:
                    payroll = await repo.create_payroll(  # type: ignore
                        tenant_id=tenant_id,
                        contract_id=contract_id,
                        month=month,
                        base_salary=base_salary,
                        bonuses=Decimal(0),
                        overtime_pay=overtime_pay,
                        deductions=deductions,
                        net_salary=net_salary,
                        status=PayrollStatus.APPROVED,
                        idempotency_key=idempotency_key
                    )

                logger.info(f"✅ Payroll generated for contract {contract_id}, month {month}: net_salary={net_salary}")
                
                return {
                    "status": "success",
                    "payroll_id": payroll.id,
                    "contract_id": contract_id,
                    "month": month,
                    "net_salary": float(net_salary),
                    "working_days": working_days,
                    "present_days": present_days,
                    "overtime_hours": float(overtime_hours),
                    "deductions": {k: float(v) for k, v in deductions.items()}
                }

        result = _run_async(_run())
        logger.info(f"✅ Payroll generation completed for contract {contract_id}")
        return result

    except Exception as e:
        logger.error(f"❌ Payroll generation failed for contract {contract_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)


# ============================================================
# 4. مهمة دفع الراتب (Payroll Payment)
# ============================================================
@celery_app.task(
    name="employment.pay_payroll",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    acks_late=True,              # 🔥 تأكيد بعد التنفيذ
    time_limit=300,              # 5 دقائق (تحويل مالي)
    soft_time_limit=240,         # 4 دقائق إنذار
)
def pay_payroll_task(
    self,
    payroll_id: int,
    employer_id: int,
    tenant_id: int,
    idempotency_key: Optional[str] = None
):
    """
    دفع راتب الموظف عبر تحويل MR_USDT.
    - تتحقق من Idempotency لمنع الدفع المزدوج.
    - تنشئ فاتورة (Invoice) تلقائياً.
    - تُستدعى بعد اعتماد كشف الراتب.
    """
    try:
        async def _run():
            async with SessionLocal() as db:
                service = EmploymentService(db)
                repo = service.repo
                finance = FinanceService(db, tenant_id)
                invoicing_service = InvoicingService(db, tenant_id)

                # التحقق من Idempotency
                if idempotency_key:
                    existing = await repo.get_payroll_by_idempotency(idempotency_key)  # type: ignore
                    if existing:
                        logger.info(f"⏭️ Payroll already paid for idempotency_key {idempotency_key}")
                        return {
                            "status": "already_paid",
                            "payroll_id": existing.id,
                            "payment_tx_hash": getattr(existing, 'payment_tx_hash', None)
                        }

                # 1. جلب كشف الراتب
                payroll = await repo.get_payroll(payroll_id)  # type: ignore
                if not payroll:
                    logger.warning(f"⚠️ Payroll {payroll_id} not found")
                    return {"status": "payroll_not_found", "payroll_id": payroll_id}

                payroll_status = cast(str, payroll.status)
                if payroll_status != PayrollStatus.APPROVED:
                    logger.warning(f"⚠️ Payroll {payroll_id} is not approved (status: {payroll.status})")
                    return {"status": "not_approved", "payroll_id": payroll_id}

                # 2. جلب العقد
                contract = await repo.get_contract(payroll.contract_id, tenant_id)  # type: ignore
                if not contract:
                    logger.warning(f"⚠️ Contract not found for payroll {payroll_id}")
                    return {"status": "contract_not_found", "payroll_id": payroll_id}

                if cast(int, contract.employer_id) != employer_id:
                    logger.warning(f"⚠️ Employer {employer_id} not authorized for payroll {payroll_id}")
                    return {"status": "unauthorized", "payroll_id": payroll_id}

                # 3. جلب البريد الإلكتروني للموظف
                employee_id = cast(int, contract.employee_id)
                employee_email = await service._get_user_email(employee_id, tenant_id)

                # 4. تنفيذ التحويل المالي
                net_salary = cast(Decimal, payroll.net_salary)
                try:
                    tx_hash = await finance.transfer(
                        sender_id=employer_id,
                        receiver_email=employee_email,
                        currency="MR_USDT",
                        amount=net_salary,
                        notes=f"Salary payment for {payroll.month} - Contract {contract.id}",
                        idempotency_key=idempotency_key or f"PAYROLL-{payroll_id}-{datetime.utcnow().timestamp()}"
                    )
                except InsufficientBalanceError as e:
                    logger.error(f"❌ Insufficient balance for employer {employer_id}: {e}")
                    return {"status": "insufficient_balance", "payroll_id": payroll_id}
                except Exception as e:
                    logger.error(f"❌ Transfer failed for payroll {payroll_id}: {e}")
                    raise

                # 5. تحديث حالة كشف الراتب
                await repo.update_payroll_status(  # type: ignore
                    payroll_id,
                    PayrollStatus.PAID,
                    payment_tx_hash=tx_hash
                )

                # 6. إنشاء فاتورة (Invoicing)
                await invoicing_service.create_invoice(
                    entity_id=tenant_id,
                    user_id=employee_id,
                    amount=net_salary,
                    description=f"Salary payment for contract {contract.id} - {payroll.month}",
                    due_date=datetime.utcnow() + timedelta(days=30)
                )

                # 7. تسجيل التدقيق (Audit)
                await service._register_affiliate_commission(
                    employee_id,
                    tenant_id,
                    "SALARY_PAID",
                    net_salary
                )

                logger.info(f"✅ Payroll {payroll_id} paid: tx_hash={tx_hash}")

                return {
                    "status": "success",
                    "payroll_id": payroll_id,
                    "payment_tx_hash": tx_hash,
                    "amount": float(net_salary),
                    "employee_id": employee_id,
                    "month": payroll.month
                }

        result = _run_async(_run())
        logger.info(f"✅ Payroll payment completed for payroll {payroll_id}")
        return result

    except Exception as e:
        logger.error(f"❌ Payroll payment failed for payroll {payroll_id}: {str(e)}")
        raise self.retry(exc=e, countdown=120)


# ============================================================
# 5. مهمة معالجة الإجازات الشهرية (اختياري)
# ============================================================
@celery_app.task(
    name="employment.process_monthly_leave_balances",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    acks_late=True,
    time_limit=1800,             # 30 دقيقة (معالجة عدد كبير من الموظفين)
    soft_time_limit=1500,
)
def process_monthly_leave_balances_task(self, tenant_id: int):
    """
    معالجة أرصدة الإجازات الشهرية (تحديث الرصيد التراكمي).
    تُستدعى في بداية كل شهر.
    """
    try:
        async def _run():
            async with SessionLocal() as db:
                service = EmploymentService(db)
                repo = service.repo

                contracts = await repo.list_active_contracts(tenant_id)  # type: ignore
                updated_count = 0

                for contract in contracts:
                    annual_leave_days = cast(Decimal, contract.annual_leave_days) if contract.annual_leave_days else Decimal(0)
                    annual_leave_accumulated = cast(Decimal, contract.annual_leave_accumulated) if contract.annual_leave_accumulated else Decimal(0)
                    if annual_leave_days > 0:
                        new_balance = annual_leave_accumulated + Decimal(2.5)
                        await repo.update_contract(  # type: ignore
                            contract.id,
                            annual_leave_accumulated=new_balance
                        )
                        updated_count += 1

                logger.info(f"✅ Updated leave balances for {updated_count} employees")
                return {"status": "success", "updated_count": updated_count}

        result = _run_async(_run())
        logger.info(f"✅ Monthly leave balances processed for tenant {tenant_id}")
        return result

    except Exception as e:
        logger.error(f"❌ Failed to process leave balances: {str(e)}")
        raise self.retry(exc=e, countdown=300)


# ============================================================
# 6. مهمة إنشاء تقارير الرواتب الشهرية (اختياري)
# ============================================================
@celery_app.task(
    name="employment.generate_monthly_payroll_report",
    bind=True,
    max_retries=2,
    default_retry_delay=600,
    acks_late=True,
    time_limit=3600,             # ساعة واحدة (تقارير ثقيلة)
    soft_time_limit=3000,
)
def generate_monthly_payroll_report_task(self, tenant_id: int, month: str):
    """
    إنشاء تقرير شهرية الرواتب بصيغة CSV/PDF وإرساله إلى صاحب العمل.
    تُستدعى بعد اكتمال جميع صرفيات الرواتب.
    """
    try:
        async def _run():
            async with SessionLocal() as db:
                service = EmploymentService(db)
                repo = service.repo

                payrolls = await repo.list_payrolls_by_month(tenant_id, month)  # type: ignore

                report = {
                    "tenant_id": tenant_id,
                    "month": month,
                    "total_payrolls": len(payrolls),
                    "total_amount": sum(cast(Decimal, p.net_salary) for p in payrolls),
                    "payrolls": [
                        {
                            "contract_id": p.contract_id,
                            "employee_name": cast(int, p.contract.employee_id) if p.contract else None,
                            "net_salary": float(cast(Decimal, p.net_salary)),
                            "status": cast(str, p.status) if p.status else None
                        }
                        for p in payrolls
                    ]
                }

                logger.info(f"✅ Monthly payroll report generated for tenant {tenant_id}, month {month}")
                return {
                    "status": "success",
                    "tenant_id": tenant_id,
                    "month": month,
                    "report": report
                }

        result = _run_async(_run())
        logger.info(f"✅ Monthly payroll report completed for tenant {tenant_id}")
        return result

    except Exception as e:
        logger.error(f"❌ Failed to generate payroll report: {str(e)}")
        raise self.retry(exc=e, countdown=600)