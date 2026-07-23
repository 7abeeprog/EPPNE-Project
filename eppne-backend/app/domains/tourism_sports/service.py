# pyright: reportGeneralTypeIssues=false
# pyright: reportCallIssue=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportArgumentType=false

# app/domains/tourism_sports/service.py (الإصدار النهائي المتكامل المصحح)
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import datetime, timedelta
import uuid
import hashlib
import bleach
from typing import Optional, Dict, Any, cast, List

from app.domains.tourism_sports.repository import TourismSportsRepository
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
from app.domains.tourism_sports.models import (
    TourismProgram, ProgramParticipant, NFTTicket, PlayerTransfer,
    EntertainmentEvent, Tournament, SportsMatch, TransferStatus,
    TourismDestination, SportsOrganization, PlayerProfile
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
        self.event_bus = EventBus(cast(Any, redis_client))
        self.redis = redis_client

    # ============================================================
    # 0. دوال Idempotency الموحّدة
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

    # ========== التحقق من صلاحيات SaaS ==========
    async def _check_saas_limits(self, tenant_id: int, feature: str = "tourism_sports"):
        has_access = await self.saas_service.can_access_service(tenant_id, feature)
        if not has_access:
            raise PermissionDeniedError("Tourism & Sports feature is not included in your current plan.")
        return None, {}

    # ============================================================
    # 1. السياحة (Tourism)
    # ============================================================
    async def create_destination(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> TourismDestination:
        """إنشاء وجهة سياحية جديدة (للمشرفين)."""
        await self._check_saas_limits(tenant_id, "tourism")
        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)
        sanitized_desc = bleach.clean(data.get("description", ""), tags=[], strip=True) if data.get("description") else None
        return await self.repo.create_destination(
            tenant_id=tenant_id,
            name=sanitized_name,
            destination_type=data["destination_type"],
            planet_body=data.get("planet_body", "EARTH"),
            gps_location=data.get("gps_location"),
            description=sanitized_desc
        )

    async def list_destinations(
        self,
        tenant_id: int,
        destination_type: Optional[str] = None
    ) -> List[TourismDestination]:
        """قائمة الوجهات السياحية."""
        await self._check_saas_limits(tenant_id, "tourism")
        result = await self.repo.list_destinations(tenant_id, destination_type)
        return list(result)

    async def create_program(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> TourismProgram:
        """إنشاء برنامج سياحي جديد (للمشرفين)."""
        await self._check_saas_limits(tenant_id, "tourism")
        sanitized_title = bleach.clean(data.get("title", ""), tags=[], strip=True)
        sanitized_desc = bleach.clean(data.get("description", ""), tags=[], strip=True) if data.get("description") else None
        return await self.repo.create_program(
            tenant_id=tenant_id,
            title=sanitized_title,
            description=sanitized_desc,
            program_tier=data["program_tier"],
            required_certificate_id=data.get("required_certificate_id"),
            base_price_mrusdt=data["base_price_mrusdt"],
            max_capacity=data["max_capacity"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            status="ANNOUNCED"
        )

    # ============================================================
    # 2. حجز برنامج سياحي (مع Idempotency محسّن)
    # ============================================================

    async def book_program(
        self,
        user_id: int,
        tenant_id: int,
        program_id: int,
        idempotency_key: Optional[str] = None
    ) -> ProgramParticipant:
        """حجز برنامج سياحي مع Idempotency ومعاملة ذرية."""
        await self._check_saas_limits(tenant_id, "tourism")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                participant_id = cached.get("participant_id")
                if participant_id:
                    participant = await self.repo.get_program_participant(participant_id)
                    if participant:
                        return participant
                raise ValidationError("Idempotency record exists but participant not found.")

        program = await self.repo.get_program(program_id)
        if not program or program.status != "ANNOUNCED":  # type: ignore
            raise NotFoundError("البرنامج غير متاح")
        if program.tenant_id != tenant_id:  # type: ignore
            raise PermissionDeniedError("Program not accessible")

        participants_count = await self.repo.count_participants(program_id)
        if participants_count >= program.max_capacity:  # type: ignore
            raise InsufficientBalanceError("البرنامج مكتمل العدد")

        async with self.db.begin_nested():
            try:
                tx_hash = await self.finance.transfer(
                    sender_id=user_id,
                    receiver_email="tourism@eppne.com",
                    currency="MR_USDT",
                    amount=program.base_price_mrusdt,  # type: ignore
                    notes=f"Booking program {program_id}",
                    idempotency_key=idempotency_key or ""
                )
            except InsufficientBalanceError:
                raise PermissionDeniedError("Insufficient balance")

            await self.invoicing_service.create_invoice(  # type: ignore[attr-defined]
                entity_id=tenant_id,
                user_id=user_id,
                amount=program.base_price_mrusdt,  # type: ignore
                description=f"Tourism program booking: {program.title}",
                due_date=datetime.utcnow() + timedelta(days=30)
            )

            await self._register_affiliate_commission(user_id, tenant_id, "PROGRAM_BOOKED", program.base_price_mrusdt)  # type: ignore

            nft_id = f"TKT-PROG-{program_id}-{user_id}-{uuid.uuid4().hex[:8].upper()}"
            participant = await self.repo.create_program_participant(
                tenant_id=tenant_id,
                program_id=program_id,
                user_id=user_id,
                ticket_nft_id=nft_id,
                payment_tx_hash=tx_hash,
                idempotency_key=idempotency_key
            )

            await audit_log(  # type: ignore[call-arg]
                user_id=user_id,
                tenant_id=tenant_id,
                action="PROGRAM_BOOKED",
                resource_id=participant.id,
                details={"program_id": program_id, "amount": float(program.base_price_mrusdt)}  # type: ignore
            )

        # تخزين معرف المشارك فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"participant_id": participant.id})

        return participant

    # ============================================================
    # 3. الترفيه (Entertainment)
    # ============================================================
    async def create_event(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> EntertainmentEvent:
        """إنشاء فعالية ترفيهية جديدة (للمشرفين)."""
        await self._check_saas_limits(tenant_id, "entertainment")
        sanitized_title = bleach.clean(data.get("title", ""), tags=[], strip=True)
        return await self.repo.create_event(
            tenant_id=tenant_id,
            venue_id=data["venue_id"],
            title=sanitized_title,
            event_type=data["event_type"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            base_ticket_price_mrusdt=data["base_ticket_price_mrusdt"]
        )

    # ============================================================
    # 4. شراء تذكرة فعالية (مع Idempotency محسّن)
    # ============================================================

    async def purchase_event_ticket(
        self,
        user_id: int,
        tenant_id: int,
        event_id: int,
        tier: str,
        require_vip_transport: bool,
        idempotency_key: Optional[str] = None
    ) -> NFTTicket:
        """شراء تذكرة فعالية مع Idempotency ومعاملة ذرية."""
        await self._check_saas_limits(tenant_id, "entertainment")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                ticket_id = cached.get("ticket_id")
                if ticket_id:
                    ticket = await self.repo.get_ticket(ticket_id)
                    if ticket:
                        return ticket
                raise ValidationError("Idempotency record exists but ticket not found.")

        event = await self.repo.get_event(event_id)
        if not event or event.tenant_id != tenant_id:  # type: ignore
            raise NotFoundError("Event not found")

        multiplier = {"GENERAL": 1, "VIP": 2.5, "VVIP_TRANSIT": 5}
        price = event.base_ticket_price_mrusdt * Decimal(multiplier.get(tier, 1))  # type: ignore
        if require_vip_transport and tier in ["VIP", "VVIP_TRANSIT"]:
            price += Decimal(50)

        if require_vip_transport:
            try:
                await self.ai_service.execute_agent_action(  # type: ignore[call-arg]
                    agent_id=5,
                    tenant_id=tenant_id,
                    action_type="ANALYZE_SENSOR",
                    payload={"event_id": event_id, "tier": tier},
                    executor_user_id=user_id
                )
            except Exception as e:
                logger.warning(f"AI transport optimization failed: {e}")

        async with self.db.begin_nested():
            try:
                tx_hash = await self.finance.transfer(
                    sender_id=user_id,
                    receiver_email="events@eppne.com",
                    currency="MR_USDT",
                    amount=price,
                    notes=f"Ticket for event {event_id}",
                    idempotency_key=idempotency_key or ""
                )
            except InsufficientBalanceError:
                raise PermissionDeniedError("Insufficient balance")

            await self.invoicing_service.create_invoice(  # type: ignore[attr-defined]
                entity_id=tenant_id,
                user_id=user_id,
                amount=price,
                description=f"Event ticket: {event.title} ({tier})",
                due_date=datetime.utcnow() + timedelta(days=30)
            )

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

            await audit_log(  # type: ignore[call-arg]
                user_id=user_id,
                tenant_id=tenant_id,
                action="TICKET_PURCHASED",
                resource_id=ticket.id,
                details={"event_id": event_id, "tier": tier, "amount": float(price)}
            )

        # تخزين معرف التذكرة فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"ticket_id": ticket.id})

        return ticket

    # ============================================================
    # 5. الرياضة (Sports)
    # ============================================================
    async def create_sports_org(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> SportsOrganization:
        """إنشاء منظمة رياضية جديدة."""
        await self._check_saas_limits(tenant_id, "sports")
        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)
        return await self.repo.create_sports_org(
            tenant_id=tenant_id,
            owner_id=user_id,
            name=sanitized_name,
            org_type=data["org_type"],
            main_sport=data.get("main_sport")
        )

    async def create_player_profile(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> PlayerProfile:
        """إنشاء ملف لاعب جديد."""
        await self._check_saas_limits(tenant_id, "sports")
        existing = await self.repo.get_player_profile(user_id)
        if existing:
            raise PermissionDeniedError("Player profile already exists")
        return await self.repo.create_player_profile(
            tenant_id=tenant_id,
            user_id=user_id,
            sport_category=data["sport_category"],
            position_or_role=data.get("position_or_role"),
            market_value_mrusdt=data.get("market_value_mrusdt", Decimal(0))
        )

    # ============================================================
    # 6. تقديم عرض شراء لاعب (مع Idempotency محسّن)
    # ============================================================

    async def place_transfer_bid(
        self,
        user_id: int,
        tenant_id: int,
        from_club_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> PlayerTransfer:
        """تقديم عرض شراء لاعب مع Idempotency ومعاملة ذرية."""
        await self._check_saas_limits(tenant_id, "sports")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                transfer_id = cached.get("transfer_id")
                if transfer_id:
                    transfer = await self.repo.get_transfer(transfer_id)
                    if transfer:
                        return transfer
                raise ValidationError("Idempotency record exists but transfer not found.")

        player = await self.repo.get_player_profile(data["player_id"])
        if not player or player.tenant_id != tenant_id:  # type: ignore
            raise NotFoundError("Player not found")

        from_club = await self.repo.get_sports_org(from_club_id, tenant_id)
        if not from_club or from_club.owner_id != user_id:  # type: ignore
            raise PermissionDeniedError("You are not authorized to bid from this club")

        medical_flag = False
        medical_report = None
        try:
            ai_result = await self.ai_service.execute_agent_action(  # type: ignore[call-arg]
                agent_id=6,
                tenant_id=tenant_id,
                action_type="ANALYZE_SENSOR",
                payload={
                    "player_id": data["player_id"],
                    "medical_profile_id": player.medical_profile_id,  # type: ignore
                    "sport_category": player.sport_category.value  # type: ignore
                },
                executor_user_id=user_id
            )
            medical_flag = ai_result.get("result", {}).get("flag", False)
            medical_report = ai_result.get("result", {}).get("summary")
        except Exception as e:
            logger.warning(f"AI medical analysis failed: {e}")

        from app.domains.ai_governance.service import AIGovernanceService
        governance = AIGovernanceService(self.db)
        await governance.check_and_consume(
            tenant_id=tenant_id,
            agent_id=6,
            user_id=user_id,
            tokens=200,
            cost=Decimal("0.02")
        )

        async with self.db.begin_nested():
            transfer = await self.repo.create_transfer(
                tenant_id=tenant_id,
                from_club_id=from_club_id,
                status=TransferStatus.BID_PLACED,
                medical_ai_flag=medical_flag,
                medical_report_summary=medical_report,
                idempotency_key=idempotency_key,
                **data
            )

            agency_fee = data["bid_amount_mrusdt"] * (data.get("agency_fee_percentage", 10) / 100)
            await self.invoicing_service.create_invoice(  # type: ignore[attr-defined]
                entity_id=tenant_id,
                user_id=user_id,
                amount=agency_fee,
                description=f"Agency fee for transfer of player {player.user_id}",
                due_date=datetime.utcnow() + timedelta(days=30)
            )

            if data.get("facilitating_agency_id"):
                await self._register_affiliate_commission(user_id, tenant_id, "PLAYER_TRANSFER", agency_fee)

            await audit_log(  # type: ignore[call-arg]
                user_id=user_id,
                tenant_id=tenant_id,
                action="PLAYER_TRANSFER_BID",
                resource_id=transfer.id,
                details={"player_id": data["player_id"], "bid_amount": float(data["bid_amount_mrusdt"])}
            )

        # تخزين معرف التحويل فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"transfer_id": transfer.id})

        return transfer

    async def create_tournament(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> Tournament:
        """إنشاء بطولة جديدة (للمشرفين)."""
        await self._check_saas_limits(tenant_id, "sports")
        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)
        return await self.repo.create_tournament(
            tenant_id=tenant_id,
            organizer_agency_id=data.get("organizer_agency_id"),
            name=sanitized_name,
            sport_category=data["sport_category"],
            format=data["format"],
            prize_pool_mrusdt=data.get("prize_pool_mrusdt", Decimal(0)),
            start_date=data["start_date"]
        )

    # ============================================================
    # 7. دوال مساعدة
    # ============================================================

    async def _register_affiliate_commission(
        self,
        user_id: int,
        tenant_id: int,
        action_type: str,
        amount: Decimal
    ):
        try:
            from app.domains.identity.repository import UserRepository
            user_repo = UserRepository(self.db)
            user = await user_repo.get_by_id(user_id)
            if user and user.referred_by:
                commission = amount * Decimal("0.05")
                await self.affiliate_service.register_commission(  # type: ignore[attr-defined]
                    affiliate_id=user.referred_by,
                    user_id=user_id,
                    amount=commission,
                    description=f"Affiliate commission for {action_type}",
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")