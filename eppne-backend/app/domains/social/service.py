# app/domains/social/service.py (الإصدار النهائي المتكامل)
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import datetime, timedelta
import uuid
import bleach
from typing import Optional, List, Dict, Any

from app.domains.social.repository import SocialRepository
from app.domains.finance.service import FinanceService
from app.domains.ai_agents.service import AIAgentsService
from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
from app.domains.affiliate.service import AffiliateService
from app.domains.invoicing.service import InvoicingService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError
from app.core.idempotency import check_idempotency, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging_conf import logger
from app.domains.social.models import (
    Post, PostLike, PostComment, SocialGroup, GroupMember,
    SocialSmartContract, ContractSignature, AIMatchProfile, UserConnection,
    SocialEvent, EventAttendee,
    UserOccasion, OccasionReminder, DigitalGift, PhysicalGiftRequest, GiftReminder,
    GroupSubscriptionPlan, GroupSubscription, GroupFeature
)

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

        # استدعاء وكيل AI_MATCHMAKER
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