# app/domains/affiliate/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_  # ✅ إضافة and_
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import uuid
import random
import hashlib
from typing import Optional, List, Dict, Any, cast
from fastapi import HTTPException

from app.domains.affiliate.repository import AffiliateRepository
from app.domains.affiliate.models import (
    AffiliateProfile,
    ReferralTree,
    Commission,
    CommissionTier,
    AffiliateLink,
    AffiliateClickLog,
)
from app.domains.affiliate.schemas import (
    AffiliateProfileCreate,
    AffiliateProfileUpdate,
    CommissionCreate,
    CommissionTierCreate,
    CommissionTierUpdate,
    WithdrawRequest,
    AffiliateLinkCreate,
    AffiliateLinkUpdate,
    AffiliateLinkResponse,
    CommissionResponse,
    AffiliateStatsResponse,
    CommissionBulkReleaseResponse,
)
from app.core.pagination import PaginatedResponse
from app.domains.finance.service import FinanceService
from app.domains.commerce.repository import CommerceRepository
from app.domains.identity.models import User
from app.domains.identity.repository import UserRepository
from app.core.errors import (
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
    InsufficientBalanceError,
)
from app.core.logging_conf import logger


class AffiliateService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = AffiliateRepository(db)
        self.finance = FinanceService(db, tenant_id)
        self.commerce_repo = CommerceRepository(db)

    # ==========================================
    # 1. ملف الداعي (Affiliate Profile)
    # ==========================================

    async def get_or_create_profile(self, user_id: int) -> AffiliateProfile:
        profile = await self.repo.get_affiliate_profile(user_id, self.tenant_id)
        if not profile:
            referral_code = await self._generate_referral_code(user_id)
            profile = await self.repo.create_affiliate_profile(
                tenant_id=self.tenant_id,
                user_id=user_id,
                referral_code=referral_code,
            )
        return profile

    async def update_profile(self, user_id: int, data: AffiliateProfileUpdate) -> AffiliateProfile:
        return await self.repo.update_affiliate_profile(
            user_id,
            self.tenant_id,
            **data.model_dump(exclude_unset=True)
        )

    async def _generate_referral_code(self, user_id: int) -> str:
        base = f"EPPNE-{user_id}-{uuid.uuid4().hex[:6].upper()}"
        return base[:8].upper()

    # ==========================================
    # 2. روابط الدعوة (مع tenant_id)
    # ==========================================

    async def create_affiliate_link(self, user_id: int, data: AffiliateLinkCreate) -> AffiliateLink:
        profile = await self.get_or_create_profile(user_id)

        link = await self.repo.create_affiliate_link(
            tenant_id=self.tenant_id,
            affiliate_id=profile.id,
            target=data.target,
            target_id=data.target_id,
            product_id=data.product_id,
            utm_source=data.utm_source,
            utm_medium=data.utm_medium,
            utm_campaign=data.utm_campaign,
        )
        return link

    async def get_affiliate_links(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> PaginatedResponse[AffiliateLinkResponse]:
        profile = await self.repo.get_affiliate_profile(user_id, self.tenant_id)
        if not profile:
            return PaginatedResponse(data=[], total=0, skip=skip, limit=limit)

        affiliate_id = cast(int, profile.id)
        result = await self.repo.get_affiliate_links(affiliate_id, self.tenant_id, skip, limit)
        return PaginatedResponse(
            data=[AffiliateLinkResponse.model_validate(item) for item in result.data],
            total=result.total,
            skip=result.skip,
            limit=result.limit
        )

    async def update_affiliate_link(
        self,
        user_id: int,
        link_id: int,
        data: AffiliateLinkUpdate,
    ) -> AffiliateLink:
        profile = await self.repo.get_affiliate_profile(user_id, self.tenant_id)
        if not profile:
            raise NotFoundError("ملف الداعي غير موجود")

        affiliate_id = cast(int, profile.id)
        links_result = await self.repo.get_affiliate_links(affiliate_id, self.tenant_id, 0, 100)
        link = None
        for l in links_result.data:
            if l.id == link_id:
                link = l
                break

        if not link:
            raise NotFoundError("الرابط غير موجود أو لا يخصك")

        update_data = data.model_dump(exclude_unset=True)

        if 'status' in update_data and update_data['status'] not in ['ACTIVE', 'EXPIRED', 'INACTIVE']:
            raise ValidationError("الحالة غير صالحة. القيم المسموحة: ACTIVE, EXPIRED, INACTIVE")

        await self.db.execute(
            update(AffiliateLink)
            .where(and_(AffiliateLink.id == link_id, AffiliateLink.tenant_id == self.tenant_id))
            .values(**update_data)
        )
        await self.db.commit()

        result = await self.db.execute(
            select(AffiliateLink).where(and_(AffiliateLink.id == link_id, AffiliateLink.tenant_id == self.tenant_id))
        )
        updated_link = result.scalar_one_or_none()
        if not updated_link:
            raise NotFoundError("حدث خطأ أثناء تحديث الرابط")
        return updated_link

    # ==========================================
    # 3. تتبع الإحالة (مع tenant_id)
    # ==========================================

    async def track_referral(
        self,
        referrer_code: str,
        referred_user_id: int,
        entity_type: str = "GLOBAL",
        entity_id: Optional[int] = None,
    ) -> Optional[ReferralTree]:
        referrer = await self.repo.get_affiliate_by_code(referrer_code, self.tenant_id)
        if not referrer or not getattr(referrer, "is_active", False):
            return None

        user_repo = UserRepository(self.db)
        referred_user = await user_repo.get_by_id(referred_user_id, self.tenant_id)
        if not referred_user:
            return None

        existing = await self.repo.get_referral_by_scope(
            referred_id=referred_user_id,
            entity_type=entity_type,
            tenant_id=self.tenant_id,
            entity_id=entity_id,
        )
        if existing:
            return None

        referrer_id = cast(int, referrer.user_id)
        referrer_tree = await self.repo.get_referral_tree(referrer_id, self.tenant_id)
        depth = getattr(referrer_tree, "depth", 0) + 1 if referrer_tree else 1

        await self.repo.update_affiliate_stats(
            referrer_id,
            self.tenant_id,
            total_conversions=getattr(referrer, "total_conversions", 0) + 1,
        )

        return await self.repo.create_referral_tree(
            tenant_id=self.tenant_id,
            referrer_id=referrer_id,
            referred_id=referred_user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            depth=depth,
        )

    async def track_click(
        self,
        referral_code: str,
        target: Optional[str] = None,
        product_id: Optional[int] = None,
        utm_source: Optional[str] = None,
        utm_medium: Optional[str] = None,
        utm_campaign: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referer_url: Optional[str] = None,
    ) -> dict:
        profile = await self.repo.get_affiliate_by_code(referral_code, self.tenant_id)
        if not profile or not getattr(profile, "is_active", False):
            raise HTTPException(status_code=404, detail="كود الدعوة غير صالح")

        link = None
        affiliate_id = cast(int, profile.id)
        if target:
            links_result = await self.repo.get_affiliate_links(affiliate_id, self.tenant_id, 0, 100)
            for l in links_result.data:
                if getattr(l, "target", "") == target and (product_id is None or getattr(l, "product_id", None) == product_id):
                    link = l
                    break

        click_log = await self.repo.create_click_log(
            tenant_id=self.tenant_id,
            link_id=link.id if link else None,
            affiliate_id=affiliate_id,
            ip_address=ip_address,
            user_agent=user_agent,
            referer_url=referer_url,
        )

        if link:
            await self.repo.increment_link_clicks(link.id, self.tenant_id)

        user_id = cast(int, profile.user_id)
        await self.repo.update_affiliate_stats(
            user_id,
            self.tenant_id,
            total_clicks=getattr(profile, "total_clicks", 0) + 1,
        )

        return {"message": "تم تسجيل النقرة", "click_id": getattr(click_log, "id", None)}

    # ==========================================
    # 4. توزيع العمولات (مع tenant_id)
    # ==========================================

    async def distribute_commissions(self, order_id: int) -> List[Commission]:
        order = await self.commerce_repo.get_order(order_id, self.tenant_id)
        if not order:
            return []

        order_items = []
        try:
            if hasattr(order, 'items'):
                order_items = order.items
            else:
                from app.domains.commerce.models import OrderItem
                result = await self.db.execute(
                    select(OrderItem).where(OrderItem.order_id == order_id)
                )
                order_items = result.scalars().all()
        except Exception as e:
            logger.warning(f"Could not fetch order items: {e}")
            return []

        all_commissions: List[Commission] = []
        tiers = await self.repo.get_commission_tiers(self.tenant_id)

        for item in order_items:
            product_id = getattr(item, "product_id", 0)

            referral = await self.repo.get_referral_by_scope(
                referred_id=getattr(order, "customer_id", 0),
                entity_type="PRODUCT",
                tenant_id=self.tenant_id,
                entity_id=product_id,
            )

            if not referral:
                referral = await self.repo.get_referral_by_scope(
                    referred_id=getattr(order, "customer_id", 0),
                    entity_type="GLOBAL",
                    tenant_id=self.tenant_id,
                )

            if not referral:
                continue

            item_amount = Decimal(str(getattr(item, "total_price_mrusdt", 0)))
            level_commissions = await self._distribute_levels(
                referral=referral,
                item_amount=item_amount,
                order_id=order_id,
                product_id=product_id,
                order_item_id=getattr(item, "id", 0),
                tiers=tiers,
            )

            all_commissions.extend(level_commissions)

        return all_commissions

    async def _distribute_levels(
        self,
        referral: ReferralTree,
        item_amount: Decimal,
        order_id: int,
        product_id: int,
        order_item_id: int,
        tiers: Optional[CommissionTier],
    ) -> List[Commission]:
        commissions: List[Commission] = []
        current_referral = referral

        for level in range(1, 11):
            if not current_referral:
                break

            referrer_id = cast(int, current_referral.referrer_id)
            referrer_profile = await self.repo.get_affiliate_profile(referrer_id, self.tenant_id)
            if not referrer_profile or not getattr(referrer_profile, "is_active", False):
                current_referral = await self.repo.get_referral_tree(referrer_id, self.tenant_id)
                continue

            rate = await self._get_commission_rate(
                tiers=tiers,
                level=level,
                product_id=product_id,
            )

            if rate <= 0:
                current_referral = await self.repo.get_referral_tree(referrer_id, self.tenant_id)
                continue

            commission_amount = item_amount * Decimal(rate) / Decimal(100)

            if commission_amount > 0:
                commission = await self.repo.create_commission(
                    tenant_id=self.tenant_id,
                    affiliate_id=referrer_profile.id,
                    user_id=referrer_profile.user_id,
                    order_id=order_id,
                    order_item_id=order_item_id,
                    product_id=product_id,
                    item_amount=item_amount,
                    order_amount=Decimal(0),
                    commission_rate=Decimal(rate),
                    commission_amount=commission_amount,
                    currency="MR_USDT",
                    referral_level=level,
                    entity_type="PRODUCT",
                    status="PENDING",
                )
                commissions.append(commission)

            current_referral = await self.repo.get_referral_tree(referrer_id, self.tenant_id)

        return commissions

    async def _get_commission_rate(
        self,
        tiers: Optional[CommissionTier],
        level: int,
        product_id: int,
    ) -> Decimal:
        product_tier = await self.repo.get_commission_tier_by_product(
            tenant_id=self.tenant_id,
            product_id=product_id,
        )
        if product_tier:
            return getattr(product_tier, f"level_{level}_pct", Decimal(0))

        if tiers:
            return getattr(tiers, f"level_{level}_pct", Decimal(0))

        return Decimal(0)

    # ==========================================
    # 5. العمولات (مع tenant_id)
    # ==========================================

    async def get_commissions_by_user(
        self,
        user_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> PaginatedResponse[CommissionResponse]:
        result = await self.repo.get_commissions_by_user(
            user_id,
            self.tenant_id,
            status,
            skip,
            limit
        )
        return PaginatedResponse(
            data=[CommissionResponse.model_validate(item) for item in result.data],
            total=result.total,
            skip=result.skip,
            limit=result.limit
        )

    async def release_commissions(self, user_id: int, idempotency_key: Optional[str] = None) -> dict:
        profile = await self.repo.get_affiliate_profile(user_id, self.tenant_id)
        if not profile:
            raise NotFoundError("ملف الداعي غير موجود")

        pending = await self.repo.get_pending_commissions(user_id, self.tenant_id)
        if not pending:
            return {"message": "لا توجد عمولات معلقة", "released": 0, "count": 0}

        if idempotency_key:
            logger.info(f"Processing release commissions with idempotency_key: {idempotency_key}")

        commission_ids = [cast(int, c.id) for c in pending]
        released = await self.repo.bulk_update_commission_status(
            commission_ids,
            self.tenant_id,
            status="CONFIRMED",
            updated_at=datetime.now(timezone.utc),
        )

        return {
            "message": f"تم إفراج {released} عمولة",
            "released": released,
            "count": len(pending)
        }

    # ==========================================
    # 6. سحب العمولات (مع tenant_id)
    # ==========================================

    async def withdraw_commissions(
        self,
        user_id: int,
        amount: Decimal,
        idempotency_key: str,
    ) -> dict:
        profile = await self.repo.get_affiliate_profile(user_id, self.tenant_id)
        if not profile:
            raise NotFoundError("ليس لديك ملف داعي")

        tiers = await self.repo.get_commission_tiers(self.tenant_id)
        min_withdrawal = getattr(tiers, "min_withdrawal", Decimal(10)) if tiers else Decimal(10)

        if amount < min_withdrawal:
            raise ValidationError(f"الحد الأدنى للسحب هو {min_withdrawal} MR_USDT")

        pending_commissions = await self.repo.get_pending_commissions(user_id, self.tenant_id)
        total_pending = sum(getattr(c, "commission_amount", Decimal(0)) for c in pending_commissions)

        if amount > total_pending:
            raise InsufficientBalanceError("الرصيد غير كافٍ للسحب")

        user_repo = UserRepository(self.db)
        user_obj = await user_repo.get_by_id(user_id, self.tenant_id)
        if not user_obj:
            raise NotFoundError("المستخدم غير موجود")
        receiver_email = cast(str, user_obj.email)

        async with self.db.begin_nested():
            tx = await self.finance.transfer(
                sender_id=1,
                receiver_email=receiver_email,
                amount=amount,
                currency="MR_USDT",
                notes=f"سحب عمولات الداعي {getattr(profile, 'referral_code', '')}",
                idempotency_key=idempotency_key,
            )

            remaining = amount
            paid_commissions = []
            for commission in pending_commissions:
                if remaining <= 0:
                    break
                commission_amount = getattr(commission, "commission_amount", Decimal(0))
                if commission_amount <= remaining:
                    remaining -= commission_amount
                    commission_id = cast(int, commission.id)
                    await self.repo.update_commission_status(
                        commission_id,
                        self.tenant_id,
                        status="PAID",
                        paid_at=datetime.now(timezone.utc),
                        paid_tx_hash=tx.tx_hash,
                    )
                    paid_commissions.append(commission)

        await self.repo.update_affiliate_stats(
            user_id,
            self.tenant_id,
            total_paid=getattr(profile, "total_paid", Decimal(0)) + amount,
        )

        await self.db.commit()

        return {
            "message": "تم سحب العمولات بنجاح",
            "tx_hash": tx.tx_hash,
            "amount": float(amount),
            "currency": "MR_USDT",
            "paid_commissions": len(paid_commissions),
            "created_at": datetime.now(timezone.utc),
        }

    # ==========================================
    # 7. إحصائيات الداعي
    # ==========================================

    async def get_affiliate_stats(self, user_id: int) -> Optional[AffiliateStatsResponse]:
        profile = await self.repo.get_affiliate_profile(user_id, self.tenant_id)
        if not profile:
            return None

        pending_commissions = await self.repo.get_pending_commissions(user_id, self.tenant_id)
        total_pending = sum(getattr(c, "commission_amount", Decimal(0)) for c in pending_commissions)

        total_clicks = getattr(profile, "total_clicks", 0)
        total_conversions = getattr(profile, "total_conversions", 0)
        conversion_rate = float(total_conversions / total_clicks * 100) if total_clicks > 0 else 0.0

        referral_code = cast(str, profile.referral_code)

        return AffiliateStatsResponse(
            user_id=user_id,
            referral_code=referral_code,
            total_referrals=total_conversions,
            active_referrals=0,
            total_clicks=total_clicks,
            total_conversions=total_conversions,
            total_earned=float(getattr(profile, "total_earned", 0)),
            pending_earned=float(total_pending),
            paid_earned=float(getattr(profile, "total_paid", 0)),
            conversion_rate=conversion_rate,
            top_performing_product=None,
        )

    # ==========================================
    # 8. شجرة الإحالة (مع tenant_id)
    # ==========================================

    async def get_referral_tree(self, user_id: int, max_depth: int = 5) -> List[dict]:
        return await self.repo.get_referral_tree_with_sponsors(user_id, self.tenant_id, max_depth)

    # ==========================================
    # 9. إدارة العمولات (Admin) – مع tenant_id
    # ==========================================

    async def get_commission_tiers(self) -> Optional[CommissionTier]:
        return await self.repo.get_commission_tiers(self.tenant_id)

    async def update_commission_tiers(
        self,
        data: CommissionTierUpdate,
    ) -> CommissionTier:
        tiers = await self.repo.get_commission_tiers(self.tenant_id)
        if not tiers:
            raise NotFoundError("إعدادات العمولات غير موجودة")

        tier_id = cast(int, tiers.id)
        return await self.repo.update_commission_tier(
            tier_id,
            self.tenant_id,
            **data.model_dump(exclude_unset=True)
        )

    async def create_product_tier(
        self,
        data: CommissionTierCreate,
    ) -> CommissionTier:
        product_id = data.target_product_id
        if product_id is None:
            raise ValidationError("يجب تحديد معرف المنتج")

        existing = await self.repo.get_commission_tier_by_product(
            tenant_id=self.tenant_id,
            product_id=product_id,
        )
        if existing:
            raise ValidationError("توجد بالفعل إعدادات عمولات لهذا المنتج")

        return await self.repo.create_commission_tier(
            tenant_id=self.tenant_id,
            **data.model_dump()
        )

    async def bulk_release_commissions(
        self,
        commission_ids: List[int],
        admin_id: int,
        notes: Optional[str] = None,
    ) -> CommissionBulkReleaseResponse:
        if not commission_ids:
            raise ValidationError("يجب تحديد عمولة واحدة على الأقل")

        commissions = []
        total_amount = Decimal(0)
        for cid in commission_ids:
            commission = await self.repo.get_commission(cid, self.tenant_id)
            if commission:
                commissions.append(commission)
                total_amount += getattr(commission, "commission_amount", Decimal(0))

        if not commissions:
            raise NotFoundError("لم يتم العثور على العمولات المحددة")

        async with self.db.begin_nested():
            commission_ids_int = [cast(int, c.id) for c in commissions]
            released = await self.repo.bulk_update_commission_status(
                commission_ids_int,
                self.tenant_id,
                status="CONFIRMED",
                updated_at=datetime.now(timezone.utc),
                admin_notes=notes,
            )

        tx_hash = f"BULK-RELEASE-{uuid.uuid4().hex[:12].upper()}"

        return CommissionBulkReleaseResponse(
            released_count=released,
            failed_count=len(commission_ids) - released,
            total_amount=float(total_amount),
            currency="MR_USDT",
            tx_hash=tx_hash,
        )

    # ==========================================
    # 10. تنظيف الروابط المنتهية – مع tenant_id
    # ==========================================

    async def clean_expired_invitations(self, days: int = 30) -> int:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        deleted_count = await self.repo.delete_expired_invitations(cutoff_date, self.tenant_id)
        logger.info(f"✅ Cleaned {deleted_count} expired affiliate links for tenant {self.tenant_id}")
        return deleted_count