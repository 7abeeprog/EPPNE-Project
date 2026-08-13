# app/domains/social/repository.py (الإصدار النهائي المتكامل)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, or_, and_
from typing import Optional, List
from datetime import datetime, timedelta

from app.domains.social.models import (
    Post, PostLike, PostComment, SocialGroup, GroupMember,
    SocialSmartContract, ContractSignature, AIMatchProfile, UserConnection,
    UserOccasion, OccasionReminder, DigitalGift, PhysicalGiftRequest,
    GiftReminder, GroupSubscriptionPlan, GroupSubscription
)
from app.core.errors import NotFoundError

class SocialRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ========== Posts ==========
    async def create_post(self, **kwargs) -> Post:
        post = Post(**kwargs)
        self.db.add(post)
        await self.db.commit()
        await self.db.refresh(post)
        return post

    async def get_post(self, post_id: int) -> Optional[Post]:
        result = await self.db.execute(select(Post).where(Post.id == post_id, Post.is_deleted == False))
        return result.scalar_one_or_none()

    async def get_global_feed(self, skip: int, limit: int) -> List[Post]:
        result = await self.db.execute(
            select(Post)
            .where(Post.is_deleted == False)
            .order_by(Post.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_like(self, post_id: int, user_id: int) -> bool:
        existing = await self.db.execute(select(PostLike).where(PostLike.post_id == post_id, PostLike.user_id == user_id))
        if existing.scalar_one_or_none():
            return False
            
        like = PostLike(post_id=post_id, user_id=user_id)
        self.db.add(like)
        await self.db.execute(update(Post).where(Post.id == post_id).values(likes_count=Post.likes_count + 1))
        await self.db.commit()
        return True

    async def increment_shares(self, post_id: int) -> None:
        await self.db.execute(update(Post).where(Post.id == post_id).values(shares_count=Post.shares_count + 1))
        await self.db.commit()

    # ========== Groups ==========
    async def create_group(self, **kwargs) -> SocialGroup:
        group = SocialGroup(**kwargs)
        self.db.add(group)
        await self.db.commit()
        await self.db.refresh(group)
        await self.add_group_member(group.id, group.creator_id, role="ADMIN")
        return group

    async def add_group_member(self, group_id: int, user_id: int, role: str = "MEMBER") -> GroupMember:
        member = GroupMember(group_id=group_id, user_id=user_id, role=role)
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    # ========== Contracts ==========
    async def create_contract(self, **kwargs) -> SocialSmartContract:
        contract = SocialSmartContract(**kwargs)
        self.db.add(contract)
        await self.db.commit()
        await self.db.refresh(contract)
        return contract

    async def get_contract(self, contract_id: int) -> Optional[SocialSmartContract]:
        result = await self.db.execute(select(SocialSmartContract).where(SocialSmartContract.id == contract_id))
        return result.scalar_one_or_none()

    async def add_signature(self, contract_id: int, signer_id: int, signature_hash: str) -> ContractSignature:
        sig = ContractSignature(contract_id=contract_id, signer_id=signer_id, digital_signature_hash=signature_hash)
        self.db.add(sig)
        await self.db.commit()
        return sig

    # ========== AI Matchmaking ==========
    async def get_match_profile(self, user_id: int) -> Optional[AIMatchProfile]:
        result = await self.db.execute(select(AIMatchProfile).where(AIMatchProfile.user_id == user_id))
        return result.scalar_one_or_none()

    async def create_or_update_match_profile(self, user_id: int, data: dict) -> AIMatchProfile:
        profile = await self.get_match_profile(user_id)
        if profile:
            for key, value in data.items():
                setattr(profile, key, value)
        else:
            profile = AIMatchProfile(user_id=user_id, **data)
            self.db.add(profile)
            
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def create_connection(self, user_a_id: int, user_b_id: int, connection_type: str) -> UserConnection:
        conn = UserConnection(user_a_id=user_a_id, user_b_id=user_b_id, connection_type=connection_type)
        self.db.add(conn)
        await self.db.commit()
        await self.db.refresh(conn)
        return conn

    async def get_user_connections(self, user_id: int) -> List[UserConnection]:
        result = await self.db.execute(
            select(UserConnection).where(or_(UserConnection.user_a_id == user_id, UserConnection.user_b_id == user_id))
        )
        return list(result.scalars().all())

    # ========== المناسبات والتذكيرات ==========
    async def create_occasion(self, **kwargs) -> UserOccasion:
        occasion = UserOccasion(**kwargs)
        self.db.add(occasion)
        await self.db.commit()
        await self.db.refresh(occasion)
        return occasion

    async def get_occasion(self, occasion_id: int, tenant_id: int) -> Optional[UserOccasion]:
        result = await self.db.execute(
            select(UserOccasion).where(UserOccasion.id == occasion_id, UserOccasion.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_upcoming_occasions(self, user_id: int, tenant_id: int, days_ahead: int = 30) -> List[UserOccasion]:
        now = datetime.utcnow()
        target_date = now + timedelta(days=days_ahead)
        result = await self.db.execute(
            select(UserOccasion)
            .where(
                UserOccasion.user_id == user_id,
                UserOccasion.tenant_id == tenant_id,
                UserOccasion.occasion_date >= now,
                UserOccasion.occasion_date <= target_date
            )
            .order_by(UserOccasion.occasion_date)
        )
        return result.scalars().all()

    async def create_occasion_reminder(self, **kwargs) -> OccasionReminder:
        reminder = OccasionReminder(**kwargs)
        self.db.add(reminder)
        await self.db.commit()
        await self.db.refresh(reminder)
        return reminder

    async def get_pending_occasion_reminders(self, tenant_id: int) -> List[OccasionReminder]:
        result = await self.db.execute(
            select(OccasionReminder)
            .where(
                OccasionReminder.tenant_id == tenant_id,
                OccasionReminder.status == "PENDING",
                OccasionReminder.reminder_date <= datetime.utcnow()
            )
        )
        return result.scalars().all()

    # ========== الهدايا ==========
    async def create_digital_gift(self, **kwargs) -> DigitalGift:
        gift = DigitalGift(**kwargs)
        self.db.add(gift)
        await self.db.flush()
        await self.db.refresh(gift)
        return gift

    async def create_physical_gift_request(self, **kwargs) -> PhysicalGiftRequest:
        gift = PhysicalGiftRequest(**kwargs)
        self.db.add(gift)
        await self.db.flush()
        await self.db.refresh(gift)
        return gift

    async def get_physical_gift_request(self, gift_id: int, tenant_id: int) -> Optional[PhysicalGiftRequest]:
        result = await self.db.execute(
            select(PhysicalGiftRequest).where(PhysicalGiftRequest.id == gift_id, PhysicalGiftRequest.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def update_physical_gift_status(self, gift_id: int, tenant_id: int, status: str, tracking_number: str = None) -> PhysicalGiftRequest:
        values = {"shipping_status": status}
        if tracking_number:
            values["order_tracking_number"] = tracking_number
        await self.db.execute(
            update(PhysicalGiftRequest)
            .where(PhysicalGiftRequest.id == gift_id, PhysicalGiftRequest.tenant_id == tenant_id)
            .values(**values)
        )
        await self.db.commit()
        return await self.get_physical_gift_request(gift_id, tenant_id)

    async def create_gift_reminder(self, **kwargs) -> GiftReminder:
        reminder = GiftReminder(**kwargs)
        self.db.add(reminder)
        await self.db.commit()
        await self.db.refresh(reminder)
        return reminder

    # ========== SaaS للمجموعات ==========
    async def create_subscription_plan(self, **kwargs) -> GroupSubscriptionPlan:
        plan = GroupSubscriptionPlan(**kwargs)
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def get_subscription_plan(self, plan_id: int, tenant_id: int) -> Optional[GroupSubscriptionPlan]:
        result = await self.db.execute(
            select(GroupSubscriptionPlan).where(GroupSubscriptionPlan.id == plan_id, GroupSubscriptionPlan.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def create_group_subscription(self, **kwargs) -> GroupSubscription:
        sub = GroupSubscription(**kwargs)
        self.db.add(sub)
        await self.db.flush()
        await self.db.refresh(sub)
        return sub

    async def get_active_subscription_for_group(self, group_id: int, tenant_id: int) -> Optional[GroupSubscription]:
        result = await self.db.execute(
            select(GroupSubscription)
            .where(
                GroupSubscription.group_id == group_id,
                GroupSubscription.tenant_id == tenant_id,
                GroupSubscription.status == "ACTIVE",
                GroupSubscription.end_date >= datetime.utcnow()
            )
        )
        return result.scalar_one_or_none()

    async def get_group_features(self, group_id: int, tenant_id: int) -> List[str]:
        sub = await self.get_active_subscription_for_group(group_id, tenant_id)
        if not sub:
            return []
        plan = await self.get_subscription_plan(sub.plan_id, tenant_id)
        return plan.included_features if plan else []