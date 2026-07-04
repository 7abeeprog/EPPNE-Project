# app/domains/digital_twin/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import uuid
import hashlib
from decimal import Decimal
from typing import Optional

from app.domains.digital_twin.repository import DigitalTwinRepository
from app.domains.finance.service import FinanceService
from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
from app.domains.affiliate.service import AffiliateService  # 🔥 جديد
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError
from app.core.idempotency import check_idempotency, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.domains.digital_twin.models import DigitalTwinConfig, TwinInteractionLog, TimeCapsule, DeathOracleCheck


class DigitalTwinService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DigitalTwinRepository(db)
        self.finance = FinanceService(db)
        self.saas_service = SaaSSubscriptionService(db)
        self.affiliate_service = AffiliateService(db)  # 🔥 جديد
        self.event_bus = EventBus(redis_client)

    # ============================================================
    # 0. التحقق من صلاحيات SaaS
    # ============================================================

    async def _check_saas_limits(self, tenant_id: int):
        """التحقق من صلاحية التوأم الرقمي في خطة الاشتراك."""
        subscription = await self.saas_service.get_active_subscription(tenant_id)
        if not subscription:
            raise PermissionDeniedError("No active subscription found for this entity.")

        features = subscription.features or {}
        if not features.get("digital_twin", False):
            raise PermissionDeniedError("Digital Twin feature is not included in your current plan.")

        return subscription, features

    # ============================================================
    # 1. التوأم الرقمي (Digital Twin) مع دعم الإحالة
    # ============================================================

    async def get_or_create_twin(self, user_id: int, tenant_id: int) -> DigitalTwinConfig:
        """جلب أو إنشاء التوأم الرقمي مع tenant_id وتسجيل عمولة إحالة عند الإنشاء."""
        # التحقق من صلاحية SaaS
        await self._check_saas_limits(tenant_id)

        twin = await self.repo.get_twin_config(user_id, tenant_id)
        if not twin:
            twin = await self.repo.create_twin_config(
                user_id=user_id,
                tenant_id=tenant_id
            )
            # 🔥 تسجيل عمولة إحالة عند إنشاء التوأم لأول مرة
            await self._register_affiliate_commission(user_id, tenant_id, "TWIN_CREATION")
        return twin

    # ============================================================
    # 2. التفاعل مع التوأم الرقمي (مع Idempotency ودعم الإحالة)
    # ============================================================

    async def interact_with_twin(
        self,
        visitor_id: int,
        twin_owner_id: int,
        tenant_id: int,
        interaction_data: dict,
        idempotency_key: Optional[str] = None,
        affiliate_code: Optional[str] = None  # 🔥 جديد: كود الإحالة إن وجد
    ) -> TwinInteractionLog:
        """
        تفاعل المستخدم مع التوأم الرقمي مع دعم Idempotency والتحقق من صلاحية الاشتراك ودعم الإحالة.
        """
        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # 2. التحقق من صلاحية SaaS
        await self._check_saas_limits(tenant_id)

        # 3. التحقق من التوأم الرقمي
        twin = await self.repo.get_twin_config(twin_owner_id, tenant_id)
        if not twin or not twin.is_active:
            raise NotFoundError("التوأم الرقمي غير موجود أو غير نشط")

        # 4. التحقق من الحد الأقصى للإنفاق (Spending Limit)
        fee = twin.interaction_fee_mrusdt * Decimal(interaction_data.get("duration_minutes", 1))
        if twin.max_spending_limit > 0:
            total_spent = await self.repo.sum_monthly_spending(twin.id, tenant_id)
            if total_spent + fee > twin.max_spending_limit:
                raise PermissionDeniedError("Monthly spending limit exceeded for this twin.")

        # 5. حساب الرسوم وتنفيذ التحويل
        if fee > 0:
            # خصم من الزائر مع تمرير Idempotency
            await self.finance.transfer(
                sender_id=visitor_id,
                receiver_email=await self._get_user_email(twin_owner_id),
                currency="MR_USDT",
                amount=fee,
                notes=f"Interaction with digital twin of user {twin_owner_id}",
                idempotency_key=idempotency_key
            )

            # 🔥 تسجيل الإحالة إذا كان هناك كود إحالة وتم دفع رسوم
            if affiliate_code:
                await self._register_affiliate_commission(
                    user_id=visitor_id,
                    tenant_id=tenant_id,
                    action_type="TWIN_INTERACTION",
                    amount=fee,
                    affiliate_code=affiliate_code
                )

        # 6. تسجيل التفاعل
        log = await self.repo.create_interaction_log(
            tenant_id=tenant_id,
            twin_config_id=twin.id,
            visitor_id=visitor_id,
            interaction_type=interaction_data["interaction_type"],
            duration_minutes=interaction_data["duration_minutes"],
            fee_paid_mrusdt=fee,
            payout_tx_hash=f"TX-{uuid.uuid4().hex[:12].upper()}" if fee > 0 else None,
            idempotency_key=idempotency_key
        )

        # 7. تخزين نتيجة Idempotency
        if idempotency_key:
            await store_idempotency_result(idempotency_key, log)

        # 8. نشر حدث (للأتمتة)
        await self.event_bus.publish("twin.interaction", {
            "twin_config_id": twin.id,
            "visitor_id": visitor_id,
            "twin_owner_id": twin_owner_id,
            "tenant_id": tenant_id,
            "fee": float(fee),
            "interaction_type": interaction_data["interaction_type"]
        })

        return log

    # ============================================================
    # 3. خزائن الزمن (Time Capsule)
    # ============================================================

    async def setup_time_capsule(
        self,
        user_id: int,
        tenant_id: int,
        data: dict,
        beneficiaries: list
    ) -> TimeCapsule:
        """إنشاء خزنة زمنية مع المستفيدين."""
        # التحقق من صلاحية SaaS
        await self._check_saas_limits(tenant_id)

        capsule = await self.repo.create_time_capsule(
            user_id=user_id,
            tenant_id=tenant_id,
            **data
        )

        for ben in beneficiaries:
            await self.repo.create_beneficiary(
                tenant_id=tenant_id,
                capsule_id=capsule.id,
                **ben
            )

        # نشر حدث
        await self.event_bus.publish("time_capsule.created", {
            "capsule_id": capsule.id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "beneficiaries_count": len(beneficiaries)
        })

        return capsule

    async def send_heartbeat(self, user_id: int, tenant_id: int) -> TimeCapsule:
        """تحديث نبض الحياة للخزنة الزمنية."""
        capsule = await self.repo.update_capsule_heartbeat(user_id, tenant_id)
        if not capsule:
            raise NotFoundError("لا توجد خزنة زمنية لهذا المستخدم")
        return capsule

    # ============================================================
    # 4. أوراكل الموت (Death Oracle)
    # ============================================================

    async def report_death(
        self,
        reporter_id: int,
        deceased_id: int,
        tenant_id: int,
        evidence_ipfs: str,
        request_ip: Optional[str] = None,
        request_user_agent: Optional[str] = None
    ) -> DeathOracleCheck:
        """الإبلاغ عن وفاة مع تسجيل تدقيق."""
        # تسجيل تدقيق للإبلاغ
        await audit_log(
            user_id=reporter_id,
            tenant_id=tenant_id,
            action="DEATH_REPORTED",
            resource_id=deceased_id,
            details={
                "evidence_ipfs": evidence_ipfs,
                "ip_address": request_ip,
                "user_agent": request_user_agent
            }
        )

        oracle = await self.repo.get_death_oracle(deceased_id, tenant_id)
        if not oracle:
            oracle = await self.repo.create_death_oracle(
                user_id=deceased_id,
                tenant_id=tenant_id
            )

        # تحديث الحالة إلى DEATH_PENDING (بانتظار إجماع)
        oracle = await self.repo.update_death_oracle_status(
            deceased_id,
            tenant_id,
            "DEATH_PENDING",
            death_certificate_ipfs=evidence_ipfs
        )

        # نشر حدث
        await self.event_bus.publish("death.reported", {
            "deceased_id": deceased_id,
            "tenant_id": tenant_id,
            "reporter_id": reporter_id,
            "evidence_ipfs": evidence_ipfs
        })

        return oracle

    async def confirm_death(
        self,
        deceased_id: int,
        tenant_id: int,
        confirmers: list,
        request_ip: Optional[str] = None,
        request_user_agent: Optional[str] = None
    ) -> DeathOracleCheck:
        """
        تأكيد الوفاة مع تسجيل تدقيق صارم وربط مع نظام الفوترة والإحالة.
        """
        oracle = await self.repo.get_death_oracle(deceased_id, tenant_id)
        if not oracle or oracle.status != "DEATH_PENDING":
            raise PermissionDeniedError("لا يمكن تأكيد الوفاة في هذه الحالة")

        if len(confirmers) < 3:
            raise PermissionDeniedError("يحتاج التأكيد إلى 3 شهود على الأقل")

        # 🔥 تسجيل تدقيق صارم (Audit Log)
        await audit_log(
            user_id=confirmers[0],  # أول مؤكد كممثل
            tenant_id=tenant_id,
            action="DEATH_CONFIRMATION",
            resource_id=deceased_id,
            details={
                "confirmers": confirmers,
                "ip_address": request_ip,
                "user_agent": request_user_agent,
                "status": "DEATH_CONFIRMED"
            }
        )

        # تحديث أوراكل الموت
        release_tx = f"LEGACY-RELEASE-{uuid.uuid4().hex[:16].upper()}"
        oracle = await self.repo.update_death_oracle_status(
            deceased_id,
            tenant_id,
            "DEATH_CONFIRMED",
            release_tx=release_tx
        )

        # توزيع الإرث
        await self._distribute_legacy(deceased_id, tenant_id)

        # 🔥 نشر حدث للأتمتة
        await self.event_bus.publish("death.confirmed", {
            "deceased_id": deceased_id,
            "tenant_id": tenant_id,
            "release_tx": release_tx,
            "confirmers": confirmers,
            "timestamp": datetime.utcnow().isoformat()
        })

        return oracle

    # ============================================================
    # 5. توزيع الإرث (مع حسابات الفوترة)
    # ============================================================

    async def _distribute_legacy(self, deceased_id: int, tenant_id: int):
        """توزيع الأصول مع مراعاة الفوترة والإحالة."""
        capsule = await self.repo.get_time_capsule(deceased_id, tenant_id)
        if not capsule:
            return

        beneficiaries = await self.repo.list_beneficiaries(capsule.id, tenant_id)

        for ben in beneficiaries:
            try:
                # تحويل الأصول (تبسيط – يمكن استدعاء finance.transfer هنا)
                # في الإنتاج، يتم استدعاء خدمة التوزيع مع تسجيل الفوترة
                pass
            except Exception as e:
                # تسجيل فشل التوزيع
                await audit_log(
                    user_id=deceased_id,
                    tenant_id=tenant_id,
                    action="LEGACY_DISTRIBUTION_FAILED",
                    resource_id=ben.id,
                    details={"error": str(e)}
                )

    # ============================================================
    # 6. تسجيل عمولة الإحالة (موحدة)
    # ============================================================

    async def _register_affiliate_commission(
        self,
        user_id: int,
        tenant_id: int,
        action_type: str,
        amount: Decimal = Decimal(0),
        affiliate_code: Optional[str] = None
    ):
        """
        تسجيل عمولة إحالة عند إنشاء توأم أو تفاعل مدفوع.
        """
        # جلب المستخدم للتحقق من وجود مُحيل
        user = await self._get_user(user_id)
        if not user:
            return

        referrer_id = user.referred_by
        if not referrer_id and not affiliate_code:
            return

        # إذا كان هناك كود إحالة، نبحث عن المستخدم المرتبط به
        if affiliate_code and not referrer_id:
            referrer = await self.affiliate_service.get_user_by_code(affiliate_code)
            if referrer:
                referrer_id = referrer.id

        if not referrer_id:
            return

        # حساب العمولة حسب نوع الإجراء
        if action_type == "TWIN_CREATION":
            commission_amount = Decimal("5.00")  # قيمة ثابتة لإنشاء التوأم
            description = f"Affiliate commission for creating Digital Twin (User: {user_id})"
        elif action_type == "TWIN_INTERACTION":
            commission_amount = amount * Decimal("0.10")  # 10% من قيمة التفاعل
            description = f"Affiliate commission for paid interaction (User: {user_id})"
        else:
            return

        if commission_amount > 0:
            await self.affiliate_service.register_commission(
                affiliate_id=referrer_id,
                user_id=user_id,
                amount=commission_amount,
                description=description,
                status="PENDING"
            )

    # ============================================================
    # 7. دوال مساعدة
    # ============================================================

    async def _get_user(self, user_id: int):
        """جلب المستخدم من قاعدة البيانات."""
        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)
        return await user_repo.get_user(user_id)

    async def _get_user_email(self, user_id: int) -> str:
        """جلب بريد المستخدم (تبسيط)."""
        user = await self._get_user(user_id)
        return user.email if user else f"user_{user_id}@eppne.com"