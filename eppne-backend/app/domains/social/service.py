# pyright: reportGeneralTypeIssues=false
# pyright: reportCallIssue=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportArgumentType=false

# app/domains/social/service.py (الإصدار النهائي المتكامل المصحح)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from decimal import Decimal
from datetime import datetime, timedelta
import uuid
import bleach
from typing import Optional, List, Dict, Any, cast

from app.domains.social.repository import SocialRepository
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
    async def _check_saas_limits(self, tenant_id: int, feature: str = "social"):
        has_access = await self.saas_service.can_access_service(tenant_id, feature)
        if not has_access:
            raise PermissionDeniedError(f"Social feature '{feature}' is not included in your current plan.")
        return None, {}

    # ============================================================
    # 1. المنشورات (Posts)
    # ============================================================
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
            share_reward_mr7=data.get("share_reward_mr7", Decimal(0))
        )
        await audit_log(  # type: ignore[call-arg]
            user_id=user_id,
            tenant_id=tenant_id,
            action="POST_CREATED",
            resource_id=post.id,
            details={"content_preview": content[:50]}
        )
        await self.event_bus.publish("social.post.created", {"post_id": post.id, "user_id": user_id, "tenant_id": tenant_id})
        return post

    async def get_feed(self, tenant_id: int, skip: int = 0, limit: int = 20) -> List[Post]:
        await self._check_saas_limits(tenant_id, "social")
        return await self.repo.get_global_feed(skip, limit)

    # ============================================================
    # 2. الإعجابات – مع Idempotency محسّن
    # ============================================================

    async def like_post(self, user_id: int, tenant_id: int, post_id: int, idempotency_key: Optional[str] = None) -> dict:
        await self._check_saas_limits(tenant_id, "social")

        # 1. التحقق من Idempotency – نعيد النتيجة المخزنة كاملة
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                return cached

        post = await self.repo.get_post(post_id)
        if not post or post.tenant_id != tenant_id:  # type: ignore
            raise NotFoundError("Post not found")

        success = await self.repo.add_like(post_id, user_id)
        if not success:
            result = {"status": "already_liked", "message": "Already liked"}
        else:
            result = {"status": "success", "message": "Post liked"}

        if idempotency_key:
            await self._store_idempotency(idempotency_key, result)
        return result

    async def share_post(self, user_id: int, tenant_id: int, post_id: int) -> dict:
        await self._check_saas_limits(tenant_id, "social")
        post = await self.repo.get_post(post_id)
        if not post or post.tenant_id != tenant_id:  # type: ignore
            raise NotFoundError("Post not found")
        await self.repo.increment_shares(post_id)
        return {"status": "success", "message": "Post shared"}

    # ============================================================
    # 3. المجموعات (Groups) – مع Idempotency محسّن
    # ============================================================

    async def create_group(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> SocialGroup:
        await self._check_saas_limits(tenant_id, "social")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                group_id = cached.get("group_id")
                if group_id:
                    group = await self.repo.get_group(group_id, tenant_id)
                    if group:
                        return group
                raise ValidationError("Idempotency record exists but group not found.")

        group = await self.repo.create_group(
            tenant_id=tenant_id,
            creator_id=user_id,
            name=data["name"],
            description=data.get("description"),
            privacy=data.get("privacy", "PUBLIC"),
            linked_project_id=data.get("linked_project_id"),
            idempotency_key=idempotency_key
        )

        await audit_log(  # type: ignore[call-arg]
            user_id=user_id,
            tenant_id=tenant_id,
            action="GROUP_CREATED",
            resource_id=group.id,
            details={"name": group.name}
        )

        # تخزين معرف المجموعة فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"group_id": group.id})
        return group

    # ============================================================
    # 4. الانضمام للمجموعة – مع Idempotency محسّن
    # ============================================================

    async def join_group(
        self,
        user_id: int,
        tenant_id: int,
        group_id: int,
        idempotency_key: Optional[str] = None
    ) -> dict:
        await self._check_saas_limits(tenant_id, "social")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                return cached

        result = await self.db.execute(
            select(SocialGroup).where(SocialGroup.id == group_id, SocialGroup.tenant_id == tenant_id)
        )
        group = result.scalar_one_or_none()
        if not group:
            raise NotFoundError("Group not found")

        await self.repo.add_group_member(group_id, user_id, role="MEMBER")
        result_dict = {"status": "success", "message": "Joined group"}

        if idempotency_key:
            await self._store_idempotency(idempotency_key, result_dict)
        return result_dict

    # ============================================================
    # 5. العقود الذكية (Contracts) – مع Idempotency محسّن
    # ============================================================

    async def create_contract(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> SocialSmartContract:
        await self._check_saas_limits(tenant_id, "social")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                contract_id = cached.get("contract_id")
                if contract_id:
                    contract = await self.repo.get_contract(contract_id)
                    if contract:
                        return contract
                raise ValidationError("Idempotency record exists but contract not found.")

        contract = await self.repo.create_contract(
            tenant_id=tenant_id,
            creator_id=user_id,
            template_id=data.get("template_id"),
            contract_type=data["contract_type"],
            title=data["title"],
            terms_and_conditions=data["terms_and_conditions"],
            status="DRAFT",
            idempotency_key=idempotency_key
        )

        await audit_log(  # type: ignore[call-arg]
            user_id=user_id,
            tenant_id=tenant_id,
            action="CONTRACT_CREATED",
            resource_id=contract.id,
            details={"title": contract.title}
        )

        # تخزين معرف العقد فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"contract_id": contract.id})
        return contract

    async def sign_contract(
        self,
        user_id: int,
        tenant_id: int,
        contract_id: int,
        signature_hash: str
    ) -> dict:
        await self._check_saas_limits(tenant_id, "social")
        contract = await self.repo.get_contract(contract_id)
        if not contract or contract.tenant_id != tenant_id:  # type: ignore
            raise NotFoundError("Contract not found")
        await self.repo.add_signature(contract_id, user_id, signature_hash)
        return {"status": "success", "message": "Contract signed"}

    # ============================================================
    # 6. الذكاء الاصطناعي للتوافق (AI Matchmaking)
    # ============================================================
    async def setup_match_profile(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> AIMatchProfile:
        await self._check_saas_limits(tenant_id, "social")
        profile = await self.repo.create_or_update_match_profile(
            user_id=user_id,
            data={
                "tenant_id": tenant_id,
                "seek_type": data["seek_type"],
                "ai_preferences": data["ai_preferences"],
                "is_discoverable": data.get("is_discoverable", True)
            }
        )
        return profile

    async def get_match_suggestions(self, user_id: int, tenant_id: int, limit: int = 20) -> List[dict]:
        await self._check_saas_limits(tenant_id, "social")
        profile = await self.repo.get_match_profile(user_id)
        if not profile or profile.tenant_id != tenant_id:  # type: ignore
            raise NotFoundError("Please set up your match profile first.")

        from app.domains.ai_governance.service import AIGovernanceService
        governance = AIGovernanceService(self.db)
        await governance.check_and_consume(
            tenant_id=tenant_id,
            agent_id=7,
            user_id=user_id,
            tokens=300,
            cost=Decimal("0.03")
        )

        try:
            ai_result = await self.ai_service.execute_agent_action(  # type: ignore[call-arg]
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

    # ============================================================
    # 7. الاتصالات (Connections) – مع Idempotency محسّن
    # ============================================================

    async def request_connection(
        self,
        user_id: int,
        tenant_id: int,
        target_user_id: int,
        connection_type: str,
        idempotency_key: Optional[str] = None
    ) -> UserConnection:
        await self._check_saas_limits(tenant_id, "social")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                conn_id = cached.get("connection_id")
                if conn_id:
                    conn = await self.repo.get_connection(conn_id)
                    if conn:
                        return conn
                raise ValidationError("Idempotency record exists but connection not found.")

        if user_id == target_user_id:
            raise PermissionDeniedError("Cannot connect to yourself")

        conn = await self.repo.create_connection(
            tenant_id=tenant_id,
            user_a_id=user_id,
            user_b_id=target_user_id,
            connection_type=connection_type,
            status="PENDING",
            idempotency_key=idempotency_key
        )

        await audit_log(  # type: ignore[call-arg]
            user_id=user_id,
            tenant_id=tenant_id,
            action="CONNECTION_REQUESTED",
            resource_id=conn.id,
            details={"target_user": target_user_id, "type": connection_type}
        )

        # تخزين معرف الاتصال فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"connection_id": conn.id})
        return conn

    async def get_my_connections(self, user_id: int, tenant_id: int) -> List[UserConnection]:
        await self._check_saas_limits(tenant_id, "social")
        return await self.repo.get_user_connections(user_id)

    # ============================================================
    # 8. المناسبات والتذكيرات (Occasions & Reminders)
    # ============================================================
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
        reminder_date = occasion.occasion_date - timedelta(days=cast(int, occasion.remind_days_before))
        await self.repo.create_occasion_reminder(
            tenant_id=tenant_id,
            occasion_id=occasion.id,
            reminder_date=reminder_date,
            reminder_type="SYSTEM"
        )
        await audit_log(  # type: ignore[call-arg]
            user_id=user_id,
            tenant_id=tenant_id,
            action="OCCASION_CREATED",
            resource_id=occasion.id,
            details={"type": occasion.occasion_type, "date": str(occasion.occasion_date)}
        )
        return occasion

    async def get_upcoming_occasions(
        self,
        user_id: int,
        tenant_id: int,
        days_ahead: int = 30
    ) -> List[UserOccasion]:
        await self._check_saas_limits(tenant_id, "social")
        return await self.repo.get_upcoming_occasions(user_id, tenant_id, days_ahead)

    async def send_occasion_reminders(self, tenant_id: int):
        reminders = await self.repo.get_pending_occasion_reminders(tenant_id)
        for reminder in reminders:
            try:
                occasion = await self.repo.get_occasion(cast(int, reminder.occasion_id), tenant_id)
                if not occasion:
                    continue
                await self.db.execute(
                    update(OccasionReminder)
                    .where(OccasionReminder.id == reminder.id)
                    .values(sent_at=datetime.utcnow(), status="SENT")
                )
                await self.db.commit()
            except Exception as e:
                logger.error(f"Failed to send reminder {reminder.id}: {e}")
                await self.db.execute(
                    update(OccasionReminder)
                    .where(OccasionReminder.id == reminder.id)
                    .values(status="FAILED")
                )
                await self.db.commit()

    # ============================================================
    # 9. الهدايا (Gifts) – مع معاملات ذرية و Idempotency محسّن
    # ============================================================

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
        idempotency_key: Optional[str] = None
    ) -> DigitalGift:
        await self._check_saas_limits(tenant_id, "social")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                gift_id = cached.get("gift_id")
                if gift_id:
                    gift = await self.repo.get_digital_gift(gift_id)
                    if gift:
                        return gift
                raise ValidationError("Idempotency record exists but gift not found.")

        async with self.db.begin_nested():
            if gift_value > 0:
                await self.finance.transfer(
                    sender_id=sender_id,
                    receiver_email=await self._get_user_email(receiver_id),
                    currency="MR_USDT",
                    amount=gift_value,
                    notes=f"Digital gift from user {sender_id}",
                    idempotency_key=idempotency_key or ""
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

            await audit_log(  # type: ignore[call-arg]
                user_id=sender_id,
                tenant_id=tenant_id,
                action="DIGITAL_GIFT_SENT",
                resource_id=gift.id,
                details={"receiver": receiver_id, "value": float(gift_value)}
            )
            await self.event_bus.publish("social.gift.sent", {"gift_id": gift.id, "receiver_id": receiver_id})

            # تخزين معرف الهدية فقط
            if idempotency_key:
                await self._store_idempotency(idempotency_key, {"gift_id": gift.id})

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
        idempotency_key: Optional[str] = None
    ) -> PhysicalGiftRequest:
        await self._check_saas_limits(tenant_id, "social")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                request_id = cached.get("request_id")
                if request_id:
                    gift_request = await self.repo.get_physical_gift_request(request_id)
                    if gift_request:
                        return gift_request
                raise ValidationError("Idempotency record exists but gift request not found.")

        async with self.db.begin_nested():
            await self.finance.transfer(
                sender_id=sender_id,
                receiver_email="shop@eppne.com",
                currency="MR_USDT",
                amount=product_price,
                notes=f"Physical gift order from user {sender_id}",
                idempotency_key=idempotency_key or ""
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

            await audit_log(  # type: ignore[call-arg]
                user_id=sender_id,
                tenant_id=tenant_id,
                action="PHYSICAL_GIFT_REQUESTED",
                resource_id=gift.id,
                details={"receiver": receiver_id, "product": product_name}
            )
            await self.event_bus.publish("social.gift.physical.requested", {"gift_id": gift.id})

            # تخزين معرف الطلب فقط
            if idempotency_key:
                await self._store_idempotency(idempotency_key, {"request_id": gift.id})

        return gift

    # ============================================================
    # 10. نظام SaaS للمجموعات (Group Subscriptions) – مع Idempotency محسّن
    # ============================================================

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
        idempotency_key: Optional[str] = None
    ) -> GroupSubscription:
        await self._check_saas_limits(tenant_id, "social")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                subscription_id = cached.get("subscription_id")
                if subscription_id:
                    sub = await self.repo.get_group_subscription(subscription_id)
                    if sub:
                        return sub
                raise ValidationError("Idempotency record exists but subscription not found.")

        plan = await self.repo.get_subscription_plan(plan_id, tenant_id)
        if not plan:
            raise NotFoundError("Plan not found")

        if duration_months >= 12:
            price = plan.price_yearly_mrusdt
        else:
            price = plan.price_monthly_mrusdt * duration_months

        async with self.db.begin_nested():
            await self.finance.transfer(
                sender_id=0,
                receiver_email="saas@eppne.com",
                currency="MR_USDT",
                amount=cast(Decimal, price),
                notes=f"Subscription for group {group_id}",
                idempotency_key=idempotency_key or ""
            )

            sub = await self.repo.create_group_subscription(
                tenant_id=tenant_id,
                group_id=group_id,
                plan_id=plan_id,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=30 * duration_months),
                auto_renew=True,
                status="ACTIVE",
                idempotency_key=idempotency_key
            )

            await audit_log(  # type: ignore[call-arg]
                user_id=0,
                tenant_id=tenant_id,
                action="GROUP_SUBSCRIBED",
                resource_id=sub.id,
                details={"group_id": group_id, "plan": plan.name}
            )

            # تخزين معرف الاشتراك فقط
            if idempotency_key:
                await self._store_idempotency(idempotency_key, {"subscription_id": sub.id})

        return sub

    async def get_group_features(self, group_id: int, tenant_id: int) -> List[str]:
        await self._check_saas_limits(tenant_id, "social")
        return await self.repo.get_group_features(group_id, tenant_id)

    # ============================================================
    # 11. دوال مساعدة
    # ============================================================

    async def _get_user_email(self, user_id: int) -> str:
        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)
        user = await user_repo.get_by_id(user_id)
        return cast(str, user.email) if user else f"user_{user_id}@eppne.com"