# app/domains/saas/service.py
# pyright: reportGeneralTypeIssues=false
# pyright: reportArgumentType=false

from sqlalchemy.ext.asyncio import AsyncSession
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
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
from app.core.system_account_service import get_or_create_system_account
from app.core.errors import (
    PermissionDeniedError,
    NotFoundError,
    ValidationError,
    InsufficientBalanceError,
)
from app.core.logging_conf import logger
from app.core.pagination import PaginatedResponse


class FeatureAccessStatus(str, Enum):
    """نتيجة check_feature_access — راجع §8.3 من
    saas-feature-flags-drift-session-log.md لتفاصيل سبب استخدام enum
    بدل bool بسيط هنا."""
    GRANTED = "granted"
    NO_ACTIVE_SUBSCRIPTION = "no_active_subscription"
    FEATURE_NOT_INCLUDED = "feature_not_included"


@dataclass(frozen=True)
class FeatureAccessCheck:
    status: FeatureAccessStatus
    tenant_id: int
    feature: str
    checked_subscription_ids: List[int] = field(default_factory=list)
    granting_subscription_id: Optional[int] = None

    @property
    def granted(self) -> bool:
        return self.status == FeatureAccessStatus.GRANTED


class SaaSControlService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = SaaSRepository(db)

    async def _get_tenant_admin_id(self, tenant_id: int) -> int:
        # الدافع الرسمي لفواتير/تجديدات التينانت هو AcademyTenant.admin_id
        # الإجباري الموجود بالفعل — راجع §7 بند 4 من مستند تصميم حساب
        # النظام الموحَّد لكل تينانت.
        from app.domains.academy.repository import AcademyRepository
        from app.domains.identity.repository import UserRepository
        academy_repo = AcademyRepository(self.db)
        tenant = await academy_repo.get_tenant_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("التينانت غير موجود")
        # الأدمن لازم يكون عضوًا في نفس التينانت — وإلا transfer() هيخصم من
        # محفظة (admin, tenant_id) لمستخدم مش عضو فيها. راجع
        # saas-sender-id-collision-fix-session-log.md §4.3-أ و§8.
        admin = await UserRepository(self.db).get_by_id(cast(int, tenant.admin_id), tenant_id)
        if admin is None:
            raise ValidationError("أدمن التينانت لا ينتمي لنفس التينانت — لا يمكن تحديد دافع الفاتورة")
        return cast(int, tenant.admin_id)

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

    async def check_feature_access(
        self,
        tenant_id: int,
        feature: str,
    ) -> FeatureAccessCheck:
        """يفحص هل عند الـtenant صلاحية استخدام feature معيّن، عبر union كل
        اشتراكاته النشطة/التجريبية الحالية (مش 'الأحدث' بس) — تُستخدَم من
        _check_saas_limits عبر 12 دومين. بديل get_active_subscription
        القديمة اللي كانت بترجع اشتراك واحد فقط ('الأحدث زمنيًا')، فكانت
        بتفشل بالخطأ لأي tenant عنده أكتر من اشتراك فعّال لخدمات مختلفة في
        نفس الوقت (حالة طبيعية ومتوقعة، مش استثناء).

        ⚠️ حدود متعمدة (مش عيوبًا خفية): الدالة دي **مش** بتتحقق إن
        الاشتراك اللي منحك الـfeature هو فعلًا اشتراك لنفس 'خدمة' الدومين
        اللي بيطلب الفحص — لو plan.features احتوت feature من نطاق خدمة
        تانية بالغلط، هتُمنح برضه. حل هذه النقطة يحتاج ربط رسمي
        feature→service_id غير موجود في الـschema الحالي، وهو خارج نطاق
        هذا الإصلاح عمدًا (راجع §6 من saas-feature-flags-drift-session-
        log.md — 'عيب تصميم أمني كامن'، غير قابل للاستغلال حاليًا لأن
        إنشاء اشتراك جديد عبر الـAPI الحي معطّل ببَج منفصل تمامًا
        (get_plan_by_id). ممنوع إصلاح get_plan_by_id بمعزل عن سد هذه
        النقطة، وإلا هيبقى قابل للاستغلال)."""
        subscriptions = await self.repo.get_all_active_subscriptions(tenant_id)
        checked_ids = [cast(int, s.id) for s in subscriptions]

        if not subscriptions:
            return FeatureAccessCheck(
                status=FeatureAccessStatus.NO_ACTIVE_SUBSCRIPTION,
                tenant_id=tenant_id,
                feature=feature,
                checked_subscription_ids=checked_ids,
            )

        for sub in subscriptions:
            plan_features = sub.plan.features if sub.plan else None
            if plan_features and feature in plan_features:
                return FeatureAccessCheck(
                    status=FeatureAccessStatus.GRANTED,
                    tenant_id=tenant_id,
                    feature=feature,
                    checked_subscription_ids=checked_ids,
                    granting_subscription_id=cast(int, sub.id),
                )

        return FeatureAccessCheck(
            status=FeatureAccessStatus.FEATURE_NOT_INCLUDED,
            tenant_id=tenant_id,
            feature=feature,
            checked_subscription_ids=checked_ids,
        )

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

        await self.db.commit()

        logger.info(f"Subscription created: tenant {self.tenant_id}, plan {plan_id}, trial until {trial_end}")

        await self._activate_affiliate_default_scope_if_needed(service_id)

        return subscription

    async def _activate_affiliate_default_scope_if_needed(self, service_id: int) -> None:
        """Hook تفعيل affiliate كخدمة SaaS (migration 045 / Phase 7، راجع
        .claude/reports/referral-affiliate-unified-implementation-session-log.md
        §4): أول اشتراك على service_code="affiliate" لهذا الـtenant ينشئ
        تلقائيًا نطاق ENTITY_WIDE افتراضي — بدونه أي محاولة توزيع عمولة
        تفشل بصمت (لا نطاق = لا referral link ممكن). idempotent
        (get_default_scope_id أولًا) لأن هذا المسار قد يُستدعى أكتر من
        مرة (تجديد/تغيير خطة) بعد إلغاء اشتراك سابق.

        مُستخرَجة كدالة مستقلة (بدل كتلة inline داخل create_subscription)
        عمدًا لتكون قابلة للاختبار مباشرة — `create_subscription` نفسها
        محجوبة حاليًا عبر الـAPI الحي ببَج منفصل تمامًا (`get_plan_by_id`
        chicken-and-egg، راجع
        .claude/reports/saas-get-plan-by-id-security-tradeoff-note.md)،
        فاختبارات Phase 9 بتنادي هذه الدالة مباشرة بعد seed اشتراك عبر
        الـrepo، بدل المرور بـ`create_subscription` كاملة."""
        service = await self.repo.get_service_by_id(service_id)
        if service and cast(str, service.code) == "affiliate":
            from app.domains.affiliate.service import AffiliateService
            affiliate_service = AffiliateService(self.db, self.tenant_id)
            if not await affiliate_service.get_default_scope_id():
                await affiliate_service.create_scope(
                    name="كل مبيعات المستأجر", scope_type="ENTITY_WIDE",
                )

    async def cancel_subscription(self, subscription_id: int) -> TenantSubscription:
        subscription = await self.repo.get_subscription(subscription_id, self.tenant_id)
        if not subscription:
            raise NotFoundError("الاشتراك غير موجود")

        if subscription.status in ["EXPIRED", "CANCELLED"]:
            raise ValidationError("الاشتراك ملغي بالفعل")

        result = await self.repo.update_subscription(
            subscription_id,
            self.tenant_id,
            status="CANCELLED",
            auto_renew=False,
            cancelled_at=datetime.now(timezone.utc),
        )
        await self.db.commit()
        return result

    async def process_auto_renewals(self, tenant_id: Optional[int] = None) -> List[dict]:
        """معالجة التجديد التلقائي للاشتراكات المنتهية (تُنفذ يومياً).

        [2026-09-08] tenant_id=None بيتمرر مباشرة لـget_subscriptions_for_renewal
        بلا fallback لـself.tenant_id — عبر كل المستأجرين، بنفس نمط
        check_past_due_subscriptions بالضبط: كل اشتراك بيتعامل بـ
        sub.tenant_id الحقيقي بتاعه، مش بقيمة self.tenant_id اللي اتبنى
        بيها الـservice instance. قبل التعديل، استدعاء بلا tenant_id
        (زي process_auto_renewals_task) كان بيقع على self.tenant_id
        (غالبًا 0 كـsentinel إداري) فيعالج تينانت واحد وهمي بس بدل كل
        التينانتات فعليًا — راجع backlog-process-auto-renewals-task-
        tenant-zero-noop (PROGRESS_LOG.md) لتفاصيل الاكتشاف والتحقق الحي."""
        subscriptions = await self.repo.get_subscriptions_for_renewal(tenant_id)
        results = []

        for sub in subscriptions:
            sub_tenant_id = cast(int, sub.tenant_id)
            try:
                plan = await self.repo.get_plan_by_id_admin(cast(int, sub.plan_id))
                if not plan:
                    continue

                payer_id = await self._get_tenant_admin_id(sub_tenant_id)
                system_account = await get_or_create_system_account(self.db, sub_tenant_id)
                finance = FinanceService(self.db, sub_tenant_id)
                async with self.db.begin_nested():
                    tx = await finance.transfer(
                        sender_id=payer_id,
                        receiver_email=cast(str, system_account.email),
                        currency=plan.currency,
                        amount=plan.price_monthly,
                        idempotency_key=f"AUTO-RENEW-{sub.id}-{datetime.now(timezone.utc).strftime('%Y-%m')}",
                        notes=f"تجديد اشتراك {plan.name} - {sub_tenant_id}",
                    )

                    await self.repo.update_subscription(
                        cast(int, sub.id),
                        sub_tenant_id,
                        status="ACTIVE",
                        next_billing_date=datetime.now(timezone.utc) + timedelta(days=30),
                        grace_period_end_date=None,
                    )

                    await self._generate_invoice(
                        tenant_id=sub_tenant_id,
                        subscription_id=cast(int, sub.id),
                        plan=plan,
                    )

                await self.db.commit()

                results.append({"subscription_id": cast(int, sub.id), "status": "SUCCESS", "tx_hash": tx.tx_hash})
                logger.info(f"Auto-renewal success: subscription {sub.id}")

            except InsufficientBalanceError:
                await self.repo.update_subscription(
                    cast(int, sub.id),
                    sub_tenant_id,
                    status="PAST_DUE",
                    grace_period_end_date=datetime.now(timezone.utc) + timedelta(days=3),
                )
                results.append({"subscription_id": cast(int, sub.id), "status": "PAST_DUE"})
                logger.warning(f"Auto-renewal failed: subscription {sub.id} - insufficient balance")

            except Exception as e:
                logger.error(f"Auto-renewal error: subscription {sub.id} - {str(e)}")
                results.append({"subscription_id": cast(int, sub.id), "status": "FAILED", "error": str(e)})

        return results

    async def generate_monthly_invoices(self, tenant_id: Optional[int] = None) -> int:
        """توليد فواتير الفوترة الشهرية اليدوية للاشتراكات ACTIVE بـ
        auto_renew=False (العميل اختار الدفع اليدوي — بعكس
        process_auto_renewals اللي تخص auto_renew=True) [2026-09-09].

        لكل اشتراك مستحق: تُصدر فاتورة PENDING عبر _generate_invoice
        الموجودة أصلًا (idempotent عبر idempotency_key، نفس الدالة
        المُستخدَمة جوّه process_auto_renewals) — **بلا** أي استدعاء
        لـFinanceService/transfer وبلا أي خصم فوري من المحفظة (ده الفرق
        الجوهري عن process_auto_renewals): الدفع الفعلي بيحصل لاحقًا عبر
        pay_invoice الموجودة. بعد الإصدار، next_billing_date بيتحدّث +30
        يوم (نفس منطق process_auto_renewals بالضبط) عشان الفاتورة الجاية
        متتصدرش تاني الشهر ده بالغلط.

        try/except لكل اشتراك على حدة — فشل واحد ما يوقفش معالجة الباقي.
        بلا فلتر tenant_id افتراضيًا (عبر كل المستأجرين)، بنفس نمط
        process_auto_renewals/check_past_due_subscriptions. ترجع عدد
        الفواتير المُصدرة فعليًا (مش عدد المرشَّحين للفحص)."""
        subscriptions = await self.repo.get_subscriptions_for_manual_billing(tenant_id)
        issued_count = 0

        for sub in subscriptions:
            sub_id = cast(int, sub.id)
            sub_tenant_id = cast(int, sub.tenant_id)
            try:
                plan = await self.repo.get_plan_by_id_admin(cast(int, sub.plan_id))
                if not plan:
                    continue

                async with self.db.begin_nested():
                    await self._generate_invoice(
                        tenant_id=sub_tenant_id,
                        subscription_id=sub_id,
                        plan=plan,
                    )

                    await self.repo.update_subscription(
                        sub_id,
                        sub_tenant_id,
                        next_billing_date=datetime.now(timezone.utc) + timedelta(days=30),
                    )

                await self.db.commit()
                issued_count += 1
                logger.info(f"Monthly invoice generated: subscription {sub_id}")

            except Exception as e:
                logger.error(f"Monthly invoice generation failed: subscription {sub_id} - {str(e)}")

        return issued_count

    async def check_past_due_subscriptions(self, tenant_id: Optional[int] = None) -> List[dict]:
        """فحص كل اشتراكات PAST_DUE وإرسال تنبيهات فترة السماح المرحلية
        (تُنفذ يومياً 3 صباحاً، بعد process_auto_renewals بساعة).
        [2026-09-08] — راجع خطة تصميم فترة السماح +
        .claude/reports/past-due-grace-period-notifications-implementation-session-log.md.

        بعكس process_auto_renewals (اللي بتقع على self.tenant_id لو
        tenant_id=None)، الدالة دي بتفحص عبر كل المستأجرين افتراضيًا
        (get_past_due_subscriptions(None) بلا فلتر) — كل اشتراك بيتعامل
        بـtenant_id بتاعه هو (sub.tenant_id)، مش self.tenant_id، عشان
        تشتغل صح بغض النظر عن الـtenant_id اللي اتبنى بيه الـservice
        instance (زي نمط SaaSControlService(db, 0) الإداري الموجود في
        router.py:273).

        فترة السماح 3 أيام (مضروبة فعليًا وقت التحويل لـPAST_DUE في
        process_auto_renewals، بلا تغيير هنا). المراحل:
        - يوم 0 (أكتر من يوم متبقي): تنبيه ببداية فترة السماح.
        - يوم 2 (يوم واحد أو أقل متبقي، لسه ساري): تذكير أخير.
        - يوم 3 (انتهت الفترة): تنبيه بالإيقاف + تحويل EXPIRED استباقيًا
          (بدل الاعتماد فقط على lazy check جوّه can_access_service).

        idempotency_key = f"SUB-PASTDUE-{sub.id}-{day_number}" لكل مرحلة
        يمنع تكرار الإرسال لو الـtask اتنفذت أكتر من مرة لنفس الاشتراك
        وهو لسه في نفس المرحلة."""
        from app.domains.communications.service import CommunicationsService

        subscriptions = await self.repo.get_past_due_subscriptions(tenant_id)
        comm_service = CommunicationsService(self.db)
        now = datetime.now(timezone.utc)
        results = []

        for sub in subscriptions:
            grace_end = sub.grace_period_end_date
            if grace_end is None:
                logger.warning(f"Past-due subscription {sub.id} has no grace_period_end_date - skipped")
                continue

            remaining = grace_end - now
            if remaining <= timedelta(0):
                day_number = 3
            elif remaining <= timedelta(days=1):
                day_number = 2
            else:
                day_number = 0

            sub_id = cast(int, sub.id)
            sub_tenant_id = cast(int, sub.tenant_id)

            try:
                admin_id = await self._get_tenant_admin_id(sub_tenant_id)

                if day_number == 0:
                    title = "تأخر الدفع"
                    body = "دفعتك اتأخرت، عندك 3 أيام سماح."
                elif day_number == 2:
                    title = "تنبيه: فترة السماح توشك على الانتهاء"
                    body = "باقي يوم واحد بس على انتهاء فترة السماح."
                else:
                    title = "تم إيقاف الخدمة"
                    body = "الخدمة اتوقفت بسبب انتهاء فترة السماح."

                await comm_service.send_notification(
                    user_id=admin_id,
                    title=title,
                    body=body,
                    data={"subscription_id": sub_id, "day": day_number},
                    channel="IN_APP",
                    idempotency_key=f"SUB-PASTDUE-{sub_id}-{day_number}",
                )

                if day_number == 3:
                    await self.repo.update_subscription_status(sub_id, sub_tenant_id, "EXPIRED")
                    await self.db.commit()

                results.append({"subscription_id": sub_id, "day": day_number, "status": "NOTIFIED"})

            except Exception as e:
                logger.error(f"Past-due check failed: subscription {sub_id} - {str(e)}")
                results.append({"subscription_id": sub_id, "status": "FAILED", "error": str(e)})

        return results

    async def check_and_expire_trials(self, tenant_id: Optional[int] = None) -> int:
        """فحص كل اشتراكات TRIAL المنتهية (trial_end_date <= الآن) وتحويلها
        لـEXPIRED (تُنفذ يوميًا 4 صباحًا، بنفس نمط check_past_due_subscriptions
        المبنية اليوم [2026-09-08]).

        بلا فلتر tenant_id افتراضيًا (get_trial_subscriptions(None,
        expired_only=True) — عبر كل المستأجرين) — كل اشتراك بيتعامل
        بـsub.tenant_id بتاعه هو، مش self.tenant_id، فمش متأثرة بقيمة
        tenant_id اللي اتبنى بيها الـservice instance (نمط
        SaaSControlService(db, 0) الإداري في saas_tasks.py).

        try/except حول كل اشتراك على حدة — فشل واحد ما يوقفش فحص الباقي.
        ترجع عدد الاشتراكات اللي اتحوّلت فعليًا لـEXPIRED (مش عدد
        المرشَّحين للفحص)."""
        subscriptions = await self.repo.get_trial_subscriptions(tenant_id, expired_only=True)
        expired_count = 0

        for sub in subscriptions:
            sub_id = cast(int, sub.id)
            sub_tenant_id = cast(int, sub.tenant_id)
            try:
                await self.repo.update_subscription_status(sub_id, sub_tenant_id, "EXPIRED")
                await self.db.commit()
                expired_count += 1
                logger.info(f"Trial expired: subscription {sub_id}")
            except Exception as e:
                logger.error(f"Trial expiry check failed: subscription {sub_id} - {str(e)}")

        return expired_count

    async def send_trial_expiry_reminders(self, tenant_id: Optional[int] = None) -> int:
        """إرسال تذكير "باقي يومين" لاشتراكات TRIAL اللي trial_end_date بتاعها
        بين الآن والآن+يومين (تُنفذ يوميًا، بنفس بنية check_past_due_subscriptions
        [2026-09-08] — راجع send-trial-expiry-reminders-task-fix-session-log.md).

        بتستخدم get_trial_subscriptions(tenant_id, expired_only=False) الموجودة
        بالفعل — مش expired_only=True زي check_and_expire_trials، لأن المطلوب
        هنا اشتراكات لسه سارية وقربت تنتهي مش اللي انتهت بالفعل — وتضيف فلتر
        محلي إضافي: now <= trial_end_date <= now + يومين.

        IN_APP بس — قناة EMAIL في CommunicationsService لسه stub فاضي (backlog
        منفصل)، ممنوع استخدامها هنا.

        idempotency_key = f"SUB-TRIAL-REMIND-{sub.id}" يمنع تكرار الإرسال لو
        الـtask اتنفذت أكتر من مرة والاشتراك لسه في نفس نافذة التذكير.

        try/except حول كل اشتراك على حدة — فشل واحد ما يوقفش فحص الباقي.
        ترجع عدد التذكيرات اللي اتبعتت فعلاً (مش عدد المرشَّحين للفحص)."""
        from app.domains.communications.service import CommunicationsService

        subscriptions = await self.repo.get_trial_subscriptions(tenant_id, expired_only=False)
        comm_service = CommunicationsService(self.db)
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(days=2)
        reminders_sent = 0

        for sub in subscriptions:
            trial_end = sub.trial_end_date
            if trial_end is None or not (now <= trial_end <= window_end):
                continue

            sub_id = cast(int, sub.id)
            sub_tenant_id = cast(int, sub.tenant_id)

            try:
                admin_id = await self._get_tenant_admin_id(sub_tenant_id)

                await comm_service.send_notification(
                    user_id=admin_id,
                    title="تنبيه: الفترة التجريبية توشك على الانتهاء",
                    body="باقي يومين بس على انتهاء الفترة التجريبية.",
                    data={"subscription_id": sub_id},
                    channel="IN_APP",
                    idempotency_key=f"SUB-TRIAL-REMIND-{sub_id}",
                )

                reminders_sent += 1
                logger.info(f"Trial expiry reminder sent: subscription {sub_id}")

            except Exception as e:
                logger.error(f"Trial expiry reminder failed: subscription {sub_id} - {str(e)}")

        return reminders_sent

    async def cleanup_cancelled_subscriptions(self, tenant_id: Optional[int] = None) -> int:
        """المرحلة أ فقط من تنظيف الاشتراكات الملغاة — تعطيل
        TenantServiceAccess.is_active للاشتراكات CANCELLED منذ 30 يومًا
        فأكثر (cancelled_at <= الآن - 30 يوم). بلا أي حذف أو تعمية
        لبيانات شخصية — ده مؤجَّل عمدًا لجلسة تصميم منفصلة تراجع دومين
        privacy (راجع cleanup-cancelled-subscriptions-task-fix-session-
        log.md §backlog، ونطاق ضيق موثَّق صراحةً هناك، بعكس ادّعاء
        الـdocstring الأصلي في saas_tasks.py "حذف بيانات المستخدمين").

        اشتراكات CANCELLED من قبل migration 048 (cancelled_at لسه NULL،
        زي id=50) مُستبعدة بالكامل — get_cancelled_subscriptions_for_cleanup
        بتفلتر cancelled_at IS NOT NULL صراحةً، بلا أي fallback على
        updated_at (غير موثوق كفاية: بيتغيّر لأي تعديل على الصف، مش
        بالضرورة وقت الإلغاء).

        الخدمة المرتبطة بكل اشتراك بتتحدد عبر plan.service_id (نفس FK
        المباشر المستخدَم في get_active_subscription، مش
        PlanServiceAccess many-to-many — ده pilot دومين insurance فقط
        حاليًا، راجع تعليق get_active_subscription_via_plan_access في
        repository.py). لو الخطة بلا service_id (nullable من migration
        046) أو مفيش TenantServiceAccess مطابق أصلًا أو هو معطَّل
        بالفعل، الاشتراك بيتخطى بصمت (مش عدّ كـ"معطَّل").

        try/except حول كل اشتراك على حدة — فشل واحد ما يوقفش فحص الباقي.
        ترجع عدد صفوف TenantServiceAccess اللي اتعطَّلت فعليًا (مش عدد
        الاشتراكات المرشَّحة للفحص)."""
        subscriptions = await self.repo.get_cancelled_subscriptions_for_cleanup(tenant_id)
        disabled_count = 0

        for sub in subscriptions:
            sub_id = cast(int, sub.id)
            sub_tenant_id = cast(int, sub.tenant_id)
            try:
                plan = await self.repo.get_plan_by_id_admin(cast(int, sub.plan_id))
                if not plan or plan.service_id is None:
                    continue

                access = await self.repo.get_tenant_service_access(sub_tenant_id, cast(int, plan.service_id))
                if not access or not cast(bool, access.is_active):
                    continue

                await self.repo.update_service_access(cast(int, access.id), is_active=False)
                await self.db.commit()
                disabled_count += 1
                logger.info(f"Service access disabled for cancelled subscription {sub_id}")

            except Exception as e:
                logger.error(f"Cleanup cancelled subscription failed: subscription {sub_id} - {str(e)}")

        return disabled_count

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

        subscription = await self.repo.get_active_subscription_via_plan_access(self.tenant_id, service_id)
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

        payer_id = await self._get_tenant_admin_id(self.tenant_id)
        system_account = await get_or_create_system_account(self.db, self.tenant_id)
        finance = FinanceService(self.db, self.tenant_id)
        async with self.db.begin_nested():
            try:
                tx = await finance.transfer(
                    sender_id=payer_id,
                    receiver_email=cast(str, system_account.email),
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

            except InsufficientBalanceError:
                raise InsufficientBalanceError("الرصيد غير كافٍ لدفع الفاتورة")

        await self.db.commit()
        return invoice

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
        results = await self.process_auto_renewals(target)
        await self.db.commit()
        return results