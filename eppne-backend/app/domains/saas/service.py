# app/domains/saas/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import hashlib

from app.domains.saas.repository import SaaSRepository
from app.domains.saas.models import TenantSubscription, Invoice, TenantServiceAccess, TenantFeatureFlag
from app.domains.finance.service import FinanceService
from app.domains.finance.models import Transaction
from app.core.errors import (
    PermissionDeniedError,
    NotFoundError,
    ValidationError,
    InsufficientBalanceError,
)
from app.core.logging_conf import logger
from app.domains.saas.models import ServicePlan
class SaaSControlService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SaaSRepository(db)
        self.finance = FinanceService(db)

    # ==========================================
    # 1. التحكم في الوصول (Access Control)
    # ==========================================

    async def can_access_service(self, tenant_id: int, service_code: str) -> bool:
        """التحقق مما إذا كان المستأجر يملك صلاحية الوصول لخدمة معينة"""
        service = await self.repo.get_service_by_code(service_code)
        if not service:
            return False

        access = await self.repo.get_tenant_service_access(tenant_id, service.id)
        if not access or not access.is_active:
            return False

        subscription = await self.repo.get_active_subscription(tenant_id, service.id)
        if not subscription:
            return False

        # ✅ التحقق من فترة السماح (Grace Period)
        if subscription.status == "PAST_DUE":
            if subscription.grace_period_end_date and datetime.now(timezone.utc) < subscription.grace_period_end_date:
                return True
            else:
                await self.repo.update_subscription_status(subscription.id, "EXPIRED")
                return False

        return subscription.status in ["ACTIVE", "TRIAL"]

    async def check_and_enforce_access(self, tenant_id: int, service_code: str):
        """رفع استثناء إذا كانت الخدمة غير متاحة"""
        if not await self.can_access_service(tenant_id, service_code):
            raise PermissionDeniedError(
                f"الخدمة '{service_code}' غير متاحة. يرجى الاشتراك في الخطة المناسبة."
            )

    # ==========================================
    # 2. إدارة الاشتراكات (Subscriptions)
    # ==========================================

    async def create_subscription(
        self,
        tenant_id: int,
        plan_id: int,
        start_date: datetime = None,
        trial_days: int = 14,
    ) -> TenantSubscription:
        """إنشاء اشتراك جديد مع فترة تجريبية اختيارية"""
        plan = await self.repo.get_plan_by_id(plan_id)
        if not plan:
            raise NotFoundError("الخطة غير موجودة")

        # التحقق من عدم وجود اشتراك نشط لنفس الخدمة
        service_id = plan.service_id
        existing = await self.repo.get_active_subscription(tenant_id, service_id)
        if existing:
            raise ValidationError("يوجد اشتراك نشط لهذه الخدمة بالفعل")

        start = start_date or datetime.now(timezone.utc)
        trial_end = start + timedelta(days=trial_days)

        subscription = await self.repo.create_subscription(
            tenant_id=tenant_id,
            plan_id=plan_id,
            status="TRIAL",
            trial_end_date=trial_end,
            start_date=start,
            next_billing_date=trial_end + timedelta(days=30),
            idempotency_key=f"SUB-{tenant_id}-{plan_id}-{uuid.uuid4().hex[:12]}",
        )

        # إنشاء صلاحية وصول للخدمة
        access = await self.repo.get_tenant_service_access(tenant_id, service_id)
        if not access:
            await self.repo.create_service_access(
                tenant_id=tenant_id,
                service_id=service_id,
                access_level=plan.code.upper(),
                user_limit=plan.max_users,
            )

        logger.info(f"Subscription created: tenant {tenant_id}, plan {plan_id}, trial until {trial_end}")
        return subscription

    async def cancel_subscription(self, subscription_id: int, tenant_id: int) -> TenantSubscription:
        """إلغاء الاشتراك (إيقاف التجديد التلقائي)"""
        subscription = await self.repo.get_subscription(subscription_id)
        if not subscription or subscription.tenant_id != tenant_id:
            raise NotFoundError("الاشتراك غير موجود")

        if subscription.status in ["EXPIRED", "CANCELLED"]:
            raise ValidationError("الاشتراك ملغي بالفعل")

        return await self.repo.update_subscription(
            subscription_id,
            status="CANCELLED",
            auto_renew=False,
        )

    async def process_auto_renewals(self):
        """معالجة التجديد التلقائي للاشتراكات المنتهية (تُنفذ يومياً)"""
        subscriptions = await self.repo.get_subscriptions_for_renewal()
        results = []

        for sub in subscriptions:
            try:
                plan = await self.repo.get_plan_by_id(sub.plan_id)
                if not plan:
                    continue

                # محاولة خصم المبلغ من المحفظة
                tx = await self.finance.transfer(
                    sender_id=sub.tenant_id,
                    receiver_email="system@eppne.com",
                    currency=plan.currency,
                    amount=plan.price_monthly,
                    idempotency_key=f"AUTO-RENEW-{sub.id}-{datetime.now(timezone.utc).strftime('%Y-%m')}",
                    notes=f"تجديد اشتراك {plan.name} - {sub.tenant_id}",
                )

                # نجاح الدفع -> تحديث الاشتراك
                await self.repo.update_subscription(
                    sub.id,
                    status="ACTIVE",
                    next_billing_date=datetime.now(timezone.utc) + timedelta(days=30),
                    grace_period_end_date=None,
                )

                # إنشاء فاتورة
                await self._generate_invoice(
                    tenant_id=sub.tenant_id,
                    subscription_id=sub.id,
                    plan=plan,
                )

                results.append({"subscription_id": sub.id, "status": "SUCCESS", "tx_hash": tx.tx_hash})
                logger.info(f"Auto-renewal success: subscription {sub.id}")

            except InsufficientBalanceError:
                # ❌ رصيد غير كافٍ -> تفعيل فترة السماح
                await self.repo.update_subscription(
                    sub.id,
                    status="PAST_DUE",
                    grace_period_end_date=datetime.now(timezone.utc) + timedelta(days=3),
                )
                results.append({"subscription_id": sub.id, "status": "PAST_DUE"})
                logger.warning(f"Auto-renewal failed: subscription {sub.id} - insufficient balance")

            except Exception as e:
                logger.error(f"Auto-renewal error: subscription {sub.id} - {str(e)}")
                results.append({"subscription_id": sub.id, "status": "FAILED", "error": str(e)})

        return results

    # ==========================================
    # 3. الفواتير (Invoicing)
    # ==========================================

    async def _generate_invoice(
        self,
        tenant_id: int,
        subscription_id: int,
        plan: ServicePlan,
    ) -> Invoice:
        """إنشاء فاتورة جديدة مع Idempotency"""
        period = datetime.now(timezone.utc).strftime("%Y-%m")
        idempotency_key = hashlib.sha256(
            f"{tenant_id}:{subscription_id}:{period}".encode()
        ).hexdigest()

        existing = await self.repo.get_invoice_by_idempotency(idempotency_key)
        if existing:
            return existing

        invoice = await self.repo.create_invoice(
            tenant_id=tenant_id,
            subscription_id=subscription_id,
            invoice_number=f"INV-{uuid.uuid4().hex[:12].upper()}",
            amount=plan.price_monthly,
            currency=plan.currency,
            description=f"اشتراك {plan.name} - {period}",
            items=[{
                "service": plan.name,
                "period": period,
                "amount": float(plan.price_monthly),
                "currency": plan.currency,
            }],
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
            status="PENDING",
            idempotency_key=idempotency_key,
        )
        return invoice

    async def pay_invoice(self, invoice_id: int, tenant_id: int) -> Invoice:
        """دفع فاتورة باستخدام المحفظة"""
        invoice = await self.repo.get_invoice_by_id(invoice_id)
        if not invoice or invoice.tenant_id != tenant_id:
            raise NotFoundError("الفاتورة غير موجودة")

        if invoice.status != "PENDING":
            raise ValidationError("الفاتورة غير قابلة للدفع")

        try:
            tx = await self.finance.transfer(
                sender_id=tenant_id,
                receiver_email="system@eppne.com",
                currency=invoice.currency,
                amount=invoice.amount,
                idempotency_key=f"PAY-INV-{invoice.id}",
                notes=f"دفع فاتورة {invoice.invoice_number}",
            )

            await self.repo.update_invoice(
                invoice.id,
                status="PAID",
                paid_at=datetime.now(timezone.utc),
                paid_tx_hash=tx.tx_hash,
            )

            # تحديث حالة الاشتراك
            subscription = await self.repo.get_subscription(invoice.subscription_id)
            if subscription and subscription.status == "PAST_DUE":
                await self.repo.update_subscription(
                    subscription.id,
                    status="ACTIVE",
                    grace_period_end_date=None,
                )

            return invoice

        except InsufficientBalanceError:
            raise InsufficientBalanceError("الرصيد غير كافٍ لدفع الفاتورة")

    # ==========================================
    # 4. رايات الميزات (Feature Flags)
    # ==========================================

    async def toggle_feature_flag(
        self,
        tenant_id: int,
        service_code: str,
        feature_key: str,
        enabled: bool,
    ) -> TenantFeatureFlag:
        """تفعيل/تعطيل راية ميزة"""
        service = await self.repo.get_service_by_code(service_code)
        if not service:
            raise NotFoundError("الخدمة غير موجودة")

        return await self.repo.toggle_feature_flag(
            tenant_id=tenant_id,
            service_id=service.id,
            feature_key=feature_key,
            enabled=enabled,
        )

    async def get_feature_flag(
        self,
        tenant_id: int,
        service_code: str,
        feature_key: str,
    ) -> bool:
        """جلب حالة راية ميزة (افتراضياً False إذا لم توجد)"""
        service = await self.repo.get_service_by_code(service_code)
        if not service:
            return False

        flag = await self.repo.get_feature_flag(tenant_id, service.id, feature_key)
        return flag.is_enabled if flag else False

    # ==========================================
    # 5. لوحة التحكم (Dashboard)
    # ==========================================

    async def get_dashboard_stats(self) -> dict:
        """جلب إحصائيات SaaS للمشرفين"""
        services = await self.repo.get_all_services()
        total_subscriptions = 0
        total_invoices_paid = 0
        total_revenue = Decimal(0)

        for service in services:
            subscriptions = await self.repo.get_active_subscription_count(service.id)
            total_subscriptions += subscriptions

        invoices = await self.repo.get_all_invoices()
        for inv in invoices:
            if inv.status == "PAID":
                total_invoices_paid += 1
                total_revenue += inv.amount

        return {
            "total_services": len(services),
            "total_subscriptions": total_subscriptions,
            "total_invoices_paid": total_invoices_paid,
            "total_revenue_mrusdt": float(total_revenue),
            "revenue_currency": "MR_USDT",
        }