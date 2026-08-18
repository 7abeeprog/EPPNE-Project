# pyright: reportGeneralTypeIssues=false
# pyright: reportCallIssue=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportArgumentType=false

# app/domains/tenders_auctions/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import datetime
import uuid
import bleach
from typing import Optional, List, Dict, Any, cast

from app.domains.tenders_auctions.repository import TendersAuctionsRepository
from app.domains.tenders_auctions.models import (
    SovereignTender, TenderBid, SovereignAuction, LiveBid,
    TenderStatus, BidStatus, AuctionStatus
)
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


class TendersAuctionsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TendersAuctionsRepository(db)
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
    async def _check_saas_limits(self, tenant_id: int, feature: str = "tenders_auctions"):
        saas_service = SaaSSubscriptionService(self.db, tenant_id)
        has_access = await saas_service.can_access_service(tenant_id, feature)
        if not has_access:
            raise PermissionDeniedError("Tenders & Auctions feature is not included in your current plan.")
        return None, {}

    # ========== إنشاء مناقصة ==========
    async def create_tender(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> SovereignTender:
        await self._check_saas_limits(tenant_id, "tenders")

        sanitized_title = bleach.clean(data.get("title", ""), tags=[], strip=True)
        sanitized_description = bleach.clean(data.get("description", ""), tags=[], strip=True)
        sanitized_scope = self._sanitize_json(data.get("scope_of_work", {}))

        tender = await self.repo.create_tender(
            tenant_id=tenant_id,
            created_by=user_id,
            title=sanitized_title,
            description=sanitized_description,
            scope_of_work=sanitized_scope,
            estimated_budget_mrusdt=data["estimated_budget_mrusdt"],
            min_bid_mrusdt=data.get("min_bid_mrusdt"),
            max_bid_mrusdt=data.get("max_bid_mrusdt"),
            submission_start=data["submission_start"],
            submission_deadline=data["submission_deadline"],
            project_id=data.get("project_id"),
            status=TenderStatus.DRAFT
        )

        await self._register_affiliate_commission(user_id, tenant_id, "TENDER_CREATED")

        await audit_log(  # type: ignore[call-arg]
            user_id=user_id,
            tenant_id=tenant_id,
            action="TENDER_CREATED",
            resource_id=tender.id,
            details={"title": tender.title, "project_id": tender.project_id}
        )

        await self.event_bus.publish("tenders.tender.created", {
            "tender_id": tender.id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "title": tender.title
        })

        return tender

    # ========== تقديم عطاء (مع Idempotency محسّن) ==========
    async def submit_bid(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> TenderBid:
        await self._check_saas_limits(tenant_id, "tenders")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                bid_id = cached.get("bid_id")
                if bid_id:
                    bid = await self.repo.get_bid(bid_id)
                    if bid:
                        return bid
                raise ValidationError("Idempotency record exists but bid not found.")

        tender = await self.repo.get_tender(data["tender_id"])
        if not tender or tender.tenant_id != tenant_id:  # type: ignore
            raise NotFoundError("Tender not found")
        if tender.status != TenderStatus.PUBLISHED:  # type: ignore
            raise PermissionDeniedError("Tender is not open for bidding")
        if datetime.utcnow() > tender.submission_deadline:  # type: ignore
            raise PermissionDeniedError("Tender submission deadline has passed")

        existing = await self.repo.get_bid_by_tender_and_bidder(tender.id, user_id)  # type: ignore
        if existing:
            raise PermissionDeniedError("You have already submitted a bid")

        sanitized_technical = self._sanitize_json(data["technical_envelope"])
        sanitized_financial = bleach.clean(data["encrypted_financial_envelope"], tags=[], strip=True)

        bid = await self.repo.create_bid(
            tenant_id=tenant_id,
            tender_id=tender.id,  # type: ignore
            bidder_id=user_id,
            technical_envelope=sanitized_technical,
            encrypted_financial_envelope=sanitized_financial,
            bid_tx_hash=f"BID-{uuid.uuid4().hex[:12].upper()}",
            idempotency_key=idempotency_key
        )

        await audit_log(  # type: ignore[call-arg]
            user_id=user_id,
            tenant_id=tenant_id,
            action="BID_SUBMITTED",
            resource_id=bid.id,
            details={"tender_id": tender.id}
        )

        # تخزين معرف العطاء فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"bid_id": bid.id})

        return bid

    # ========== تقييم عطاء (مع Idempotency محسّن) ==========
    async def evaluate_bid_technically(
        self,
        evaluator_id: int,
        tenant_id: int,
        bid_id: int,
        score: Decimal,
        idempotency_key: Optional[str] = None
    ) -> TenderBid:
        await self._check_saas_limits(tenant_id, "tenders")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                bid_id_cached = cached.get("bid_id")
                if bid_id_cached:
                    bid = await self.repo.get_bid(bid_id_cached)
                    if bid:
                        return bid
                raise ValidationError("Idempotency record exists but bid not found.")

        bid = await self.repo.get_bid(bid_id)
        if not bid or bid.tenant_id != tenant_id:  # type: ignore
            raise NotFoundError("Bid not found")
        tender = await self.repo.get_tender(bid.tender_id)  # type: ignore
        if tender.created_by != evaluator_id:  # type: ignore
            raise PermissionDeniedError("Only tender creator can evaluate bids")
        if tender.status != TenderStatus.EVALUATION:  # type: ignore
            raise PermissionDeniedError("Tender is not in evaluation phase")

        # AI Governance
        ai_service = AIAgentsService(self.db, tenant_id)
        try:
            from app.domains.ai_governance.service import AIGovernanceService
            governance = AIGovernanceService(self.db, tenant_id)
            await governance.check_and_consume(
                agent_id=8,
                user_id=evaluator_id,
                action_type="BID_EVALUATION",
                tokens=500,
                cost=Decimal("0.05")
            )

            ai_result = await ai_service.execute_agent_action(
                agent_id=8,
                action_type="ANALYZE_SENSOR",
                payload={
                    "bid_id": bid_id,
                    "technical_envelope": bid.technical_envelope,
                    "score": float(score)
                },
                executor_user_id=evaluator_id,
                idempotency_key=f"AI-BIDEVAL-T{tenant_id}-{bid_id}"
            )
            logger.info(f"AI evaluation result: {ai_result}")
        except Exception as e:
            logger.warning(f"AI evaluation failed: {e}")

        status = BidStatus.ACCEPTED if score >= 70 else BidStatus.REJECTED
        bid = await self.repo.update_bid(
            bid_id,
            technical_score=score,
            status=status,
            idempotency_key=idempotency_key
        )

        await audit_log(  # type: ignore[call-arg]
            user_id=evaluator_id,
            tenant_id=tenant_id,
            action="BID_EVALUATED",
            resource_id=bid.id,
            details={"score": float(score), "status": status.value}
        )

        # تخزين معرف العطاء فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"bid_id": bid.id})

        return bid

    # ========== إنشاء مزاد ==========
    async def create_auction(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> SovereignAuction:
        await self._check_saas_limits(tenant_id, "auctions")

        sanitized_title = bleach.clean(data.get("title", ""), tags=[], strip=True)
        sanitized_description = bleach.clean(data.get("description", ""), tags=[], strip=True)

        auction = await self.repo.create_auction(
            tenant_id=tenant_id,
            created_by=user_id,
            title=sanitized_title,
            description=sanitized_description,
            asset_type=data["asset_type"],
            asset_id=data.get("asset_id"),
            start_price_mrusdt=data["start_price_mrusdt"],
            min_increment_mrusdt=data.get("min_increment_mrusdt", Decimal(0)),
            start_time=data["start_time"],
            end_time=data["end_time"],
            status=AuctionStatus.DRAFT
        )

        await audit_log(  # type: ignore[call-arg]
            user_id=user_id,
            tenant_id=tenant_id,
            action="AUCTION_CREATED",
            resource_id=auction.id,
            details={"title": auction.title, "asset_type": auction.asset_type}
        )

        await self.event_bus.publish("tenders.auction.created", {
            "auction_id": auction.id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "title": auction.title
        })

        return auction

    # ========== وضع مزايدة حية (مع Idempotency محسّن) ==========
    async def place_bid(
        self,
        user_id: int,
        tenant_id: int,
        auction_id: int,
        bid_amount: Decimal,
        idempotency_key: Optional[str] = None
    ) -> LiveBid:
        await self._check_saas_limits(tenant_id, "auctions")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                bid_id = cached.get("bid_id")
                if bid_id:
                    live_bid = await self.repo.get_live_bid(bid_id)
                    if live_bid:
                        return live_bid
                raise ValidationError("Idempotency record exists but live bid not found.")

        auction = await self.repo.get_auction(auction_id)
        if not auction or auction.tenant_id != tenant_id:  # type: ignore
            raise NotFoundError("Auction not found")
        
        auction_status = cast(AuctionStatus, auction.status)
        if auction_status != AuctionStatus.OPEN:
            raise PermissionDeniedError("Auction is not open")
        
        now = datetime.utcnow()
        if now < auction.start_time or now > auction.end_time:  # type: ignore
            raise PermissionDeniedError("Auction is not active at this time")

        # الحصول على أعلى مزايدة حالية من جدول live_bids
        live_bids = await self.repo.get_live_bids_for_auction(auction_id, limit=1)
        current_highest = live_bids[0].bid_amount_mrusdt if live_bids else auction.start_price_mrusdt
        min_required = current_highest + auction.min_increment_mrusdt  # type: ignore
        if bid_amount < min_required:
            raise PermissionDeniedError(f"Minimum bid: {min_required} MR_USDT")

        # AI تحليل
        ai_service = AIAgentsService(self.db, tenant_id)
        try:
            ai_result = await ai_service.execute_agent_action(
                agent_id=9,
                action_type="ANALYZE_SENSOR",
                payload={
                    "auction_id": auction_id,
                    "bid_amount": float(bid_amount),
                    "user_id": user_id
                },
                executor_user_id=user_id,
                idempotency_key=f"AI-AUCTIONBID-T{tenant_id}-{idempotency_key}" if idempotency_key else f"AI-AUCTIONBID-T{tenant_id}-{uuid.uuid4().hex[:12]}"
            )
            logger.info(f"AI auction analysis: {ai_result}")
        except Exception as e:
            logger.warning(f"AI analysis failed: {e}")

        # حجز المبلغ
        finance = FinanceService(self.db, tenant_id)
        try:
            await finance.hold_funds(  # type: ignore[attr-defined]
                user_id,
                bid_amount,
                "MR_USDT",
                f"Auction {auction_id} bid",
                idempotency_key=idempotency_key
            )
        except InsufficientBalanceError:
            raise PermissionDeniedError("Insufficient balance to place this bid")

        bid = await self.repo.create_live_bid(
            tenant_id=tenant_id,
            auction_id=auction_id,
            bidder_id=user_id,
            bid_amount_mrusdt=bid_amount,
            bid_tx_hash=f"BID-{uuid.uuid4().hex[:12].upper()}",
            idempotency_key=idempotency_key
        )

        await self.event_bus.publish("tenders.auction.new_bid", {
            "auction_id": auction_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "amount": float(bid_amount)
        })

        await audit_log(  # type: ignore[call-arg]
            user_id=user_id,
            tenant_id=tenant_id,
            action="LIVE_BID_PLACED",
            resource_id=bid.id,
            details={"auction_id": auction_id, "amount": float(bid_amount)}
        )

        # تخزين معرف المزايدة فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"bid_id": bid.id})

        return bid

    # ========== إغلاق المزاد ==========
    async def close_auction(self, auction_id: int, closer_id: int, tenant_id: int) -> dict:
        await self._check_saas_limits(tenant_id, "auctions")

        auction = await self.repo.get_auction(auction_id)
        if not auction or auction.tenant_id != tenant_id:  # type: ignore
            raise NotFoundError("Auction not found")
        if auction.created_by != closer_id:  # type: ignore
            raise PermissionDeniedError("Only auction creator can close")

        live_bids = await self.repo.get_live_bids_for_auction(auction_id, limit=1)
        highest_bid = live_bids[0] if live_bids else None
        has_winner = highest_bid is not None

        if has_winner and highest_bid:
            bidder_id = cast(int, highest_bid.bidder_id)
            bid_amount = cast(Decimal, highest_bid.bid_amount_mrusdt)
            
            finance = FinanceService(self.db, tenant_id)
            await finance.release_held_funds(  # type: ignore[attr-defined]
                bidder_id,
                bid_amount,
                "MR_USDT",
                f"Auction {auction_id} winner payment"
            )
            await finance.transfer(
                sender_id=bidder_id,
                receiver_email="system@eppne.com",
                currency="MR_USDT",
                amount=bid_amount,
                notes=f"Auction {auction.title} sale",
                idempotency_key=f"AUCTION-SALE-{auction_id}-{uuid.uuid4().hex[:8]}"
            )

            invoice_service = InvoicingService(self.db, tenant_id)
            await invoice_service.create_invoice(  # type: ignore[attr-defined]
                entity_id=tenant_id,
                user_id=bidder_id,
                amount=bid_amount,
                description=f"Auction purchase: {auction.title}",
                due_date=datetime.utcnow()
            )

            await self._register_affiliate_commission(bidder_id, tenant_id, "AUCTION_WON")

        updated = await self.repo.close_auction(
            auction_id,
            has_winner,
            cast(int, highest_bid.id) if has_winner and highest_bid else None
        )

        final_price = float(cast(Decimal, highest_bid.bid_amount_mrusdt)) if has_winner and highest_bid else 0
        winner_id = cast(int, highest_bid.bidder_id) if has_winner and highest_bid else None

        await self.event_bus.publish("tenders.auction.closed", {
            "auction_id": auction_id,
            "tenant_id": tenant_id,
            "has_winner": has_winner,
            "winner_id": winner_id,
            "final_price": final_price
        })

        await audit_log(  # type: ignore[call-arg]
            user_id=closer_id,
            tenant_id=tenant_id,
            action="AUCTION_CLOSED",
            resource_id=auction.id,
            details={"has_winner": has_winner, "final_price": final_price}
        )

        return {
            "status": updated.status,
            "winner_id": winner_id,
            "final_price": final_price
        }

    # ========== دوال مساعدة ==========
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

    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, action_type: str):
        affiliate_service = AffiliateService(self.db, tenant_id)
        try:
            from app.domains.identity.repository import UserRepository
            user_repo = UserRepository(self.db)
            user = await user_repo.get_by_id(user_id)
            if user and user.referred_by:
                commission = Decimal("5.00") if action_type == "TENDER_CREATED" else Decimal("25.00")
                await affiliate_service.register_commission(  # type: ignore[attr-defined]
                    affiliate_id=user.referred_by,
                    user_id=user_id,
                    amount=commission,
                    description=f"Affiliate commission for {action_type}",
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")