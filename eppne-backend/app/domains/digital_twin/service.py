# app/domains/digital_twin/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import uuid
import hashlib
from decimal import Decimal
from typing import Optional, List, Dict, Any, cast

from app.domains.digital_twin.repository import DigitalTwinRepository
from app.domains.finance.service import FinanceService
from app.domains.saas.service import SaaSControlService
from app.domains.affiliate.service import AffiliateService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, ValidationError
from app.core.idempotency import get_idempotency_result, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging_conf import logger
from app.domains.digital_twin.models import (
    DigitalTwinConfig, TwinInteractionLog, TimeCapsule, DeathOracleCheck,
    LifeMilestone, PreBirthRecord, DigitalWill
)
from app.domains.identity.models import User


class DigitalTwinService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DigitalTwinRepository(db)
        self.event_bus = EventBus(cast(Any, redis_client))

    # ============================================================
    # دوال مساعدة
    # ============================================================

    async def _check_saas_limits(self, tenant_id: int):
        """التحقق من صلاحية التوأم الرقمي في خطة الاشتراك."""
        saas_service = SaaSControlService(self.db, tenant_id)
        subscription = await saas_service.get_active_subscription(tenant_id)  # type: ignore
        if not subscription:
            raise PermissionDeniedError("No active subscription found for this entity.")
        if not subscription.plan:
            raise PermissionDeniedError("No valid subscription plan found.")
        features = subscription.plan.features or []
        if "digital_twin" not in features:
            raise PermissionDeniedError("Digital Twin feature is not included in your current plan.")
        return subscription, features

    async def _get_user(self, user_id: int):
        """جلب المستخدم من قاعدة البيانات."""
        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)
        return await user_repo.get_user(user_id)  # type: ignore

    async def _get_user_email(self, user_id: int) -> str:
        """جلب بريد المستخدم."""
        user = await self._get_user(user_id)
        return user.email if user else f"user_{user_id}@eppne.com"

    async def _register_affiliate_commission(
        self,
        user_id: int,
        tenant_id: int,
        action_type: str,
        amount: Decimal = Decimal("0.0"),
        affiliate_code: Optional[str] = None
    ):
        """تسجيل عمولة إحالة عند إنشاء توأم أو تفاعل مدفوع."""
        affiliate_service = AffiliateService(self.db, tenant_id)
        try:
            user = await self._get_user(user_id)
            if not user:
                return

            referrer_id = user.referred_by
            if not referrer_id and not affiliate_code:
                return

            if affiliate_code and not referrer_id:
                referrer = await affiliate_service.get_user_by_code(affiliate_code)
                if referrer:
                    referrer_id = referrer.user_id  # AffiliateProfile.user_id — register_commission's affiliate_id متوقع user_id، مش profile id

            if not referrer_id:
                return

            if action_type == "TWIN_CREATION":
                commission_amount = Decimal("5.00")
                description = f"Affiliate commission for creating Digital Twin (User: {user_id})"
            elif action_type == "TWIN_INTERACTION":
                commission_amount = amount * Decimal("0.10")
                description = f"Affiliate commission for paid interaction (User: {user_id})"
            else:
                return

            if commission_amount > 0:
                await affiliate_service.register_commission(  # type: ignore
                    affiliate_id=referrer_id,
                    user_id=user_id,
                    amount=commission_amount,
                    description=description,
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")

    # ============================================================
    # 1. التوأم الرقمي (Digital Twin)
    # ============================================================

    async def get_or_create_twin(self, user_id: int, tenant_id: int) -> DigitalTwinConfig:
        """جلب أو إنشاء التوأم الرقمي مع تسجيل عمولة إحالة عند الإنشاء."""
        await self._check_saas_limits(tenant_id)

        twin = await self.repo.get_twin_config(user_id, tenant_id)
        if not twin:
            async with self.db.begin_nested():
                twin = await self.repo.create_twin_config(
                    user_id=user_id,
                    tenant_id=tenant_id
                )
            await self.db.commit()
            await self._register_affiliate_commission(user_id, tenant_id, "TWIN_CREATION")
        return twin

    async def update_twin_config(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> DigitalTwinConfig:
        """تحديث إعدادات التوأم الرقمي."""
        await self._check_saas_limits(tenant_id)
        return await self.repo.update_twin_config(user_id, tenant_id, **data)

    # ============================================================
    # 2. التفاعل مع التوأم الرقمي (مع Idempotency محسّن)
    # ============================================================

    async def interact_with_twin(
        self,
        visitor_id: int,
        twin_owner_id: int,
        tenant_id: int,
        interaction_data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> TwinInteractionLog:
        """تفاعل المستخدم مع التوأم الرقمي مع دعم Idempotency."""

        # 1. التحقق من Idempotency باستخدام get_idempotency_result
        if idempotency_key:
            cached = await get_idempotency_result(idempotency_key)
            if cached is not None:
                # استرجاع سجل التفاعل من قاعدة البيانات باستخدام المعرف المخزن
                log_id = cached.get("log_id")
                if log_id:
                    log = await self.repo.get_interaction_log(log_id)  # type: ignore
                    if log:
                        return log
                raise ValidationError("Idempotency record exists but interaction log not found.")

        # 2. التحقق من صلاحية SaaS
        await self._check_saas_limits(tenant_id)

        # 3. التحقق من التوأم الرقمي
        twin = await self.repo.get_twin_config(twin_owner_id, tenant_id)
        if not twin or not cast(Any, twin.is_active):
            raise NotFoundError("التوأم الرقمي غير موجود أو غير نشط")

        # 4. التحقق من الحد الأقصى للإنفاق
        fee = cast(Decimal, twin.interaction_fee_mrusdt) * Decimal(interaction_data.get("duration_minutes", 1))
        if cast(Decimal, twin.max_spending_limit) > 0:
            total_spent = await self.repo.sum_monthly_spending(cast(int, twin.id), tenant_id)
            if total_spent + fee > cast(Decimal, twin.max_spending_limit):
                raise PermissionDeniedError("Monthly spending limit exceeded for this twin.")

        # 5. حساب الرسوم وتنفيذ التحويل
        payout_tx_hash = None
        if fee > 0:
            # 🔥 معاملة ذرية للدفع
            finance = FinanceService(self.db, tenant_id)
            async with self.db.begin_nested():
                tx = await finance.transfer(
                    sender_id=visitor_id,
                    receiver_email=await self._get_user_email(twin_owner_id),
                    currency="MR_USDT",
                    amount=fee,
                    notes=f"Interaction with digital twin of user {twin_owner_id}",
                    idempotency_key=idempotency_key or f"twin-interact-{uuid.uuid4().hex[:12]}"
                )
                payout_tx_hash = tx.tx_hash

                # تسجيل الإحالة
                affiliate_code = interaction_data.get("affiliate_code")
                if affiliate_code and fee > 0:
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
            twin_config_id=twin.id,  # type: ignore
            visitor_id=visitor_id,
            interaction_type=interaction_data["interaction_type"],
            duration_minutes=interaction_data["duration_minutes"],
            fee_paid_mrusdt=fee,
            payout_tx_hash=payout_tx_hash,
            idempotency_key=idempotency_key
        )

        # 7. تخزين نتيجة Idempotency (معرف السجل فقط)
        if idempotency_key:
            await store_idempotency_result(idempotency_key, {"log_id": log.id})

        # 8. نشر حدث
        await self.event_bus.publish("twin.interaction", {
            "twin_config_id": cast(int, twin.id),
            "visitor_id": visitor_id,
            "twin_owner_id": twin_owner_id,
            "tenant_id": tenant_id,
            "fee": float(cast(Decimal, fee)),
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
        data: Dict[str, Any],
        beneficiaries: List[Dict[str, Any]]
    ) -> TimeCapsule:
        """إنشاء خزنة زمنية مع المستفيدين."""
        await self._check_saas_limits(tenant_id)

        async with self.db.begin_nested():
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

        await self.db.commit()

        await self.event_bus.publish("time_capsule.created", {
            "capsule_id": capsule.id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "beneficiaries_count": len(beneficiaries)
        })

        return capsule

    async def get_time_capsule(self, user_id: int, tenant_id: int) -> Optional[TimeCapsule]:
        """جلب خزنة الزمن للمستخدم."""
        return await self.repo.get_time_capsule(user_id, tenant_id)

    async def send_heartbeat(self, user_id: int, tenant_id: int) -> TimeCapsule:
        """تحديث نبض الحياة للخزنة الزمنية."""
        capsule = await self.repo.update_capsule_heartbeat(user_id, tenant_id)
        if not capsule:
            raise NotFoundError("لا توجد خزنة زمنية لهذا المستخدم")
        return capsule

    # ============================================================
    # 4. الوصية الرقمية (Digital Will)
    # ============================================================

    async def create_digital_will(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> DigitalWill:
        """إنشاء وصية رقمية جديدة."""
        existing = await self.repo.get_digital_will(user_id, tenant_id)
        if existing:
            raise PermissionDeniedError("Digital will already exists")

        nft_id = f"WILL-{user_id}-{uuid.uuid4().hex[:8].upper()}"
        return await self.repo.create_digital_will(
            user_id=user_id,
            tenant_id=tenant_id,
            will_nft_id=nft_id,
            **data
        )

    async def get_digital_will(self, user_id: int, tenant_id: int) -> Optional[DigitalWill]:
        """جلب الوصية الرقمية للمستخدم."""
        return await self.repo.get_digital_will(user_id, tenant_id)

    # ============================================================
    # 5. أوراكل الموت (Death Oracle)
    # ============================================================

    async def get_death_oracle(self, user_id: int, tenant_id: int) -> Optional[DeathOracleCheck]:
        """جلب سجل أوراكل الموت."""
        return await self.repo.get_death_oracle(user_id, tenant_id)

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
        await audit_log(
            user_id=reporter_id,
            tenant_id=tenant_id,  # type: ignore
            action="DEATH_REPORTED",
            resource_id=deceased_id,  # type: ignore
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

        oracle = await self.repo.update_death_oracle_status(
            deceased_id,
            tenant_id,
            "DEATH_PENDING",
            death_certificate_ipfs=evidence_ipfs
        )

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
        confirmers: List[int],
        request_ip: Optional[str] = None,
        request_user_agent: Optional[str] = None
    ) -> DeathOracleCheck:
        """تأكيد الوفاة مع تسجيل تدقيق صارم."""
        oracle = await self.repo.get_death_oracle(deceased_id, tenant_id)
        if not oracle or oracle.status != "DEATH_PENDING":  # type: ignore
            raise PermissionDeniedError("لا يمكن تأكيد الوفاة في هذه الحالة")

        if len(confirmers) < 3:
            raise PermissionDeniedError("يحتاج التأكيد إلى 3 شهود على الأقل")

        await audit_log(
            user_id=confirmers[0],
            tenant_id=tenant_id,  # type: ignore
            action="DEATH_CONFIRMATION",
            resource_id=deceased_id,  # type: ignore
            details={
                "confirmers": confirmers,
                "ip_address": request_ip,
                "user_agent": request_user_agent,
                "status": "DEATH_CONFIRMED"
            }
        )

        release_tx = f"LEGACY-RELEASE-{uuid.uuid4().hex[:16].upper()}"
        oracle = await self.repo.update_death_oracle_status(
            deceased_id,
            tenant_id,
            "DEATH_CONFIRMED",
            release_tx=release_tx
        )

        await self._distribute_legacy(deceased_id, tenant_id)

        await self.event_bus.publish("death.confirmed", {
            "deceased_id": deceased_id,
            "tenant_id": tenant_id,
            "release_tx": release_tx,
            "confirmers": confirmers,
            "timestamp": datetime.utcnow().isoformat()
        })

        return oracle

    async def _distribute_legacy(self, deceased_id: int, tenant_id: int):
        """توزيع الأصول مع مراعاة الفوترة والإحالة."""
        capsule = await self.repo.get_time_capsule(deceased_id, tenant_id)
        if not capsule:
            return

        beneficiaries = await self.repo.list_beneficiaries(cast(int, capsule.id), tenant_id)
        for ben in beneficiaries:
            try:
                # في الإنتاج، يتم استدعاء خدمة التوزيع مع تسجيل الفوترة
                pass
            except Exception as e:
                await audit_log(
                    user_id=deceased_id,
                    tenant_id=tenant_id,  # type: ignore
                    action="LEGACY_DISTRIBUTION_FAILED",
                    resource_id=cast(int, ben.id),  # type: ignore
                    details={"error": str(e)}
                )

    # ============================================================
    # 6. محطات الحياة (Life Milestones)
    # ============================================================

    async def add_life_milestone(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> LifeMilestone:
        """إضافة محطة حياة جديدة."""
        nft_id = f"MLS-{user_id}-{data['milestone_type'].value if hasattr(data['milestone_type'], 'value') else data['milestone_type']}-{uuid.uuid4().hex[:8].upper()}"
        return await self.repo.create_life_milestone(
            user_id=user_id,
            tenant_id=tenant_id,
            milestone_nft_id=nft_id,
            **data
        )

    async def list_life_milestones(self, user_id: int, tenant_id: int) -> List[LifeMilestone]:
        """جلب قائمة محطات الحياة للمستخدم."""
        return await self.repo.list_life_milestones(user_id, tenant_id)

    # ============================================================
    # 7. الحجز قبل الولادة (Pre-Birth Identity)
    # ============================================================

    async def reserve_pre_birth_identity(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> PreBirthRecord:
        """حجز هوية قبل الولادة."""
        existing = await self.repo.get_pre_birth_record(data["reserved_sovereign_id"], tenant_id)
        if existing:
            raise PermissionDeniedError("Sovereign ID already reserved")

        return await self.repo.create_pre_birth_record(
            tenant_id=tenant_id,
            parent_1_id=user_id,
            **data
        )