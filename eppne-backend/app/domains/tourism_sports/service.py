# app/domains/tourism_sports/service.py (الإصدار النهائي المتكامل)
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import datetime, timedelta
import uuid
import hashlib
import bleach
from typing import Optional, Dict, Any

from app.domains.tourism_sports.repository import TourismSportsRepository
from app.domains.finance.service import FinanceService
from app.domains.ai_agents.service import AIAgentsService
from app.domains.saas.service import SaaSSubscriptionService
from app.domains.affiliate.service import AffiliateService
from app.domains.invoicing.service import InvoicingService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, IdempotencyError
from app.core.idempotency import check_idempotency, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging import logger
from app.domains.tourism_sports.models import (
    TourismProgram, ProgramParticipant, NFTTicket, PlayerTransfer,
    EntertainmentEvent, Tournament, SportsMatch, TransferStatus
)

class TourismSportsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TourismSportsRepository(db)
        self.finance = FinanceService(db)
        self.ai_service = AIAgentsService(db)
        self.saas_service = SaaSSubscriptionService(db)
        self.affiliate_service = AffiliateService(db)
        self.invoicing_service = InvoicingService(db)
        self.event_bus = EventBus(redis_client)
        self.redis = redis_client

    # ========== التحقق من صلاحيات SaaS ==========
    async def _check_saas_limits(self, tenant_id: int, feature: str = "tourism_sports"):
        subscription = await self.saas_service.get_active_subscription(tenant_id)
        if not subscription:
            raise PermissionDeniedError("No active subscription found.")
        features = subscription.features or {}
        if not features.get(feature, False):
            raise PermissionDeniedError("Tourism & Sports feature is not included in your current plan.")
        return subscription, features

    # ========== حجز برنامج سياحي (مع Idempotency + SaaS + Affiliate + Invoicing) ==========
    async def book_program(
        self,
        user_id: int,
        tenant_id: int,
        program_id: int,
        idempotency_key: str = None
    ) -> ProgramParticipant:
        # 1. التحقق من SaaS
        await self._check_saas_limits(tenant_id, "tourism")

        # 2. التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # 3. جلب البرنامج
        program = await self.repo.get_program(program_id)
        if not program or program.status != "ANNOUNCED":
            raise NotFoundError("البرنامج غير متاح")
        if program.tenant_id != tenant_id:
            raise PermissionDeniedError("Program not accessible")

        # 4. التحقق من السعة
        participants_count = await self.repo.count_participants(program_id)
        if participants_count >= program.max_capacity:
            raise InsufficientBalanceError("البرنامج مكتمل العدد")

        # 5. الدفع
        try:
            tx_hash = await self.finance.transfer(
                sender_id=user_id,
                receiver_email="tourism@eppne.com",
                currency="MR_USDT",
                amount=program.base_price_mrusdt,
                notes=f"Booking program {program_id}",
                idempotency_key=idempotency_key
            )
        except InsufficientBalanceError:
            raise PermissionDeniedError("Insufficient balance")

        # 6. إنشاء فاتورة (Invoicing)
        await self.invoicing_service.create_invoice(
            entity_id=tenant_id,
            user_id=user_id,
            amount=program.base_price_mrusdt,
            description=f"Tourism program booking: {program.title}",
            due_date=datetime.utcnow() + timedelta(days=30)
        )

        # 7. تسجيل الإحالة (Affiliate)
        await self._register_affiliate_commission(user_id, tenant_id, "PROGRAM_BOOKED", program.base_price_mrusdt)

        # 8. إنشاء NFT للتذكرة
        nft_id = f"TKT-PROG-{program_id}-{user_id}-{uuid.uuid4().hex[:8].upper()}"
        participant = await self.repo.create_program_participant(
            tenant_id=tenant_id,
            program_id=program_id,
            user_id=user_id,
            ticket_nft_id=nft_id,
            payment_tx_hash=tx_hash,
            idempotency_key=idempotency_key
        )

        # 9. تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="PROGRAM_BOOKED",
            resource_id=participant.id,
            details={"program_id": program_id, "amount": float(program.base_price_mrusdt)}
        )

        # 10. تخزين نتيجة Idempotency
        if idempotency_key:
            await store_idempotency_result(idempotency_key, participant)

        return participant

    # ========== شراء تذكرة فعالية (مع Idempotency + AI + Invoicing) ==========
    async def purchase_event_ticket(
        self,
        user_id: int,
        tenant_id: int,
        event_id: int,
        tier: str,
        require_vip_transport: bool,
        idempotency_key: str = None
    ) -> NFTTicket:
        # 1. التحقق من SaaS
        await self._check_saas_limits(tenant_id, "entertainment")

        # 2. التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # 3. جلب الفعالية
        event = await self.repo.get_event(event_id)
        if not event or event.tenant_id != tenant_id:
            raise NotFoundError("Event not found")

        # 4. حساب السعر
        multiplier = {"GENERAL": 1, "VIP": 2.5, "VVIP_TRANSIT": 5}
        price = event.base_ticket_price_mrusdt * Decimal(multiplier.get(tier, 1))
        if require_vip_transport and tier in ["VIP", "VVIP_TRANSIT"]:
            price += Decimal(50)

        # 5. استدعاء وكيل الذكاء الاصطناعي لتوصية النقل (إن وجد)
        if require_vip_transport:
            try:
                ai_result = await self.ai_service.execute_agent_action(
                    agent_id=5,  # TRANSPORT_OPTIMIZER
                    tenant_id=tenant_id,
                    action_type="ANALYZE_SENSOR",
                    payload={"event_id": event_id, "tier": tier},
                    executor_user_id=user_id
                )
                logger.info(f"AI transport recommendation: {ai_result}")
            except Exception as e:
                logger.warning(f"AI transport optimization failed: {e}")

        # 6. الدفع
        try:
            tx_hash = await self.finance.transfer(
                sender_id=user_id,
                receiver_email="events@eppne.com",
                currency="MR_USDT",
                amount=price,
                notes=f"Ticket for event {event_id}",
                idempotency_key=idempotency_key
            )
        except InsufficientBalanceError:
            raise PermissionDeniedError("Insufficient balance")

        # 7. إنشاء فاتورة (Invoicing)
        await self.invoicing_service.create_invoice(
            entity_id=tenant_id,
            user_id=user_id,
            amount=price,
            description=f"Event ticket: {event.title} ({tier})",
            due_date=datetime.utcnow() + timedelta(days=30)
        )

        # 8. إنشاء التذكرة
        nft_id = f"TKT-{event_id}-{user_id}-{uuid.uuid4().hex[:12].upper()}"
        qr_data = hashlib.sha256(f"{nft_id}-{uuid.uuid4().hex}".encode()).hexdigest()[:16]
        ticket = await self.repo.create_ticket(
            tenant_id=tenant_id,
            event_id=event_id,
            owner_id=user_id,
            tier=tier,
            assigned_vehicle_id=None,
            nft_token_id=nft_id,
            qr_code_data=qr_data,
            purchase_price_mrusdt=price,
            idempotency_key=idempotency_key
        )

        # 9. تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="TICKET_PURCHASED",
            resource_id=ticket.id,
            details={"event_id": event_id, "tier": tier, "amount": float(price)}
        )

        # 10. تخزين نتيجة Idempotency
        if idempotency_key:
            await store_idempotency_result(idempotency_key, ticket)

        return ticket

    # ========== تقديم عرض شراء لاعب (مع Idempotency + AI Medical + Invoicing + Affiliate) ==========
    async def place_transfer_bid(
        self,
        user_id: int,
        tenant_id: int,
        from_club_id: int,
        data: Dict[str, Any],
        idempotency_key: str = None
    ) -> PlayerTransfer:
        # 1. التحقق من SaaS
        await self._check_saas_limits(tenant_id, "sports")

        # 2. التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # 3. جلب اللاعب
        player = await self.repo.get_player_profile(data["player_id"])
        if not player or player.tenant_id != tenant_id:
            raise NotFoundError("Player not found")

        # 4. التحقق من النادي
        from_club = await self.repo.get_sports_org(from_club_id, tenant_id)
        if not from_club or from_club.owner_id != user_id:
            raise PermissionDeniedError("You are not authorized to bid from this club")

        # 5. استدعاء وكيل الذكاء الاصطناعي الطبي (SPORTS_MED_AI)
        medical_flag = False
        medical_report = None
        try:
            ai_result = await self.ai_service.execute_agent_action(
                agent_id=6,  # SPORTS_MED_AI
                tenant_id=tenant_id,
                action_type="ANALYZE_SENSOR",
                payload={
                    "player_id": data["player_id"],
                    "medical_profile_id": player.medical_profile_id,
                    "sport_category": player.sport_category.value
                },
                executor_user_id=user_id
            )
            medical_flag = ai_result.get("result", {}).get("flag", False)
            medical_report = ai_result.get("result", {}).get("summary")
        except Exception as e:
            logger.warning(f"AI medical analysis failed: {e}")

        # 6. التحقق من حوكمة الذكاء الاصطناعي (AI Governance)
        from app.domains.ai_governance.service import AIGovernanceService
        governance = AIGovernanceService(self.db)
        await governance.check_and_consume(
            tenant_id=tenant_id,
            agent_id=6,
            user_id=user_id,
            tokens=200,
            cost=Decimal("0.02")
        )

        # 7. إنشاء عرض الانتقال
        transfer = await self.repo.create_transfer(
            tenant_id=tenant_id,
            from_club_id=from_club_id,
            status=TransferStatus.BID_PLACED,
            medical_ai_flag=medical_flag,
            medical_report_summary=medical_report,
            idempotency_key=idempotency_key,
            **data
        )

        # 8. إنشاء فاتورة (Invoicing) لرسوم الوكالة
        agency_fee = data["bid_amount_mrusdt"] * (data.get("agency_fee_percentage", 10) / 100)
        await self.invoicing_service.create_invoice(
            entity_id=tenant_id,
            user_id=user_id,
            amount=agency_fee,
            description=f"Agency fee for transfer of player {player.user_id}",
            due_date=datetime.utcnow() + timedelta(days=30)
        )

        # 9. تسجيل الإحالة (Affiliate) للوكيل الرياضي
        if data.get("facilitating_agency_id"):
            await self._register_affiliate_commission(user_id, tenant_id, "PLAYER_TRANSFER", agency_fee)

        # 10. تسجيل التدقيق
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="PLAYER_TRANSFER_BID",
            resource_id=transfer.id,
            details={"player_id": data["player_id"], "bid_amount": float(data["bid_amount_mrusdt"])}
        )

        # 11. تخزين نتيجة Idempotency
        if idempotency_key:
            await store_idempotency_result(idempotency_key, transfer)

        return transfer

    # ========== دوال مساعدة ==========
    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, action_type: str, amount: Decimal):
        try:
            from app.domains.identity.repository import UserRepository
            user_repo = UserRepository(self.db)
            user = await user_repo.get_by_id(user_id)
            if user and user.referred_by:
                commission = amount * Decimal("0.05")  # 5%
                await self.affiliate_service.register_commission(
                    affiliate_id=user.referred_by,
                    user_id=user_id,
                    amount=commission,
                    description=f"Affiliate commission for {action_type}",
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")