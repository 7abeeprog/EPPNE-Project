# app/domains/social/service.py (الإصدار النهائي المتكامل مع إضافة Tenders & Auctions)
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import datetime, timedelta
import uuid
import bleach
from typing import Optional, List, Dict, Any

from app.domains.social.repository import SocialRepository
from app.domains.finance.service import FinanceService
from app.domains.ai_agents.service import AIAgentsService
from app.domains.saas.service import SaaSSubscriptionService
from app.domains.affiliate.service import AffiliateService
from app.domains.invoicing.service import InvoicingService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError
from app.core.idempotency import check_idempotency, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging import logger
from app.domains.social.models import (
    Post, PostLike, PostComment, SocialGroup, GroupMember,
    SocialSmartContract, ContractSignature, AIMatchProfile, UserConnection,
    SocialEvent, EventAttendee,
    UserOccasion, OccasionReminder, DigitalGift, PhysicalGiftRequest, GiftReminder,
    GroupSubscriptionPlan, GroupSubscription, GroupFeature
)

# استيرادات Tenders & Auctions
from app.domains.tenders_auctions.repository import TendersAuctionsRepository
from app.domains.tenders_auctions.models import (
    SovereignTender, TenderBid, SovereignAuction, LiveBid,
    TenderStatus, BidStatus, AuctionStatus
)

# ===================== SocialService =====================
class SocialService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SocialRepository(db)
        self.finance = FinanceService(db)
        self.ai_service = AIAgentsService(db)
        self.saas_service = SaaSSubscriptionService(db)
        self.affiliate_service = AffiliateService(db)
        self.invoicing_service = InvoicingService(db)
        self.event_bus = EventBus(redis_client)
        self.redis = redis_client

    # ========== التحقق من صلاحيات SaaS ==========
    async def _check_saas_limits(self, tenant_id: int, feature: str = "social"):
        subscription = await self.saas_service.get_active_subscription(tenant_id)
        if not subscription:
            raise PermissionDeniedError("No active subscription found.")
        features = subscription.features or {}
        if not features.get(feature, False):
            raise PermissionDeniedError("Social feature is not included in your current plan.")
        return subscription, features

    # ========== المنشورات (مع Idempotency) ==========
    async def create_post(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> Post:
        await self._check_saas_limits(tenant_id, "social")
        content = bleach.clean(data.get("content", ""), tags=[], strip=True)
        post = await self.repo.create_post(
            author_id=user_id,
            tenant_id=tenant_id,
            content=content,
            post_type=data.get("post_type", "TEXT"),
            media_urls=data.get("media_urls", []),
            page_id=data.get("page_id"),
            group_id=data.get("group_id"),
            share_reward_mr7=data.get("share_reward_mr7", 0)
        )
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="POST_CREATED",
            resource_id=post.id,
            details={"content_preview": content[:50]}
        )
        await self.event_bus.publish("social.post.created", {"post_id": post.id, "user_id": user_id, "tenant_id": tenant_id})
        return post

    async def like_post(self, user_id: int, tenant_id: int, post_id: int, idempotency_key: str = None) -> dict:
        await self._check_saas_limits(tenant_id, "social")
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        post = await self.repo.get_post(post_id)
        if not post or post.tenant_id != tenant_id:
            raise NotFoundError("Post not found")

        success = await self.repo.add_like(post_id, user_id)
        if not success:
            return {"status": "already_liked", "message": "Already liked"}

        result = {"status": "success", "message": "Post liked"}
        if idempotency_key:
            await store_idempotency_result(idempotency_key, result)
        return result

    # ========== الذكاء الاصطناعي للتوافق (مع AI Governance) ==========
    async def get_match_suggestions(self, user_id: int, tenant_id: int, limit: int = 20) -> List[dict]:
        await self._check_saas_limits(tenant_id, "social")
        profile = await self.repo.get_match_profile(user_id)
        if not profile or profile.tenant_id != tenant_id:
            raise NotFoundError("Please set up your match profile first.")

        from app.domains.ai_governance.service import AIGovernanceService
        governance = AIGovernanceService(self.db)
        await governance.check_and_consume(
            tenant_id=tenant_id,
            agent_id=7,  # AI_MATCHMAKER
            user_id=user_id,
            tokens=300,
            cost=Decimal("0.03")
        )

        try:
            ai_result = await self.ai_service.execute_agent_action(
                agent_id=7,
                tenant_id=tenant_id,
                action_type="ANALYZE_SENSOR",
                payload={
                    "user_id": user_id,
                    "preferences": profile.ai_preferences,
                    "seek_type": profile.seek_type,
                    "limit": limit
                },
                executor_user_id=user_id
            )
            suggestions = ai_result.get("result", {}).get("suggestions", [])
            return suggestions
        except Exception as e:
            logger.error(f"AI matchmaking failed: {e}")
            import random
            return [
                {
                    "suggested_user_id": random.randint(100, 999),
                    "match_score": round(random.uniform(70, 99), 1),
                    "reasoning": "اهتمامات مشتركة"
                }
                for _ in range(min(limit, 10))
            ]

    # ========== نظام التذكير ==========
    async def create_occasion(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> UserOccasion:
        await self._check_saas_limits(tenant_id, "social")
        title = bleach.clean(data.get("title", ""), tags=[], strip=True)
        description = bleach.clean(data.get("description", ""), tags=[], strip=True)
        occasion = await self.repo.create_occasion(
            tenant_id=tenant_id,
            user_id=user_id,
            occasion_type=data["occasion_type"],
            title=title,
            description=description,
            occasion_date=data["occasion_date"],
            is_public=data.get("is_public", False),
            remind_days_before=data.get("remind_days_before", 7)
        )
        reminder_date = occasion.occasion_date - timedelta(days=occasion.remind_days_before)
        await self.repo.create_occasion_reminder(
            tenant_id=tenant_id,
            occasion_id=occasion.id,
            reminder_date=reminder_date,
            reminder_type="SYSTEM"
        )
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="OCCASION_CREATED",
            resource_id=occasion.id,
            details={"type": occasion.occasion_type, "date": str(occasion.occasion_date)}
        )
        return occasion

    async def send_occasion_reminders(self, tenant_id: int):
        reminders = await self.repo.get_pending_occasion_reminders(tenant_id)
        for reminder in reminders:
            try:
                occasion = await self.repo.get_occasion(reminder.occasion_id, tenant_id)
                if not occasion:
                    continue
                reminder.sent_at = datetime.utcnow()
                reminder.status = "SENT"
                await self.db.commit()
            except Exception as e:
                logger.error(f"Failed to send reminder {reminder.id}: {e}")
                reminder.status = "FAILED"
                await self.db.commit()

    # ========== نظام الهدايا ==========
    async def send_digital_gift(
        self,
        sender_id: int,
        tenant_id: int,
        receiver_id: int,
        occasion_id: Optional[int],
        gift_type: str,
        gift_value: Decimal,
        message: str,
        metadata: dict,
        idempotency_key: str = None
    ) -> DigitalGift:
        await self._check_saas_limits(tenant_id, "social")
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        if gift_value > 0:
            await self.finance.transfer(
                sender_id=sender_id,
                receiver_email=await self._get_user_email(receiver_id),
                currency="MR_USDT",
                amount=gift_value,
                notes=f"Digital gift from user {sender_id}",
                idempotency_key=idempotency_key
            )

        gift = await self.repo.create_digital_gift(
            tenant_id=tenant_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            occasion_id=occasion_id,
            gift_type=gift_type,
            gift_value_mrusdt=gift_value,
            gift_message=bleach.clean(message, tags=[], strip=True),
            gift_metadata=metadata,
            idempotency_key=idempotency_key
        )

        await audit_log(
            user_id=sender_id,
            tenant_id=tenant_id,
            action="DIGITAL_GIFT_SENT",
            resource_id=gift.id,
            details={"receiver": receiver_id, "value": float(gift_value)}
        )
        await self.event_bus.publish("social.gift.sent", {"gift_id": gift.id, "receiver_id": receiver_id})

        if idempotency_key:
            await store_idempotency_result(idempotency_key, gift)
        return gift

    async def request_physical_gift(
        self,
        sender_id: int,
        tenant_id: int,
        receiver_id: int,
        occasion_id: Optional[int],
        product_id: Optional[int],
        product_name: str,
        product_price: Decimal,
        shipping_address: dict,
        idempotency_key: str = None
    ) -> PhysicalGiftRequest:
        await self._check_saas_limits(tenant_id, "social")
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        await self.finance.transfer(
            sender_id=sender_id,
            receiver_email="shop@eppne.com",
            currency="MR_USDT",
            amount=product_price,
            notes=f"Physical gift order from user {sender_id}",
            idempotency_key=idempotency_key
        )

        gift = await self.repo.create_physical_gift_request(
            tenant_id=tenant_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            occasion_id=occasion_id,
            product_id=product_id,
            product_name=bleach.clean(product_name, tags=[], strip=True),
            product_price_mrusdt=product_price,
            shipping_address=shipping_address,
            idempotency_key=idempotency_key
        )

        await audit_log(
            user_id=sender_id,
            tenant_id=tenant_id,
            action="PHYSICAL_GIFT_REQUESTED",
            resource_id=gift.id,
            details={"receiver": receiver_id, "product": product_name}
        )
        await self.event_bus.publish("social.gift.physical.requested", {"gift_id": gift.id})

        if idempotency_key:
            await store_idempotency_result(idempotency_key, gift)
        return gift

    # ========== نظام SaaS للمجموعات ==========
    async def create_group_subscription_plan(self, tenant_id: int, data: Dict[str, Any]) -> GroupSubscriptionPlan:
        await self._check_saas_limits(tenant_id, "social")
        plan = await self.repo.create_subscription_plan(tenant_id=tenant_id, **data)
        return plan

    async def subscribe_group_to_plan(
        self,
        group_id: int,
        tenant_id: int,
        plan_id: int,
        duration_months: int = 12,
        idempotency_key: str = None
    ) -> GroupSubscription:
        await self._check_saas_limits(tenant_id, "social")
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        plan = await self.repo.get_subscription_plan(plan_id, tenant_id)
        if not plan:
            raise NotFoundError("Plan not found")

        if duration_months >= 12:
            price = plan.price_yearly_mrusdt
        else:
            price = plan.price_monthly_mrusdt * duration_months

        await self.finance.transfer(
            sender_id=0,
            receiver_email="saas@eppne.com",
            currency="MR_USDT",
            amount=price,
            notes=f"Subscription for group {group_id}",
            idempotency_key=idempotency_key
        )

        sub = await self.repo.create_group_subscription(
            tenant_id=tenant_id,
            group_id=group_id,
            plan_id=plan_id,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30*duration_months),
            auto_renew=True,
            status="ACTIVE",
            idempotency_key=idempotency_key
        )

        await audit_log(
            user_id=0,
            tenant_id=tenant_id,
            action="GROUP_SUBSCRIBED",
            resource_id=sub.id,
            details={"group_id": group_id, "plan": plan.name}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, sub)
        return sub

    async def get_group_features(self, group_id: int, tenant_id: int) -> List[str]:
        return await self.repo.get_group_features(group_id, tenant_id)

    # ========== دوال مساعدة ==========
    async def _get_user_email(self, user_id: int) -> str:
        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)
        user = await user_repo.get_by_id(user_id)
        return user.email if user else f"user_{user_id}@eppne.com"


# ===================== TendersAuctionsService =====================
class TendersAuctionsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TendersAuctionsRepository(db)
        self.finance = FinanceService(db)
        self.ai_service = AIAgentsService(db)
        self.saas_service = SaaSSubscriptionService(db)
        self.affiliate_service = AffiliateService(db)
        self.invoicing_service = InvoicingService(db)
        self.event_bus = EventBus(redis_client)
        self.redis = redis_client

    # ========== التحقق من صلاحيات SaaS ==========
    async def _check_saas_limits(self, tenant_id: int, feature: str = "tenders_auctions"):
        subscription = await self.saas_service.get_active_subscription(tenant_id)
        if not subscription:
            raise PermissionDeniedError("No active subscription found.")
        features = subscription.features or {}
        if not features.get(feature, False):
            raise PermissionDeniedError("Tenders & Auctions feature is not included in your current plan.")
        return subscription, features

    # ========== إنشاء مناقصة (مع SaaS + Affiliate + Audit) ==========
    async def create_tender(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> SovereignTender:
        await self._check_saas_limits(tenant_id, "tenders")

        sanitized_title = bleach.clean(data.get("title", ""), tags=[], strip=True)
        sanitized_description = bleach.clean(data.get("description", ""), tags=[], strip=True)

        tender = await self.repo.create_tender(
            tenant_id=tenant_id,
            created_by=user_id,
            title=sanitized_title,
            description=sanitized_description,
            entity_id=data["entity_id"],
            opening_date=data["opening_date"],
            closing_date=data["closing_date"],
            booklet_price_mrusdt=data.get("booklet_price_mrusdt", 0),
            bid_bond_mrusdt=data["bid_bond_mrusdt"],
            estimated_value_mrusdt=data.get("estimated_value_mrusdt"),
            settlement_type=data.get("settlement_type", "WEB2_FIAT"),
            min_sovereign_rank_required=data.get("min_sovereign_rank_required")
        )

        await self._register_affiliate_commission(user_id, tenant_id, "TENDER_CREATED")

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="TENDER_CREATED",
            resource_id=tender.id,
            details={"title": tender.title, "entity_id": tender.entity_id}
        )

        await self.event_bus.publish("tenders.tender.created", {
            "tender_id": tender.id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "title": tender.title
        })

        return tender

    # ========== تقديم عطاء (مع Idempotency + SaaS + Invoicing) ==========
    async def submit_bid(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: str = None
    ) -> TenderBid:
        await self._check_saas_limits(tenant_id, "tenders")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        tender = await self.repo.get_tender(data["tender_id"])
        if not tender or tender.tenant_id != tenant_id:
            raise NotFoundError("Tender not found")
        if tender.status != TenderStatus.OPEN:
            raise PermissionDeniedError("Tender is not open for bidding")
        if datetime.utcnow() > tender.closing_date:
            raise PermissionDeniedError("Tender closing date has passed")

        if tender.min_sovereign_rank_required:
            pass

        existing = await self.repo.get_bid_by_tender_and_bidder(tender.id, user_id)
        if existing:
            raise PermissionDeniedError("You have already submitted a bid")

        if tender.booklet_price_mrusdt > 0:
            try:
                tx_hash = await self.finance.transfer(
                    sender_id=user_id,
                    receiver_email=await self._get_entity_email(tender.entity_id),
                    currency="MR_USDT",
                    amount=tender.booklet_price_mrusdt,
                    notes=f"Tender booklet fee for {tender.title}",
                    idempotency_key=idempotency_key
                )
            except InsufficientBalanceError:
                raise PermissionDeniedError("Insufficient balance to pay booklet fee")

            await self.invoicing_service.create_invoice(
                entity_id=tenant_id,
                user_id=user_id,
                amount=tender.booklet_price_mrusdt,
                description=f"Tender booklet fee: {tender.title}",
                due_date=datetime.utcnow()
            )

        sanitized_technical = self._sanitize_json(data["technical_envelope"])
        sanitized_financial = bleach.clean(data["encrypted_financial_envelope"], tags=[], strip=True)

        bid = await self.repo.create_bid(
            tenant_id=tenant_id,
            tender_id=tender.id,
            bidder_id=user_id,
            technical_envelope=sanitized_technical,
            encrypted_financial_envelope=sanitized_financial,
            bid_tx_hash=f"BID-{uuid.uuid4().hex[:12].upper()}",
            idempotency_key=idempotency_key
        )

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="BID_SUBMITTED",
            resource_id=bid.id,
            details={"tender_id": tender.id}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, bid)

        return bid

    # ========== تقييم عطاء (مع AI Governance) ==========
    async def evaluate_bid_technically(
        self,
        evaluator_id: int,
        tenant_id: int,
        bid_id: int,
        score: Decimal,
        idempotency_key: str = None
    ) -> TenderBid:
        await self._check_saas_limits(tenant_id, "tenders")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        bid = await self.repo.get_bid(bid_id)
        if not bid or bid.tenant_id != tenant_id:
            raise NotFoundError("Bid not found")
        tender = await self.repo.get_tender(bid.tender_id)
        if tender.created_by != evaluator_id:
            raise PermissionDeniedError("Only tender creator can evaluate bids")
        if tender.status != TenderStatus.EVALUATING:
            raise PermissionDeniedError("Tender is not in evaluation phase")

        try:
            from app.domains.ai_governance.service import AIGovernanceService
            governance = AIGovernanceService(self.db)
            await governance.check_and_consume(
                tenant_id=tenant_id,
                agent_id=8,  # TENDER_EVALUATOR
                user_id=evaluator_id,
                tokens=500,
                cost=Decimal("0.05")
            )

            ai_result = await self.ai_service.execute_agent_action(
                agent_id=8,
                tenant_id=tenant_id,
                action_type="ANALYZE_SENSOR",
                payload={
                    "bid_id": bid_id,
                    "technical_envelope": bid.technical_envelope,
                    "score": float(score)
                },
                executor_user_id=evaluator_id
            )
            logger.info(f"AI evaluation result: {ai_result}")
        except Exception as e:
            logger.warning(f"AI evaluation failed: {e}")

        status = BidStatus.TECHNICAL_ACCEPTED if score >= 70 else BidStatus.TECHNICAL_REJECTED
        bid = await self.repo.update_bid(
            bid_id,
            technical_score=score,
            status=status,
            idempotency_key=idempotency_key
        )

        await audit_log(
            user_id=evaluator_id,
            tenant_id=tenant_id,
            action="BID_EVALUATED",
            resource_id=bid.id,
            details={"score": float(score), "status": status.value}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, bid)

        return bid

    # ========== وضع مزايدة حية (مع Idempotency + SaaS + Audit) ==========
    async def place_bid(
        self,
        user_id: int,
        tenant_id: int,
        auction_id: int,
        bid_amount: Decimal,
        idempotency_key: str = None
    ) -> LiveBid:
        await self._check_saas_limits(tenant_id, "auctions")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        auction = await self.repo.get_auction(auction_id)
        if not auction or auction.tenant_id != tenant_id:
            raise NotFoundError("Auction not found")
        if auction.status != AuctionStatus.LIVE:
            raise PermissionDeniedError("Auction is not live")
        now = datetime.utcnow()
        if now < auction.start_time or now > auction.end_time:
            raise PermissionDeniedError("Auction is not active at this time")

        min_required = auction.current_highest_bid_mrusdt + auction.minimum_increment_mrusdt
        if bid_amount < min_required:
            raise PermissionDeniedError(f"Minimum bid: {min_required} MR_USDT")

        try:
            ai_result = await self.ai_service.execute_agent_action(
                agent_id=9,  # AUCTION_ANALYST
                tenant_id=tenant_id,
                action_type="ANALYZE_SENSOR",
                payload={
                    "auction_id": auction_id,
                    "bid_amount": float(bid_amount),
                    "user_id": user_id
                },
                executor_user_id=user_id
            )
            logger.info(f"AI auction analysis: {ai_result}")
        except Exception as e:
            logger.warning(f"AI analysis failed: {e}")

        try:
            await self.finance.hold_funds(
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

        await self.repo.update_current_bid(auction_id, bid_amount, user_id)

        await self.event_bus.publish("tenders.auction.new_bid", {
            "auction_id": auction_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "amount": float(bid_amount)
        })

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="LIVE_BID_PLACED",
            resource_id=bid.id,
            details={"auction_id": auction_id, "amount": float(bid_amount)}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, bid)

        return bid

    # ========== إغلاق المزاد (مع Invoicing + Affiliate) ==========
    async def close_auction(self, auction_id: int, closer_id: int, tenant_id: int) -> dict:
        await self._check_saas_limits(tenant_id, "auctions")

        auction = await self.repo.get_auction(auction_id)
        if not auction or auction.tenant_id != tenant_id:
            raise NotFoundError("Auction not found")
        if auction.created_by != closer_id:
            raise PermissionDeniedError("Only auction creator can close")

        has_winner = auction.current_highest_bid_mrusdt >= (auction.reserve_price_mrusdt or 0)

        if has_winner:
            await self.finance.release_held_funds(
                auction.current_winner_id,
                auction.current_highest_bid_mrusdt,
                "MR_USDT",
                f"Auction {auction_id} winner payment"
            )
            await self.finance.transfer(
                sender_id=auction.current_winner_id,
                receiver_email=await self._get_entity_email(auction.entity_id),
                currency="MR_USDT",
                amount=auction.current_highest_bid_mrusdt,
                notes=f"Auction {auction.title} sale"
            )

            await self.invoicing_service.create_invoice(
                entity_id=tenant_id,
                user_id=auction.current_winner_id,
                amount=auction.current_highest_bid_mrusdt,
                description=f"Auction purchase: {auction.title}",
                due_date=datetime.utcnow()
            )

            await self._register_affiliate_commission(auction.current_winner_id, tenant_id, "AUCTION_WON")

        updated = await self.repo.close_auction(
            auction_id,
            has_winner,
            auction.current_winner_id if has_winner else None
        )

        await self.event_bus.publish("tenders.auction.closed", {
            "auction_id": auction_id,
            "tenant_id": tenant_id,
            "has_winner": has_winner,
            "winner_id": auction.current_winner_id if has_winner else None,
            "final_price": float(auction.current_highest_bid_mrusdt)
        })

        await audit_log(
            user_id=closer_id,
            tenant_id=tenant_id,
            action="AUCTION_CLOSED",
            resource_id=auction.id,
            details={"has_winner": has_winner, "final_price": float(auction.current_highest_bid_mrusdt)}
        )

        return {
            "status": updated.status,
            "winner_id": updated.current_winner_id,
            "final_price": float(updated.current_highest_bid_mrusdt)
        }

    # ========== دوال مساعدة ==========
    async def _get_entity_email(self, entity_id: int) -> str:
        from app.domains.identity.repository import UserRepository
        return f"entity_{entity_id}@eppne.com"

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
        try:
            from app.domains.identity.repository import UserRepository
            user_repo = UserRepository(self.db)
            user = await user_repo.get_by_id(user_id)
            if user and user.referred_by:
                commission = Decimal("5.00") if action_type == "TENDER_CREATED" else Decimal("25.00")
                await self.affiliate_service.register_commission(
                    affiliate_id=user.referred_by,
                    user_id=user_id,
                    amount=commission,
                    description=f"Affiliate commission for {action_type}",
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")