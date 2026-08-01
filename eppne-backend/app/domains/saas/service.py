# app/domains/saas/service.py
# pyright: reportGeneralTypeIssues=false
# pyright: reportArgumentType=false

from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import hashlib
from typing import Optional, List, Dict, Any, cast

from app.domains.saas.repository import SaaSRepository
from app.domains.saas.models import (
    ServiceCatalog,
    TenantSubscription,
    Invoice,
    TenantServiceAccess,
    TenantFeatureFlag,
    ServicePlan,
)
from app.domains.saas.schemas import TenantSubscriptionResponse, InvoiceResponse
from app.domains.finance.service import FinanceService
from app.core.errors import (
    PermissionDeniedError,
    NotFoundError,
    ValidationError,
    InsufficientBalanceError,
)
from app.core.logging_conf import logger
from app.core.pagination import PaginatedResponse


class SaaSControlService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = SaaSRepository(db)
        self.finance = FinanceService(db, tenant_id)

    # ==========================================
    # 1. الخدمات (Services) – عامة (للمشرفين)
    # ==========================================
    async def get_all_services(self) -> List[ServiceCatalog]:
        return await self.repo.get_all_services()

    async def get_service_by_id(self, service_id: int) -> ServiceCatalog:
        service = await self.repo.get_service_by_id(service_id)
        if not service:
            raise NotFoundError("الخدمة غير موجودة")
        return service

    async def create_service(self, data: Dict[str, Any]) -> ServiceCatalog:
        return await self.repo.create_service(**data)

    # ==========================================
    # 2. خطط التسعير (Plans)
    # ==========================================
    async def get_plans_by_service(self, service_id: int) -> List[ServicePlan]:
        return await self.repo.get_plans_by_service(service_id)

    async def create_plan(self, data: Dict[str, Any]) -> ServicePlan:
        return await self.repo.create_plan(**data)

    # ==========================================
    # 3. اشتراكات المستأجر (Subscriptions)
    # ==========================================
    async def get_tenant_subscriptions(
        self, skip: int = 0, limit: int = 20
    ) -> PaginatedResponse[TenantSubscriptionResponse]:
        return await self.repo.get_tenant_subscriptions(self.tenant_id, skip, limit)

    async def get_subscription(self, subscription_id: int) -> TenantSubscription:
        sub = await self.repo.get_subscription(subscription_id, self.tenant_id)
        if not sub:
            raise NotFoundError("الاشتراك غير موجود")
        return sub

    async def get_subscription_status(self, subscription_id: int) -> dict:
        sub = await self.get_subscription(subscription_id)
        plan = await self.repo.get_plan_by_id_admin(cast(int, sub.plan_id))
        return {
            "id": sub.id,
            "status": sub.status,
            "plan": plan.name if plan else None,
            "grace_period_end_date": sub.grace_period_end_date,
            "next_billing_date": sub.next_billing_date,
            "is_active": sub.status in ["ACTIVE", "TRIAL"],
        }

    async def create_subscription(
        self,
        plan_id: int,
        start_date: Optional[datetime] = None,
        trial_days: int = 14,
    ) -> TenantSubscription:
        # التحقق من أن الخطة تخص خدمة متاحة للمستأجر
        plan = await self.repo.get_plan_by_id(plan_id, self.tenant_id)
        if not plan:
            raise NotFoundError("الخطة غير موجودة أو غير متاحة لك")

        service_id = cast(int, plan.service_id)
        existing = await self.repo.get_active_subscription(self.tenant_id, service_id)
        if existing:
            raise ValidationError("يوجد اشتراك نشط لهذه الخدمة بالفعل")

        start = start_date or datetime.now(timezone.utc)
        trial_end = start + timedelta(days=trial_days)

        async with self.db.begin_nested():
            subscription = await self.repo.create_subscription(
                tenant_id=self.tenant_id,
                plan_id=plan_id,
                status="TRIAL",
                trial_end_date=trial_end,
                start_date=start,
                next_billing_date=trial_end + timedelta(days=30),
                idempotency_key=f"SUB-{self.tenant_id}-{plan_id}-{uuid.uuid4().hex[:12]}",
            )

            access = await self.repo.get_tenant_service_access(self.tenant_id, service_id)
            if not access:
                await self.repo.create_service_access(
                    tenant_id=self.tenant_id,
                    service_id=service_id,
                    access_level=plan.code.upper(),
                    user_limit=plan.max_users,
                )

        logger.info(f"Subscription created: tenant {self.tenant_id}, plan {plan_id}, trial until {trial_end}")
        return subscription

    async def cancel_subscription(self, subscription_id: int) -> TenantSubscription:
        subscription = await self.repo.get_subscription(subscription_id, self.tenant_id)
        if not subscription:
            raise NotFoundError("الاشتراك غير موجود")

        if subscription.status in ["EXPIRED", "CANCELLED"]:
            raise ValidationError("الاشتراك ملغي بالفعل")

        return await self.repo.update_subscription(
            subscription_id,
            self.tenant_id,
            status="CANCELLED",
            auto_renew=False,
        )

    async def process_auto_renewals(self, tenant_id: Optional[int] = None) -> List[dict]:
        """معالجة التجديد التلقائي للاشتراكات المنتهية (تُنفذ يومياً)."""
        target_tenant = tenant_id if tenant_id is not None else self.tenant_id
        subscriptions = await self.repo.get_subscriptions_for_renewal(target_tenant)
        results = []

        for sub in subscriptions:
            try:
                plan = await self.repo.get_plan_by_id_admin(cast(int, sub.plan_id))
                if not plan:
                    continue

                async with self.db.begin_nested():
                    tx = await self.finance.transfer(
                        sender_id=target_tenant,
                        receiver_email="system@eppne.com",
                        currency=plan.currency,
                        amount=plan.price_monthly,
                        idempotency_key=f"AUTO-RENEW-{sub.id}-{datetime.now(timezone.utc).strftime('%Y-%m')}",
                        notes=f"تجديد اشتراك {plan.name} - {target_tenant}",
                    )

                    await self.repo.update_subscription(
                        cast(int, sub.id),
                        target_tenant,
                        status="ACTIVE",
                        next_billing_date=datetime.now(timezone.utc) + timedelta(days=30),
                        grace_period_end_date=None,
                    )

                    await self._generate_invoice(
                        tenant_id=target_tenant,
                        subscription_id=cast(int, sub.id),
                        plan=plan,
                    )

                    results.append({"subscription_id": cast(int, sub.id), "status": "SUCCESS", "tx_hash": tx.tx_hash})
                    logger.info(f"Auto-renewal success: subscription {sub.id}")

            except InsufficientBalanceError:
                await self.repo.update_subscription(
                    cast(int, sub.id),
                    target_tenant,
                    status="PAST_DUE",
                    grace_period_end_date=datetime.now(timezone.utc) + timedelta(days=3),
                )
                results.append({"subscription_id": cast(int, sub.id), "status": "PAST_DUE"})
                logger.warning(f"Auto-renewal failed: subscription {sub.id} - insufficient balance")

            except Exception as e:
                logger.error(f"Auto-renewal error: subscription {sub.id} - {str(e)}")
                results.append({"subscription_id": cast(int, sub.id), "status": "FAILED", "error": str(e)})

        return results

    # ==========================================
    # 4. صلاحيات الوصول (Access Control)
    # ==========================================
    async def can_access_service(self, service_code: str) -> bool:
        service = await self.repo.get_service_by_code(service_code)
        if not service:
            return False

        service_id = cast(int, service.id)
        access = await self.repo.get_tenant_service_access(self.tenant_id, service_id)
        if access is None or not cast(bool, access.is_active):
            return False

        subscription = await self.repo.get_active_subscription(self.tenant_id, service_id)
        if subscription is None:
            return False

        if subscription.status == "PAST_DUE":
            grace_end = subscription.grace_period_end_date
            if grace_end is not None and datetime.now(timezone.utc) < grace_end:
                return True
            else:
                await self.repo.update_subscription_status(cast(int, subscription.id), self.tenant_id, "EXPIRED")
                return False

        return subscription.status in ["ACTIVE", "TRIAL"]

    async def check_and_enforce_access(self, service_code: str):
        if not await self.can_access_service(service_code):
            raise PermissionDeniedError(
                f"الخدمة '{service_code}' غير متاحة. يرجى الاشتراك في الخطة المناسبة."
            )

    async def get_services_access(self) -> List[Dict[str, Any]]:
        return await self.repo.get_services_with_access(self.tenant_id)

    async def check_service_access(self, service_code: str) -> dict:
        accessible = await self.can_access_service(service_code)
        reason = None
        if not accessible:
            reason = "الخدمة غير متاحة. يرجى الاشتراك في الخطة المناسبة."
        return {"service_code": service_code, "accessible": accessible, "reason": reason}

    # ==========================================
    # 5. الفواتير (Invoicing)
    # ==========================================
    async def _generate_invoice(
        self,
        tenant_id: int,
        subscription_id: int,
        plan: ServicePlan,
    ) -> Invoice:
        period = datetime.now(timezone.utc).strftime("%Y-%m")
        idempotency_key = hashlib.sha256(
            f"{tenant_id}:{subscription_id}:{period}".encode()
        ).hexdigest()

        existing = await self.repo.get_invoice_by_idempotency(idempotency_key, tenant_id)
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

    async def get_tenant_invoices(self, skip: int = 0, limit: int = 20) -> PaginatedResponse[InvoiceResponse]:
        return await self.repo.get_tenant_invoices(self.tenant_id, skip, limit)

    async def get_invoice(self, invoice_id: int) -> Invoice:
        invoice = await self.repo.get_invoice_by_id(invoice_id, self.tenant_id)
        if not invoice:
            raise NotFoundError("الفاتورة غير موجودة")
        return invoice

    async def pay_invoice(self, invoice_id: int) -> Invoice:
        invoice = await self.get_invoice(invoice_id)
        if invoice.status != "PENDING":
            raise ValidationError("الفاتورة غير قابلة للدفع")

        async with self.db.begin_nested():
            try:
                tx = await self.finance.transfer(
                    sender_id=self.tenant_id,
                    receiver_email="system@eppne.com",
                    currency=invoice.currency,
                    amount=invoice.amount,
                    idempotency_key=f"PAY-INV-{invoice.id}",
                    notes=f"دفع فاتورة {invoice.invoice_number}",
                )

                await self.repo.update_invoice(
                    cast(int, invoice.id),
                    self.tenant_id,
                    status="PAID",
                    paid_at=datetime.now(timezone.utc),
                    paid_tx_hash=tx.tx_hash,
                )

                subscription = await self.repo.get_subscription(cast(int, invoice.subscription_id), self.tenant_id)
                if subscription is not None and subscription.status == "PAST_DUE":
                    await self.repo.update_subscription(
                        cast(int, subscription.id),
                        self.tenant_id,
                        status="ACTIVE",
                        grace_period_end_date=None,
                    )

                return invoice

            except InsufficientBalanceError:
                raise InsufficientBalanceError("الرصيد غير كافٍ لدفع الفاتورة")

    # ==========================================
    # 6. رايات الميزات (Feature Flags)
    # ==========================================
    async def toggle_feature_flag(
        self,
        service_code: str,
        feature_key: str,
        enabled: bool,
    ) -> TenantFeatureFlag:
        service = await self.repo.get_service_by_code(service_code)
        if not service:
            raise NotFoundError("الخدمة غير موجودة")

        return await self.repo.toggle_feature_flag(
            tenant_id=self.tenant_id,
            service_id=cast(int, service.id),
            feature_key=feature_key,
            enabled=enabled,
        )

    async def get_feature_flag(
        self,
        service_code: str,
        feature_key: str,
    ) -> bool:
        service = await self.repo.get_service_by_code(service_code)
        if not service:
            return False

        flag = await self.repo.get_feature_flag(self.tenant_id, cast(int, service.id), feature_key)
        return cast(bool, flag.is_enabled) if flag else False

    async def list_feature_flags(self) -> List[TenantFeatureFlag]:
        return await self.repo.get_all_feature_flags_for_tenant(self.tenant_id)

    # ==========================================
    # 7. لوحة التحكم (Dashboard) – للمشرفين
    # ==========================================
    async def get_dashboard_stats(self) -> dict:
        services = await self.repo.get_all_services()
        total_subscriptions = 0
        total_invoices_paid = 0
        total_revenue = Decimal(0)

        for service in services:
            count = await self.repo.get_active_subscription_count(cast(int, service.id))
            total_subscriptions += count

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

    # ==========================================
    # 8. دوال إدارية (Admin)
    # ==========================================
    async def get_tenant_subscriptions_admin(
        self, tenant_id: int, skip: int = 0, limit: int = 20
    ) -> PaginatedResponse[TenantSubscriptionResponse]:
        return await self.repo.get_tenant_subscriptions(tenant_id, skip, limit)

    async def trigger_renewals(self, tenant_id: Optional[int] = None):
        """تشغيل مهمة تجديد الاشتراكات يدوياً (للمشرفين)."""
        target = tenant_id if tenant_id is not None else self.tenant_id
        return await self.process_auto_renewals(target)