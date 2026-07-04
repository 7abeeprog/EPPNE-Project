# app/domains/arbitration_syndicates/service.py (الإصدار النهائي المتكامل)
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any
import uuid
import hashlib
import bleach

from app.domains.arbitration_syndicates.repository import ArbitrationSyndicatesRepository
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
from app.domains.arbitration_syndicates.models import (
    ArbitrationCase, CrowdJury, DisputeStatus, SovereignSyndicate,
    SyndicateMembership, ProfessionalLicense, SyndicateElection,
    ElectionCandidate, ElectionVote, ElectionStatus
)

class ArbitrationSyndicatesService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ArbitrationSyndicatesRepository(db)
        self.finance = FinanceService(db)
        self.ai_service = AIAgentsService(db)
        self.saas_service = SaaSSubscriptionService(db)
        self.affiliate_service = AffiliateService(db)
        self.invoicing_service = InvoicingService(db)
        self.event_bus = EventBus(redis_client)
        self.redis = redis_client

    # ========== التحقق من صلاحيات SaaS ==========
    async def _check_saas_limits(self, tenant_id: int, feature: str = "arbitration_syndicates"):
        subscription = await self.saas_service.get_active_subscription(tenant_id)
        if not subscription:
            raise PermissionDeniedError("No active subscription found.")
        features = subscription.features or {}
        if not features.get(feature, False):
            raise PermissionDeniedError("Arbitration & Syndicates feature is not included in your current plan.")
        return subscription, features

    # ========== إنشاء قضية تحكيم (مع SaaS + AI Governance + Audit) ==========
    async def create_dispute(
        self,
        claimant_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: str = None
    ) -> ArbitrationCase:
        # 1. التحقق من SaaS
        await self._check_saas_limits(tenant_id, "arbitration")

        # 2. التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # 3. تعقيم المدخلات
        sanitized_reason = bleach.clean(data["dispute_reason"], tags=[], strip=True)

        # 4. استدعاء وكيل الذكاء الاصطناعي (AI_JUDGE) مع حوكمة الاستهلاك
        judging_mode = data.get("judging_mode", "AI_HYBRID")
        ai_judge_id = None
        if judging_mode in ["AI_ONLY", "AI_HYBRID"]:
            from app.domains.ai_governance.service import AIGovernanceService
            governance = AIGovernanceService(self.db)
            await governance.check_and_consume(
                tenant_id=tenant_id,
                agent_id=11,  # AI_JUDGE
                user_id=claimant_id,
                tokens=500,
                cost=Decimal("0.05")
            )

            try:
                ai_result = await self.ai_service.execute_agent_action(
                    agent_id=11,
                    tenant_id=tenant_id,
                    action_type="ANALYZE_SENSOR",
                    payload={
                        "dispute_reason": sanitized_reason,
                        "evidence_hashes": data.get("evidence_hashes", []),
                        "judging_mode": judging_mode
                    },
                    executor_user_id=claimant_id
                )
                ai_judge_id = ai_result.get("agent_id", 11)
                logger.info(f"AI Judge analysis: {ai_result}")
            except Exception as e:
                logger.warning(f"AI Judge analysis failed: {e}")

        # 5. إنشاء القضية
        case = await self.repo.create_case(
            tenant_id=tenant_id,
            claimant_id=claimant_id,
            dispute_reason=sanitized_reason,
            judging_mode=judging_mode,
            ai_judge_id=ai_judge_id,
            idempotency_key=idempotency_key,
            **{k: v for k, v in data.items() if k not in ["dispute_reason", "judging_mode"]}
        )

        # 6. تسجيل الإحالة (Affiliate)
        await self._register_affiliate_commission(claimant_id, tenant_id, "ARBITRATION_CASE_CREATED")

        # 7. إنشاء فاتورة (Invoicing) لرسوم التحكيم
        await self.invoicing_service.create_invoice(
            entity_id=tenant_id,
            user_id=claimant_id,
            amount=Decimal("25.00"),  # رسوم ثابتة للتحكيم
            description=f"Arbitration case #{case.id}",
            due_date=datetime.utcnow() + timedelta(days=30)
        )

        # 8. نشر حدث للأتمتة
        await self.event_bus.publish("arbitration.case.created", {
            "case_id": case.id,
            "tenant_id": tenant_id,
            "claimant_id": claimant_id,
            "judging_mode": judging_mode
        })

        # 9. تسجيل التدقيق
        await audit_log(
            user_id=claimant_id,
            tenant_id=tenant_id,
            action="ARBITRATION_CASE_CREATED",
            resource_id=case.id,
            details={"dispute_reason": sanitized_reason[:50]}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, case)

        return case

    # ========== تصويت المحلفين (مع Idempotency + Audit) ==========
    async def cast_jury_vote(
        self,
        juror_id: int,
        tenant_id: int,
        case_id: int,
        vote: bool,
        justification: str = None,
        idempotency_key: str = None
    ) -> CrowdJury:
        # 1. التحقق من SaaS
        await self._check_saas_limits(tenant_id, "arbitration")

        # 2. التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # 3. جلب القضية
        case = await self.repo.get_case(case_id)
        if not case or case.tenant_id != tenant_id:
            raise NotFoundError("Case not found")
        if case.status != DisputeStatus.IN_REVIEW:
            raise PermissionDeniedError("Case is not in review phase")

        # 4. التحقق من عدم التكرار
        existing = await self.repo.get_jury_votes_for_case(case_id)
        if any(v.juror_id == juror_id for v in existing):
            raise PermissionDeniedError("You have already voted on this case")

        # 5. تعقيم المدخلات
        sanitized_justification = bleach.clean(justification, tags=[], strip=True) if justification else None

        # 6. إنشاء التصويت
        vote_record = await self.repo.create_jury_vote(
            tenant_id=tenant_id,
            case_id=case_id,
            juror_id=juror_id,
            vote=vote,
            justification=sanitized_justification,
            reward_mr7=Decimal(10),
            idempotency_key=idempotency_key
        )

        # 7. تحديث حالة القضية إذا اكتمل عدد المحلفين (افتراضي 3)
        votes = await self.repo.get_jury_votes_for_case(case_id)
        if len(votes) >= 3:
            await self.repo.update_case_status(case_id, DisputeStatus.RESOLVED)

        # 8. تسجيل التدقيق
        await audit_log(
            user_id=juror_id,
            tenant_id=tenant_id,
            action="JURY_VOTE_CAST",
            resource_id=vote_record.id,
            details={"case_id": case_id, "vote": vote}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, vote_record)

        return vote_record

    # ========== الانضمام إلى نقابة (مع Idempotency + SaaS + Affiliate + Invoicing) ==========
    async def join_syndicate(
        self,
        user_id: int,
        tenant_id: int,
        syndicate_id: int,
        idempotency_key: str = None
    ) -> SyndicateMembership:
        # 1. التحقق من SaaS
        await self._check_saas_limits(tenant_id, "syndicates")

        # 2. التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # 3. جلب النقابة
        syndicate = await self.repo.get_syndicate(syndicate_id)
        if not syndicate or not syndicate.is_active or syndicate.tenant_id != tenant_id:
            raise NotFoundError("Syndicate not found or inactive")

        # 4. التحقق من العضوية الحالية
        existing = await self.repo.get_membership(user_id, syndicate_id)
        if existing:
            raise PermissionDeniedError("You are already a member of this syndicate")

        # 5. دفع الرسوم السنوية
        fee = syndicate.annual_fee_mrusdt
        if fee > 0:
            try:
                tx_hash = await self.finance.transfer(
                    sender_id=user_id,
                    receiver_email=await self._get_treasury_email(syndicate_id),
                    currency="MR_USDT",
                    amount=fee,
                    notes=f"Syndicate membership fee for {syndicate.name}",
                    idempotency_key=idempotency_key
                )
            except InsufficientBalanceError:
                raise PermissionDeniedError("Insufficient balance for membership fee")

            # إنشاء فاتورة (Invoicing)
            await self.invoicing_service.create_invoice(
                entity_id=tenant_id,
                user_id=user_id,
                amount=fee,
                description=f"Syndicate membership fee: {syndicate.name}",
                due_date=datetime.utcnow() + timedelta(days=30)
            )

            # تسجيل الإحالة (Affiliate)
            await self._register_affiliate_commission(user_id, tenant_id, "SYNDICATE_JOINED")

        # 6. إنشاء العضوية
        membership_number = f"SYN-{syndicate_id}-{user_id}-{uuid.uuid4().hex[:6].upper()}"
        sbt_id = f"SBT-MEM-{uuid.uuid4().hex[:12].upper()}"
        membership = await self.repo.create_membership(
            tenant_id=tenant_id,
            syndicate_id=syndicate_id,
            member_user_id=user_id,
            membership_number=membership_number,
            join_date=datetime.utcnow(),
            expiry_date=datetime.utcnow() + timedelta(days=365),
            membership_sbt_id=sbt_id,
            minting_tx_hash=f"0x{sbt_id.lower()}",
            idempotency_key=idempotency_key
        )

        # 7. نشر حدث للأتمتة
        await self.event_bus.publish("syndicate.membership.created", {
            "membership_id": membership.id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "syndicate_id": syndicate_id
        })

        # 8. تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="SYNDICATE_JOINED",
            resource_id=membership.id,
            details={"syndicate_id": syndicate_id, "fee": float(fee)}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, membership)

        return membership

    # ========== إصدار رخصة مهنية (مع Idempotency + Invoicing) ==========
    async def issue_license(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: str = None
    ) -> ProfessionalLicense:
        # 1. التحقق من SaaS
        await self._check_saas_limits(tenant_id, "syndicates")

        # 2. التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # 3. التحقق من العضوية
        membership = await self.repo.get_membership(user_id, data["syndicate_id"])
        if not membership or membership.tenant_id != tenant_id:
            raise PermissionDeniedError("You must be a member of the syndicate first")

        # 4. تعقيم المدخلات
        sanitized_name = bleach.clean(data["license_name"], tags=[], strip=True)

        # 5. إنشاء الرخصة
        license_number = f"LIC-{data['syndicate_id']}-{user_id}-{uuid.uuid4().hex[:8].upper()}"
        license = await self.repo.create_license(
            tenant_id=tenant_id,
            user_id=user_id,
            license_number=license_number,
            issue_date=datetime.utcnow(),
            expiry_date=datetime.utcnow() + timedelta(days=1095),
            license_sbt_id=f"SBT-LIC-{uuid.uuid4().hex[:12].upper()}",
            license_name=sanitized_name,
            idempotency_key=idempotency_key,
            **{k: v for k, v in data.items() if k not in ["license_name", "syndicate_id"]}
        )

        # 6. إنشاء فاتورة (Invoicing) لرسوم الترخيص
        await self.invoicing_service.create_invoice(
            entity_id=tenant_id,
            user_id=user_id,
            amount=Decimal("10.00"),
            description=f"Professional license: {sanitized_name}",
            due_date=datetime.utcnow() + timedelta(days=30)
        )

        # 7. تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="PROFESSIONAL_LICENSE_ISSUED",
            resource_id=license.id,
            details={"license_name": sanitized_name}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, license)

        return license

    # ========== التصويت في الانتخابات (مع Idempotency + Audit) ==========
    async def cast_election_vote(
        self,
        voter_id: int,
        tenant_id: int,
        election_id: int,
        candidate_id: int,
        idempotency_key: str = None
    ) -> ElectionVote:
        # 1. التحقق من SaaS
        await self._check_saas_limits(tenant_id, "syndicates")

        # 2. التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # 3. جلب الانتخابات
        election = await self.repo.get_election(election_id)
        if not election or election.tenant_id != tenant_id:
            raise NotFoundError("Election not found")
        if election.status != ElectionStatus.VOTING:
            raise PermissionDeniedError("Election is not in voting phase")
        now = datetime.utcnow()
        if now < election.voting_start or now > election.voting_end:
            raise PermissionDeniedError("Voting period has ended")

        # 4. التحقق من العضوية في النقابة
        membership = await self.repo.get_membership(voter_id, election.syndicate_id)
        if not membership or membership.tenant_id != tenant_id:
            raise PermissionDeniedError("You must be a member of the syndicate to vote")
        if membership.status != "ACTIVE":
            raise PermissionDeniedError("Your membership is not active")

        # 5. التحقق من عدم التصويت المسبق
        if await self.repo.has_voted(election_id, voter_id):
            raise PermissionDeniedError("You have already voted in this election")

        # 6. إنشاء التصويت
        vote_hash = hashlib.sha256(f"{election_id}-{voter_id}-{candidate_id}-{uuid.uuid4().hex}".encode()).hexdigest()
        vote = await self.repo.create_vote(
            tenant_id=tenant_id,
            election_id=election_id,
            voter_user_id=voter_id,
            candidate_id=candidate_id,
            vote_hash=vote_hash,
            blockchain_tx_hash=f"0x{vote_hash[:40]}",
            idempotency_key=idempotency_key
        )

        # 7. تسجيل التدقيق
        await audit_log(
            user_id=voter_id,
            tenant_id=tenant_id,
            action="ELECTION_VOTE_CAST",
            resource_id=vote.id,
            details={"election_id": election_id, "candidate_id": candidate_id}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, vote)

        return vote

    # ========== إصدار حكم (مع EventBus + Audit) ==========
    async def issue_verdict(
        self,
        case_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        user_id: int,
        idempotency_key: str = None
    ) -> ArbitrationCase:
        # 1. التحقق من SaaS
        await self._check_saas_limits(tenant_id, "arbitration")

        # 2. التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # 3. جلب القضية
        case = await self.repo.get_case(case_id)
        if not case or case.tenant_id != tenant_id:
            raise NotFoundError("Case not found")

        # 4. تعقيم المدخلات
        sanitized_verdict = bleach.clean(data["final_verdict"], tags=[], strip=True)

        # 5. تحديث القضية
        case = await self.repo.update_case_status(
            case_id,
            DisputeStatus.RESOLVED,
            sanitized_verdict,
            data.get("enforcement_tx_hash")
        )

        # 6. نشر حدث للأتمتة
        await self.event_bus.publish("arbitration.verdict.issued", {
            "case_id": case.id,
            "tenant_id": tenant_id,
            "verdict": sanitized_verdict
        })

        # 7. تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="ARBITRATION_VERDICT_ISSUED",
            resource_id=case.id,
            details={"verdict": sanitized_verdict[:50]}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, case)

        return case

    # ========== دوال مساعدة ==========
    async def _get_treasury_email(self, syndicate_id: int) -> str:
        return f"treasury_{syndicate_id}@syndicates.eppne.com"

    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, action_type: str):
        try:
            from app.domains.identity.repository import UserRepository
            user_repo = UserRepository(self.db)
            user = await user_repo.get_by_id(user_id)
            if user and user.referred_by:
                commission = Decimal("5.00") if action_type == "ARBITRATION_CASE_CREATED" else Decimal("2.00")
                await self.affiliate_service.register_commission(
                    affiliate_id=user.referred_by,
                    user_id=user_id,
                    amount=commission,
                    description=f"Affiliate commission for {action_type}",
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")