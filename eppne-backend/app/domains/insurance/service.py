"""
خدمات قطاع التأمينات السيادية
تشمل: إنشاء بوالص، الاشتراك، تقديم المطالبات، تسوية التعويضات، إدارة المعاشات
"""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, cast, List
import uuid
import bleach

from app.domains.insurance.repository import InsuranceRepository
from app.domains.finance.service import FinanceService
from app.domains.ai_agents.service import AIAgentsService
from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
from app.domains.affiliate.service import AffiliateService
from app.domains.invoicing.service import InvoicingService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, ValidationError
from app.core.idempotency import get_idempotency_result, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging_conf import logger
from app.domains.insurance.models import (
    InsurancePolicy, InsuranceSubscription, InsuranceClaim,
    PensionRecord, EmployeeInsuranceProfile, ClaimStatus, PensionStatus
)
from app.domains.identity.models import User


class InsuranceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = InsuranceRepository(db)
        self.finance = FinanceService(db)
        self.ai_service = AIAgentsService(db)
        self.saas_service = SaaSSubscriptionService(db)
        self.affiliate_service = AffiliateService(db)
        self.invoicing_service = InvoicingService(db)
        self.event_bus = EventBus(cast(Any, redis_client))
        self.redis = redis_client

    # ============================================================
    # دوال مساعدة (مع Idempotency الموحّد)
    # ============================================================

    async def _check_saas_limits(self, tenant_id: int, feature: str = "insurance"):
        subscription = await self.saas_service.get_active_subscription(tenant_id)  # type: ignore
        if not subscription:
            raise PermissionDeniedError("No active subscription found.")
        features = subscription.features or {}
        if not features.get(feature, False):
            raise PermissionDeniedError("Insurance feature is not included in your current plan.")
        return subscription, features

    async def _get_entity_email(self, entity_id: int) -> str:
        return f"entity_{entity_id}@eppne.com"

    async def _get_user(self, user_id: int) -> Optional[User]:
        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)
        return await user_repo.get_by_id(user_id)

    async def _get_user_email(self, user_id: int) -> str:
        user = await self._get_user(user_id)
        return user.email if user else f"user_{user_id}@eppne.com"  # type: ignore

    async def _get_payout_date(self, tx_hash: str) -> datetime:
        return datetime.utcnow()

    def _sanitize_json(self, data: dict) -> dict:
        if not data:
            return {}
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = bleach.clean(value, tags=[], strip=True)
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_json(value)
            elif isinstance(value, list):
                sanitized[key] = [self._sanitize_json(item) if isinstance(item, dict) else item for item in value]
            else:
                sanitized[key] = value
        return sanitized

    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, action_type: str, amount: Decimal):
        try:
            user = await self._get_user(user_id)
            if user and user.referred_by:  # type: ignore
                commission = amount * Decimal("0.02")
                await self.affiliate_service.register_commission(  # type: ignore
                    affiliate_id=user.referred_by,  # type: ignore
                    user_id=user_id,
                    amount=commission,
                    description=f"Affiliate commission for {action_type}",
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")

    # ============================================================
    # دوال Idempotency الموحّدة
    # ============================================================

    async def _validate_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """التحقق من وجود نتيجة مخزنة مسبقاً لمفتاح Idempotency."""
        if idempotency_key:
            cached = await get_idempotency_result(idempotency_key)
            if cached is not None:
                return cached
        return None

    async def _store_idempotency(self, idempotency_key: str, result: Dict[str, Any]):
        """تخزين نتيجة العملية بعد النجاح."""
        if idempotency_key:
            await store_idempotency_result(idempotency_key, result)

    # ============================================================
    # 1. بوالص التأمين (Policies)
    # ============================================================

    async def create_policy(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> InsurancePolicy:
        """إنشاء بوليصة تأمين جديدة (للمشرفين فقط)."""
        async with self.db.begin_nested():
            policy = await self.repo.create_policy(
                tenant_id=tenant_id,
                created_by=user_id,
                **data
            )
            await audit_log(
                user_id=user_id,
                tenant_id=tenant_id,  # type: ignore
                action="POLICY_CREATED",
                resource_id=policy.id,  # type: ignore
                details={"name": policy.name, "type": policy.policy_type}  # type: ignore
            )
        await self.db.commit()
        return policy

    async def list_policies(
        self,
        tenant_id: int,
        policy_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[InsurancePolicy]:
        return await self.repo.list_policies(tenant_id, cast(Any, policy_type), is_active, skip, limit)

    async def get_policy(self, policy_id: int, tenant_id: int) -> Optional[InsurancePolicy]:
        policy = await self.repo.get_policy(policy_id)
        if policy and policy.tenant_id != tenant_id:  # type: ignore
            raise PermissionDeniedError("ليس لديك صلاحية الاطلاع على هذه البوليصة")
        return policy

    # ============================================================
    # 2. اشتراكات التأمين (Subscriptions) – مع Idempotency محسّن
    # ============================================================

    async def subscribe(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> InsuranceSubscription:
        """إنشاء اشتراك تأميني مع دعم Idempotency و Atomicity."""
        await self._check_saas_limits(tenant_id, "insurance")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                subscription_id = cached.get("subscription_id")
                if subscription_id:
                    subscription = await self.repo.get_subscription(subscription_id)
                    if subscription:
                        return subscription
                raise ValidationError("Idempotency record exists but subscription not found.")

        policy = await self.repo.get_policy(data["policy_id"])
        if not policy or not cast(Any, policy.is_active) or cast(int, policy.tenant_id) != tenant_id:
            raise NotFoundError("Policy not found or inactive")
        target_fields = ["subscriber_user_id", "fleet_id", "land_asset_id", "project_id",
                         "bio_asset_id", "shipment_id", "employment_contract_id"]
        target = {f: data.get(f) for f in target_fields if data.get(f)}
        if len(target) != 1:
            raise ValueError("Exactly one insured entity must be specified")

        premium = cast(Decimal, policy.base_premium_mrusdt)  # type: ignore
        payment_idempotency = f"insurance_payment_{idempotency_key or uuid.uuid4().hex[:12]}"

        # 🔥 معاملة ذرية للاشتراك والدفع
        async with self.db.begin_nested():
            if premium > 0:
                try:
                    tx_hash = await self.finance.transfer(
                        sender_id=user_id,
                        receiver_email=await self._get_entity_email(policy.issuer_entity_id),  # type: ignore
                        currency="MR_USDT",
                        amount=premium,
                        notes=f"Insurance subscription to {policy.name}",
                        idempotency_key=payment_idempotency
                    )
                except InsufficientBalanceError:
                    raise PermissionDeniedError("Insufficient balance for premium payment")

                await self.invoicing_service.create_invoice(  # type: ignore
                    entity_id=tenant_id,
                    user_id=user_id,
                    amount=premium,
                    description=f"Insurance premium: {policy.name}",
                    due_date=datetime.utcnow() + timedelta(days=30)
                )

                await self._register_affiliate_commission(user_id, tenant_id, "INSURANCE_SUBSCRIPTION", premium)

            sanitized_beneficiaries = self._sanitize_json(data.get("beneficiaries_json", {}))

            subscription = await self.repo.create_subscription(
                tenant_id=tenant_id,
                policy_id=policy.id,
                policy_nft_id=f"INS-{policy.id}-{user_id}-{uuid.uuid4().hex[:8].upper()}",
                subscription_tx_hash=f"SUB-{uuid.uuid4().hex[:12].upper()}",
                beneficiaries_json=sanitized_beneficiaries,
                idempotency_key=cast(str, idempotency_key),
                **{k: v for k, v in data.items() if k not in target_fields + ["policy_id", "beneficiaries_json"]},
                **target
            )

        await self.db.commit()

        await self.event_bus.publish("insurance.subscription.created", {
            "subscription_id": subscription.id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "policy_id": policy.id
        })

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="INSURANCE_SUBSCRIBED",
            resource_id=subscription.id,  # type: ignore
            details={"policy_id": policy.id, "premium": float(premium)}
        )

        # تخزين معرف الاشتراك فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"subscription_id": subscription.id})

        return subscription

    async def get_my_subscriptions(
        self,
        user_id: int,
        tenant_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[InsuranceSubscription]:
        return await self.repo.list_subscriptions(tenant_id, user_id, status, skip, limit)

    async def renew_subscription(self, subscription_id: int, user_id: int) -> InsuranceSubscription:
        """تجديد الاشتراك مع دفع القسط."""
        subscription = await self.repo.get_subscription(subscription_id)
        if not subscription or subscription.subscriber_user_id != user_id:  # type: ignore
            raise NotFoundError("Subscription not found")
        policy = await self.repo.get_policy(subscription.policy_id)  # type: ignore
        if not policy:
            raise NotFoundError("Policy not found")

        payment_idempotency = f"renew_{subscription_id}_{uuid.uuid4().hex[:12]}"
        await self.finance.transfer(
            sender_id=user_id,
            receiver_email=await self._get_entity_email(cast(int, policy.issuer_entity_id)),  # type: ignore
            currency="MR_USDT",
            amount=cast(Decimal, policy.base_premium_mrusdt),
            notes=f"Insurance renewal for {cast(Any, policy).name}",
            idempotency_key=payment_idempotency
        )

        new_end = None
        if subscription.end_date:  # type: ignore
            if policy.premium_cycle == "MONTHLY":  # type: ignore
                new_end = subscription.end_date + timedelta(days=30)  # type: ignore
            elif policy.premium_cycle == "ANNUALLY":  # type: ignore
                new_end = subscription.end_date + timedelta(days=365)  # type: ignore

        return await self.repo.update_subscription(subscription_id, end_date=new_end, status="ACTIVE")

    # ============================================================
    # 3. مطالبات التعويض (Claims) – مع Idempotency محسّن
    # ============================================================

    async def submit_claim(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> InsuranceClaim:
        """تقديم مطالبة تعويض مع Idempotency و AI."""
        await self._check_saas_limits(tenant_id, "insurance")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                claim_id = cached.get("claim_id")
                if claim_id:
                    claim = await self.repo.get_claim(claim_id)
                    if claim:
                        return claim
                raise ValidationError("Idempotency record exists but claim not found.")

        subscription = await self.repo.get_subscription(data["subscription_id"])
        if not subscription or cast(int, subscription.tenant_id) != tenant_id:  # type: ignore
            raise NotFoundError("Subscription not found")
        if cast(int, subscription.subscriber_user_id) != user_id:  # type: ignore
            raise PermissionDeniedError("You can only submit claims for your own subscriptions")
        if cast(Any, subscription.status) != "ACTIVE":  # type: ignore
            raise PermissionDeniedError("Subscription is not active")

        sanitized_description = bleach.clean(data["incident_description"], tags=[], strip=True)

        # استدعاء وكيل الذكاء الاصطناعي
        try:
            from app.domains.ai_governance.service import AIGovernanceService
            governance = AIGovernanceService(self.db)
            await governance.check_and_consume(
                tenant_id=tenant_id,
                agent_id=10,
                user_id=user_id,
                action_type="CLAIM_ANALYSIS",
                tokens=300,
                cost=Decimal("0.03")
            )
            ai_result = await self.ai_service.execute_agent_action(
                agent_id=10,
                tenant_id=tenant_id,
                action_type="ANALYZE_SENSOR",
                payload={
                    "description": sanitized_description,
                    "claimed_amount": float(data["claimed_amount_mrusdt"]),
                    "policy_type": subscription.policy.policy_type if subscription.policy else None
                },
                executor_user_id=user_id,
                idempotency_key=cast(str, idempotency_key)
            )
            logger.info(f"AI claim analysis: {ai_result}")
        except Exception as e:
            logger.warning(f"AI claim analysis failed: {e}")

        # 🔥 معاملة ذرية لإنشاء المطالبة
        async with self.db.begin_nested():
            claim = await self.repo.create_claim(
                tenant_id=tenant_id,
                claimant_user_id=user_id,
                incident_description=sanitized_description,
                idempotency_key=cast(str, idempotency_key),
                **{k: v for k, v in data.items() if k not in ["incident_description", "subscription_id"]}
            )

        await self.db.commit()

        await self.event_bus.publish("insurance.claim.submitted", {
            "claim_id": claim.id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "amount": float(data["claimed_amount_mrusdt"])
        })

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="INSURANCE_CLAIM_SUBMITTED",
            resource_id=claim.id,  # type: ignore
            details={"subscription_id": subscription.id, "amount": float(data["claimed_amount_mrusdt"])}
        )

        # تخزين معرف المطالبة فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"claim_id": claim.id})

        return claim

    async def get_my_claims(
        self,
        user_id: int,
        status: Optional[str] = None
    ) -> List[InsuranceClaim]:
        return await self.repo.list_claims_for_user(user_id, cast(Any, status))

    async def review_claim(
        self,
        claim_id: int,
        reviewer_id: int,
        tenant_id: int,
        approve: bool,
        approved_amount: Optional[Decimal] = None,
        notes: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> InsuranceClaim:
        """مراجعة مطالبة تعويض مع صرف التعويض في حال الموافقة."""
        await self._check_saas_limits(tenant_id, "insurance")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                claim_id_cached = cached.get("claim_id")
                if claim_id_cached:
                    claim = await self.repo.get_claim(claim_id_cached)
                    if claim:
                        return claim
                raise ValidationError("Idempotency record exists but claim not found.")

        claim = await self.repo.get_claim(claim_id)
        if not claim or cast(int, claim.tenant_id) != tenant_id:  # type: ignore
            raise NotFoundError("Claim not found")

        subscription = await self.repo.get_subscription(claim.subscription_id)  # type: ignore
        policy = await self.repo.get_policy(subscription.policy_id)  # type: ignore

        if cast(int, policy.issuer_entity_id) != reviewer_id:  # type: ignore
            raise PermissionDeniedError("Not authorized to review this claim")

        # AI Review
        try:
            ai_result = await self.ai_service.execute_agent_action(
                agent_id=10,
                tenant_id=tenant_id,
                action_type="ANALYZE_SENSOR",
                payload={
                    "claim_id": claim_id,
                    "claimed_amount": float(claim.claimed_amount_mrusdt),  # type: ignore
                    "evidence_urls": claim.evidence_urls  # type: ignore
                },
                executor_user_id=reviewer_id
            )
            logger.info(f"AI claim review: {ai_result}")
        except Exception as e:
            logger.warning(f"AI claim review failed: {e}")

        # 🔥 معاملة ذرية للموافقة والصرف
        async with self.db.begin_nested():
            if approve:
                final_amount = approved_amount or cast(Decimal, claim.claimed_amount_mrusdt)  # type: ignore
                if final_amount > cast(Decimal, policy.max_coverage_limit_mrusdt):  # type: ignore
                    final_amount = cast(Decimal, policy.max_coverage_limit_mrusdt)  # type: ignore

                payment_idempotency = f"claim_payout_{claim_id}_{uuid.uuid4().hex[:12]}"
                payout_tx = await self.finance.transfer(
                    sender_id=reviewer_id,
                    receiver_email=await self._get_user_email(claim.claimant_user_id),  # type: ignore
                    currency="MR_USDT",
                    amount=final_amount,
                    notes=f"Insurance claim payout for {cast(Any, policy).name}",
                    idempotency_key=payment_idempotency
                )

                await self.invoicing_service.create_invoice(  # type: ignore
                    entity_id=tenant_id,
                    user_id=claim.claimant_user_id,  # type: ignore
                    amount=final_amount,
                    description=f"Insurance claim payout: {cast(Any, policy).name}",
                    due_date=datetime.utcnow()
                )

                claim = await self.repo.update_claim(
                    claim_id,
                    status=ClaimStatus.PAID,
                    approved_amount_mrusdt=final_amount,
                    payout_tx_hash=payout_tx,
                    investigation_notes=notes
                )
            else:
                claim = await self.repo.update_claim(
                    claim_id,
                    status=ClaimStatus.REJECTED,
                    investigation_notes=notes
                )

        await self.db.commit()

        await self.event_bus.publish("insurance.claim.resolved", {
            "claim_id": claim.id,
            "tenant_id": tenant_id,
            "status": claim.status.value if hasattr(claim.status, 'value') else str(claim.status),  # type: ignore
            "amount": float(claim.approved_amount_mrusdt)  # type: ignore
        })

        await audit_log(
            user_id=reviewer_id,
            tenant_id=tenant_id,  # type: ignore
            action="INSURANCE_CLAIM_REVIEWED",
            resource_id=claim.id,  # type: ignore
            details={"approved": approve, "amount": float(final_amount) if approve else 0}
        )

        # تخزين معرف المطالبة فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"claim_id": claim.id})

        return claim

    # ============================================================
    # 4. المعاشات (Pensions)
    # ============================================================

    async def create_pension(self, user_id: int, data: Dict[str, Any]) -> PensionRecord:
        """إنشاء سجل معاش (للمشرفين فقط)."""
        async with self.db.begin_nested():
            pension = await self.repo.create_pension(**data)
            await audit_log(
                user_id=user_id,
                tenant_id=data.get("tenant_id", 1),  # type: ignore
                action="PENSION_CREATED",
                resource_id=pension.id,  # type: ignore
                details={"beneficiary": data.get("beneficiary_id"), "amount": float(data.get("monthly_amount_mrusdt", 0))}
            )
        await self.db.commit()
        return pension

    async def get_my_pensions(self, user_id: int) -> List[PensionRecord]:
        return await self.repo.list_pensions_for_beneficiary(user_id)

    async def disburse_monthly_pensions(self) -> int:
        """دفع المعاشات الشهرية (يتم استدعاؤها تلقائياً عبر جدولة)."""
        pensions = await self.repo.list_pensions_for_beneficiary(cast(int, None), status=PensionStatus.ACTIVE)
        count = 0
        for pension in pensions:
            if pension.last_payout_tx:  # type: ignore
                last_payout_date = await self._get_payout_date(pension.last_payout_tx)  # type: ignore
                if last_payout_date and last_payout_date.month == datetime.utcnow().month:
                    continue
            try:
                tx = await self.finance.transfer(
                    sender_id=1,
                    receiver_email=await self._get_user_email(pension.beneficiary_id),  # type: ignore
                    currency="MR_USDT",
                    amount=pension.monthly_amount_mrusdt,  # type: ignore
                    notes=f"Pension payment for {pension.pension_type}"
                )
                await self.repo.update_pension(pension.id, last_payout_tx=tx)  # type: ignore
                count += 1
            except Exception:
                pass
        return count

    # ============================================================
    # 5. ملفات التأمين للموظفين (Employee Insurance)
    # ============================================================

    async def create_employee_insurance_profile(self, user_id: int, data: Dict[str, Any]) -> EmployeeInsuranceProfile:
        """إنشاء ملف تأميني للموظف."""
        async with self.db.begin_nested():
            profile = await self.repo.create_employee_profile(**data)
            await audit_log(
                user_id=user_id,
                tenant_id=data.get("tenant_id", 1),  # type: ignore
                action="EMPLOYEE_INSURANCE_PROFILE_CREATED",
                resource_id=profile.id,  # type: ignore
                details={"employee": data.get("user_id")}
            )
        await self.db.commit()
        return profile

    async def get_employee_profile(self, user_id: int) -> Optional[EmployeeInsuranceProfile]:
        return await self.repo.get_employee_profile(user_id)