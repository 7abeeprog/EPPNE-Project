# app/domains/affiliate/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any, cast
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from app.domains.affiliate.schemas import CommissionResponse, AffiliateLinkResponse
from app.domains.affiliate.models import (
    AffiliateProfile,
    ReferralTree,
    Commission,
    CommissionTier,
    AffiliateLink,
    AffiliateClickLog,
)
from app.core.errors import NotFoundError
from app.core.pagination import PaginatedResponse


class AffiliateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ==========================================
    # 1. ملف الداعي (Affiliate Profile)
    # ==========================================
    async def get_affiliate_profile(self, user_id: int) -> Optional[AffiliateProfile]:
        result = await self.db.execute(
            select(AffiliateProfile).where(AffiliateProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_affiliate_by_code(self, referral_code: str) -> Optional[AffiliateProfile]:
        result = await self.db.execute(
            select(AffiliateProfile).where(AffiliateProfile.referral_code == referral_code)
        )
        return result.scalar_one_or_none()

    async def get_affiliate_by_id(self, affiliate_id: int) -> Optional[AffiliateProfile]:
        result = await self.db.execute(
            select(AffiliateProfile).where(AffiliateProfile.id == affiliate_id)
        )
        return result.scalar_one_or_none()

    async def create_affiliate_profile(self, **kwargs) -> AffiliateProfile:
        profile = AffiliateProfile(**kwargs)
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def update_affiliate_profile(self, user_id: int, **kwargs) -> AffiliateProfile:
        await self.db.execute(
            update(AffiliateProfile)
            .where(AffiliateProfile.user_id == user_id)
            .values(**kwargs)
        )
        await self.db.commit()
        profile = await self.get_affiliate_profile(user_id)
        if not profile:
            raise NotFoundError("ملف الداعي غير موجود")
        return profile

    async def update_affiliate_stats(self, user_id: int, **kwargs) -> AffiliateProfile:
        return await self.update_affiliate_profile(user_id, **kwargs)

    # ==========================================
    # 2. شجرة الإحالة (Referral Tree)
    # ==========================================
    async def get_referral_tree(self, user_id: int) -> Optional[ReferralTree]:
        result = await self.db.execute(
            select(ReferralTree).where(ReferralTree.referred_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_referral_by_scope(
        self,
        referred_id: int,
        entity_type: str,
        entity_id: Optional[int] = None,
    ) -> Optional[ReferralTree]:
        query = select(ReferralTree).where(
            ReferralTree.referred_id == referred_id,
            ReferralTree.entity_type == entity_type,
        )
        if entity_id is not None:
            query = query.where(ReferralTree.entity_id == entity_id)
        else:
            query = query.where(ReferralTree.entity_id.is_(None))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_referral_tree_with_sponsors(self, user_id: int, max_depth: int = 10) -> List[dict]:
        """جلب سلسلة الداعين حتى 10 مستويات مع بياناتهم"""
        chain = []
        current = await self.get_referral_tree(user_id)
        while current and len(chain) < max_depth:
            # 🔥 إصلاح: تحويل current.referrer_id من Column إلى int
            referrer_id = cast(int, current.referrer_id)
            profile = await self.get_affiliate_profile(referrer_id)
            chain.append({
                "user_id": referrer_id,
                "profile": profile,
                "depth": current.depth,
                "entity_type": current.entity_type,
                "entity_id": current.entity_id,
            })
            # 🔥 إصلاح: تحويل current.referrer_id من Column إلى int
            current = await self.get_referral_tree(referrer_id)
        return chain

    async def create_referral_tree(self, **kwargs) -> ReferralTree:
        tree = ReferralTree(**kwargs)
        self.db.add(tree)
        await self.db.commit()
        await self.db.refresh(tree)
        return tree

    # ==========================================
    # 3. العمولات (Commissions)
    # ==========================================
    async def create_commission(self, **kwargs) -> Commission:
        commission = Commission(**kwargs)
        self.db.add(commission)
        await self.db.commit()
        await self.db.refresh(commission)
        return commission

    async def get_commission(self, commission_id: int) -> Optional[Commission]:
        result = await self.db.execute(
            select(Commission).where(Commission.id == commission_id)
        )
        return result.scalar_one_or_none()

    async def get_commissions_by_user(
        self,
        user_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> PaginatedResponse[CommissionResponse]:
        query = select(Commission).where(Commission.user_id == user_id)
        if status:
            query = query.where(Commission.status == status)
        query = query.order_by(Commission.created_at.desc())

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        paginated_query = query.offset(skip).limit(limit)
        result = await self.db.execute(paginated_query)
        items = list(result.scalars().all())

        # 🔥 إصلاح: تحويل كائنات Commission إلى CommissionResponse
        response_items = [CommissionResponse.model_validate(item) for item in items]

        return PaginatedResponse(data=response_items, total=total, skip=skip, limit=limit)

    async def get_pending_commissions(self, user_id: int) -> List[Commission]:
        result = await self.db.execute(
            select(Commission).where(
                Commission.user_id == user_id,
                Commission.status == "PENDING"
            )
        )
        return list(result.scalars().all())

    async def update_commission_status(self, commission_id: int, status: str, **kwargs) -> Commission:
        await self.db.execute(
            update(Commission)
            .where(Commission.id == commission_id)
            .values(status=status, **kwargs)
        )
        await self.db.commit()
        commission = await self.get_commission(commission_id)
        if not commission:
            raise NotFoundError("العمولة غير موجودة")
        return commission

    async def bulk_update_commission_status(
        self,
        commission_ids: List[int],
        status: str,
        **kwargs
    ) -> int:
        result = await self.db.execute(
            update(Commission)
            .where(Commission.id.in_(commission_ids))
            .values(status=status, **kwargs)
        )
        await self.db.commit()
        return result.rowcount

    # ==========================================
    # 4. إعدادات العمولات (Commission Tiers)
    # ==========================================
    async def get_commission_tiers(self, tenant_id: int) -> Optional[CommissionTier]:
        result = await self.db.execute(
            select(CommissionTier).where(
                CommissionTier.tenant_id == tenant_id,
                CommissionTier.entity_type == "GLOBAL",
                CommissionTier.target_product_id.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def get_commission_tier_by_product(
        self,
        tenant_id: int,
        product_id: int,
    ) -> Optional[CommissionTier]:
        result = await self.db.execute(
            select(CommissionTier).where(
                CommissionTier.tenant_id == tenant_id,
                CommissionTier.entity_type == "PRODUCT",
                CommissionTier.target_product_id == product_id
            )
        )
        return result.scalar_one_or_none()

    async def create_commission_tier(self, **kwargs) -> CommissionTier:
        tier = CommissionTier(**kwargs)
        self.db.add(tier)
        await self.db.commit()
        await self.db.refresh(tier)
        return tier

    async def update_commission_tier(self, tier_id: int, **kwargs) -> CommissionTier:
        await self.db.execute(
            update(CommissionTier)
            .where(CommissionTier.id == tier_id)
            .values(**kwargs)
        )
        await self.db.commit()
        result = await self.db.execute(
            select(CommissionTier).where(CommissionTier.id == tier_id)
        )
        tier = result.scalar_one_or_none()
        if not tier:
            raise NotFoundError("إعدادات العمولة غير موجودة")
        return tier

    # ==========================================
    # 5. روابط الدعوة (Affiliate Links)
    # ==========================================
    async def create_affiliate_link(self, **kwargs) -> AffiliateLink:
        link = AffiliateLink(**kwargs)
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def get_affiliate_links(self, affiliate_id: int, skip: int = 0, limit: int = 20) -> PaginatedResponse[AffiliateLinkResponse]:
        query = select(AffiliateLink).where(AffiliateLink.affiliate_id == affiliate_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        paginated_query = query.offset(skip).limit(limit)
        result = await self.db.execute(paginated_query)
        items = list(result.scalars().all())

        # 🔥 إصلاح: تحويل كائنات AffiliateLink إلى AffiliateLinkResponse
        response_items = [AffiliateLinkResponse.model_validate(item) for item in items]

        return PaginatedResponse(data=response_items, total=total, skip=skip, limit=limit)

    async def increment_link_clicks(self, link_id: int) -> int:
        result = await self.db.execute(
            update(AffiliateLink)
            .where(AffiliateLink.id == link_id)
            .values(clicks=AffiliateLink.clicks + 1)
            .returning(AffiliateLink.clicks)
        )
        await self.db.commit()
        return result.scalar() or 0

    async def increment_link_conversions(self, link_id: int) -> int:
        result = await self.db.execute(
            update(AffiliateLink)
            .where(AffiliateLink.id == link_id)
            .values(conversions=AffiliateLink.conversions + 1)
            .returning(AffiliateLink.conversions)
        )
        await self.db.commit()
        return result.scalar() or 0

    # ==========================================
    # 6. سجل النقرات (Click Logs)
    # ==========================================
    async def create_click_log(self, **kwargs) -> AffiliateClickLog:
        log = AffiliateClickLog(**kwargs)
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def mark_click_conversion(self, click_log_id: int) -> AffiliateClickLog:
        await self.db.execute(
            update(AffiliateClickLog)
            .where(AffiliateClickLog.id == click_log_id)
            .values(converted=True, converted_at=datetime.now(timezone.utc))
        )
        await self.db.commit()
        result = await self.db.execute(
            select(AffiliateClickLog).where(AffiliateClickLog.id == click_log_id)
        )
        return result.scalar_one_or_none()

    # ==========================================
    # 7. 🆕 دالة تنظيف الروابط المنتهية (محدثة)
    # ==========================================
    async def delete_expired_invitations(self, cutoff_date: datetime) -> int:
        """
        حذف روابط الدعوة المنتهية الصلاحية.
        - تحذف الروابط التي حالتها 'EXPIRED' أو التي مضى على إنشائها أكثر من cutoff_date.
        - تعيد عدد السجلات المحذوفة.
        """
        result = await self.db.execute(
            delete(AffiliateLink).where(
                or_(
                    AffiliateLink.status == "EXPIRED",
                    AffiliateLink.created_at < cutoff_date
                )
            )
        )
        await self.db.commit()
        return result.rowcount