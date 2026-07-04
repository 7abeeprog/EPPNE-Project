"""
خدمات قطاع التأمينات السيادية
تشمل: إنشاء بوالص، الاشتراك، تقديم المطالبات، تسوية التعويضات، إدارة المعاشات
"""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any
import uuid
import bleach

from app.domains.insurance.repository import InsuranceRepository
from app.domains.finance.service import FinanceService
from app.domains.ai_agents.service import AIAgentsService
from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
from app.domains.affiliate.service import AffiliateService
from app.domains.invoicing.service import InvoicingService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, IdempotencyError
from app.core.idempotency import check_idempotency, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging_conf import logger
from app.domains.insurance.models import (
    InsurancePolicy, InsuranceSubscription, InsuranceClaim,
    PensionRecord, EmployeeInsuranceProfile, ClaimStatus, PensionStatus
)

class InsuranceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = InsuranceRepository(db)
        self.finance = FinanceService(db)
        self.ai_service = AIAgentsService(db)
        self.saas_service = SaaSSubscriptionService(db)
        self.affiliate_service = AffiliateService(db)
        self.invoicing_service = InvoicingService(db)
        self.event_bus = EventBus(redis_client)
        self.redis = redis_client

    # ========== التحقق من صلاحيات SaaS ==========
    async def _check_saas_limits(self, tenant_id: int, feature: str = "insurance"):
        subscription = await self.saas_service.get_active_subscription(tenant_id)
        if not subscription:
            raise PermissionDeniedError("No active subscription found.")
        features = subscription.features or {}
        if not features.get(feature, False):
            raise PermissionDeniedError("Insurance feature is not included in your current plan.")
        return subscription, features

    # ========== Policies ==========
    async def create_policy(self, user_id: int, tenant_id: int, data: dict) -> InsurancePolicy:
        return await self.repo.create_policy(
            tenant_id=tenant_id,
            created_by=user_id,
            **data
        )

    # ========== Subscriptions (مع Idempotency + SaaS + Invoicing + Affiliate) ==========
    async def subscribe(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: str = None
    ) -> InsuranceSubscription:
        # 1. التحقق من SaaS
        await self._check_saas_limits(tenant_id, "insurance")

        # 2. التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # 3. جلب البوليصة
        policy = await self.repo.get_policy(data["policy_id"])
        if not policy or not policy.is_active or policy.tenant_id != tenant_id:
            raise NotFoundError("Policy not found or inactive")

        # 4. تحديد الكيان المؤمن
        target_fields = ["subscriber_user_id", "fleet_id", "land_asset_id", "project_id", "bio_asset_id", "shipment_id", "employment_contract_id"]
        target = {f: data.get(f) for f in target_fields if data.get(f)}
        if len(target) != 1:
            raise ValueError("Exactly one insured entity must be specified")

        # 5. دفع القسط الأول
        premium = policy.base_premium_mrusdt
        if premium > 0:
            try:
                tx_hash = await self.finance.transfer(
                    sender_id=user_id,
                    receiver_email=await self._get_entity_email(policy.issuer_entity_id),
                    currency="MR_USDT",
                    amount=premium,
                    notes=f"Insurance subscription to {policy.name}",
                    idempotency_key=idempotency_key
                )
            except InsufficientBalanceError:
                raise PermissionDeniedError("Insufficient balance for premium payment")

            # إنشاء فاتورة (Invoicing)
            await self.invoicing_service.create_invoice(
                entity_id=tenant_id,
                user_id=user_id,
                amount=premium,
                description=f"Insurance premium: {policy.name}",
                due_date=datetime.utcnow() + timedelta(days=30)
            )

            # تسجيل الإحالة (Affiliate)
            await self._register_affiliate_commission(user_id, tenant_id, "INSURANCE_SUBSCRIPTION", premium)

        # 6. تعقيم المدخلات
        sanitized_beneficiaries = self._sanitize_json(data.get("beneficiaries_json", {}))

        # 7. إنشاء الاشتراك
        subscription = await self.repo.create_subscription(
            tenant_id=tenant_id,
            policy_id=policy.id,
            policy_nft_id=f"INS-{policy.id}-{user_id}-{uuid.uuid4().hex[:8].upper()}",
            subscription_tx_hash=f"SUB-{uuid.uuid4().hex[:12].upper()}",
            beneficiaries_json=sanitized_beneficiaries,
            idempotency_key=idempotency_key,
            **{k: v for k, v in data.items() if k not in target_fields + ["policy_id", "beneficiaries_json"]},
            **target
        )

        # 8. نشر حدث للأتمتة
        await self.event_bus.publish("insurance.subscription.created", {
            "subscription_id": subscription.id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "policy_id": policy.id
        })

        # 9. تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="INSURANCE_SUBSCRIBED",
            resource_id=subscription.id,
            details={"policy_id": policy.id, "premium": float(premium)}
        )

        # 10. تخزين نتيجة Idempotency
        if idempotency_key:
            await store_idempotency_result(idempotency_key, subscription)

        return subscription

    async def renew_subscription(self, subscription_id: int, user_id: int) -> InsuranceSubscription:
        """تجديد الاشتراك (دفع القسط التالي)"""
        subscription = await self.repo.get_subscription(subscription_id)
        if not subscription or subscription.subscriber_user_id != user_id:
            raise NotFoundError("Subscription not found")
        policy = await self.repo.get_policy(subscription.policy_id)
        if not policy:
            raise NotFoundError("Policy not found")

        # دفع القسط
        await self.finance.transfer(
            sender_id=user_id,
            receiver_email=await self._get_entity_email(policy.issuer_entity_id),
            currency="MR_USDT",
            amount=policy.base_premium_mrusdt,
            notes=f"Insurance renewal for {policy.name}"
        )

        # تمديد تاريخ الانتهاء حسب دورة الدفع
        new_end = None
        if subscription.end_date:
            if policy.premium_cycle == "MONTHLY":
                new_end = subscription.end_date + timedelta(days=30)
            elif policy.premium_cycle == "ANNUALLY":
                new_end = subscription.end_date + timedelta(days=365)
        else:
            new_end = None  # مفتوح

        return await self.repo.update_subscription(subscription_id, end_date=new_end, status="ACTIVE")

    # ========== Claims (مع Idempotency + AI Governance) ==========
    async def submit_claim(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: str = None
    ) -> InsuranceClaim:
        # 1. التحقق من SaaS
        await self._check_saas_limits(tenant_id, "insurance")

        # 2. التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # 3. جلب الاشتراك
        subscription = await self.repo.get_subscription(data["subscription_id"])
        if not subscription or subscription.tenant_id != tenant_id:
            raise NotFoundError("Subscription not found")
        if subscription.subscriber_user_id != user_id:
            raise PermissionDeniedError("You can only submit claims for your own subscriptions")
        if subscription.status != "ACTIVE":
            raise PermissionDeniedError("Subscription is not active")

        # 4. تعقيم المدخلات
        sanitized_description = bleach.clean(data["incident_description"], tags=[], strip=True)

        # 5. استدعاء وكيل الذكاء الاصطناعي (CLAIMS_ADJUSTER_AI)
        from app.domains.ai_governance.service import AIGovernanceService
        governance = AIGovernanceService(self.db)
        await governance.check_and_consume(
            tenant_id=tenant_id,
            agent_id=10,  # CLAIMS_ADJUSTER_AI
            user_id=user_id,
            tokens=300,
            cost=Decimal("0.03")
        )

        try:
            ai_result = await self.ai_service.execute_agent_action(
                agent_id=10,
                tenant_id=tenant_id,
                action_type="ANALYZE_SENSOR",
                payload={
                    "description": sanitized_description,
                    "claimed_amount": float(data["claimed_amount_mrusdt"]),
                    "policy_type": subscription.policy.policy_type if subscription.policy else None
                },
                executor_user_id=user_id
            )
            logger.info(f"AI claim analysis: {ai_result}")
        except Exception as e:
            logger.warning(f"AI claim analysis failed: {e}")

        # 6. إنشاء المطالبة
        claim = await self.repo.create_claim(
            tenant_id=tenant_id,
            claimant_user_id=user_id,
            incident_description=sanitized_description,
            idempotency_key=idempotency_key,
            **{k: v for k, v in data.items() if k not in ["incident_description", "subscription_id"]}
        )

        # 7. نشر حدث للأتمتة
        await self.event_bus.publish("insurance.claim.submitted", {
            "claim_id": claim.id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "amount": float(data["claimed_amount_mrusdt"])
        })

        # 8. تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="INSURANCE_CLAIM_SUBMITTED",
            resource_id=claim.id,
            details={"subscription_id": subscription.id, "amount": float(data["claimed_amount_mrusdt"])}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, claim)

        return claim

    async def review_claim(
        self,
        claim_id: int,
        reviewer_id: int,
        tenant_id: int,
        approve: bool,
        approved_amount: Decimal = None,
        notes: str = None,
        idempotency_key: str = None
    ) -> InsuranceClaim:
        # 1. التحقق من SaaS
        await self._check_saas_limits(tenant_id, "insurance")

        # 2. التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # 3. جلب المطالبة
        claim = await self.repo.get_claim(claim_id)
        if not claim or claim.tenant_id != tenant_id:
            raise NotFoundError("Claim not found")

        subscription = await self.repo.get_subscription(claim.subscription_id)
        policy = await self.repo.get_policy(subscription.policy_id)

        # التحقق من صلاحية المراجع
        if policy.issuer_entity_id != reviewer_id:
            raise PermissionDeniedError("Not authorized to review this claim")

        # 4. استدعاء وكيل الذكاء الاصطناعي لتقييم المطالبة
        try:
            ai_result = await self.ai_service.execute_agent_action(
                agent_id=10,
                tenant_id=tenant_id,
                action_type="ANALYZE_SENSOR",
                payload={
                    "claim_id": claim_id,
                    "claimed_amount": float(claim.claimed_amount_mrusdt),
                    "evidence_urls": claim.evidence_urls
                },
                executor_user_id=reviewer_id
            )
            logger.info(f"AI claim review: {ai_result}")
        except Exception as e:
            logger.warning(f"AI claim review failed: {e}")

        # 5. معالجة القرار
        if approve:
            final_amount = approved_amount or claim.claimed_amount_mrusdt
            if final_amount > policy.max_coverage_limit_mrusdt:
                final_amount = policy.max_coverage_limit_mrusdt

            # صرف التعويض
            try:
                payout_tx = await self.finance.transfer(
                    sender_id=reviewer_id,
                    receiver_email=await self._get_user_email(claim.claimant_user_id),
                    currency="MR_USDT",
                    amount=final_amount,
                    notes=f"Insurance claim payout for {policy.name}",
                    idempotency_key=idempotency_key
                )

                # إنشاء فاتورة (Invoicing)
                await self.invoicing_service.create_invoice(
                    entity_id=tenant_id,
                    user_id=claim.claimant_user_id,
                    amount=final_amount,
                    description=f"Insurance claim payout: {policy.name}",
                    due_date=datetime.utcnow()
                )

                claim = await self.repo.update_claim(
                    claim_id,
                    status=ClaimStatus.PAID,
                    approved_amount_mrusdt=final_amount,
                    payout_tx_hash=payout_tx,
                    investigation_notes=notes
                )
            except Exception as e:
                logger.error(f"Claim payout failed: {e}")
                raise PermissionDeniedError(f"Claim payout failed: {e}")
        else:
            claim = await self.repo.update_claim(
                claim_id,
                status=ClaimStatus.REJECTED,
                investigation_notes=notes
            )

        # 6. نشر حدث للأتمتة
        await self.event_bus.publish("insurance.claim.resolved", {
            "claim_id": claim.id,
            "tenant_id": tenant_id,
            "status": claim.status.value,
            "amount": float(claim.approved_amount_mrusdt)
        })

        # 7. تسجيل التدقيق
        await audit_log(
            user_id=reviewer_id,
            tenant_id=tenant_id,
            action="INSURANCE_CLAIM_REVIEWED",
            resource_id=claim.id,
            details={"approved": approve, "amount": float(final_amount) if approve else 0}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, claim)

        return claim

    # ========== Pensions ==========
    async def create_pension(self, user_id: int, data: dict) -> PensionRecord:
        """إنشاء سجل معاش (لموظف)"""
        return await self.repo.create_pension(**data)

    async def disburse_monthly_pensions(self) -> int:
        """دفع المعاشات الشهرية (يتم استدعاؤها تلقائياً عبر جدولة)"""
        pensions = await self.repo.list_pensions_for_beneficiary(None, status=PensionStatus.ACTIVE)
        count = 0
        for pension in pensions:
            # التحقق من أن الشهر الحالي لم يُدفع بعد
            if pension.last_payout_tx:
                last_payout_date = await self._get_payout_date(pension.last_payout_tx)
                if last_payout_date and last_payout_date.month == datetime.utcnow().month:
                    continue
            try:
                tx = await self.finance.transfer(
                    sender_id=1,  # حساب الخزينة
                    receiver_email=await self._get_user_email(pension.beneficiary_id),
                    currency="MR_USDT",
                    amount=pension.monthly_amount_mrusdt,
                    notes=f"Pension payment for {pension.pension_type}"
                )
                await self.repo.update_pension(pension.id, last_payout_tx=tx)
                count += 1
            except Exception:
                pass
        return count

    # ========== Employee Insurance ==========
    async def create_employee_insurance_profile(self, employer_id: int, data: dict) -> EmployeeInsuranceProfile:
        """إنشاء ملف تأميني للموظف (يتم استقطاعه من الراتب تلقائياً)"""
        return await self.repo.create_employee_profile(**data)

    # ========== دوال مساعدة ==========
    async def _get_entity_email(self, entity_id: int) -> str:
        from app.domains.identity.repository import UserRepository
        return f"entity_{entity_id}@eppne.com"

    async def _get_user_email(self, user_id: int) -> str:
        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)
        user = await user_repo.get_by_id(user_id)
        return user.email if user else f"user_{user_id}@eppne.com"

    async def _get_payout_date(self, tx_hash: str) -> datetime:
        # يمكن استدعاء خدمة البلوكتشين للحصول على تاريخ المعاملة
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
            from app.domains.identity.repository import UserRepository
            user_repo = UserRepository(self.db)
            user = await user_repo.get_by_id(user_id)
            if user and user.referred_by:
                commission = amount * Decimal("0.02")  # 2%
                await self.affiliate_service.register_commission(
                    affiliate_id=user.referred_by,
                    user_id=user_id,
                    amount=commission,
                    description=f"Affiliate commission for {action_type}",
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")