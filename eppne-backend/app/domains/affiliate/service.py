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
from app.core.system_account_service import get_or_create_system_account
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

    async def ensure_referral_link(
        self,
        referrer_user_id: int,
        referred_user_id: int,
        scope_id: int,
    ) -> tuple[Optional[ReferralTree], bool]:
        """يُنشئ صف ReferralTree لو غير موجود لهذا (referred × scope)، أو
        يرجّع الموجود بلا إنشاء (المعامل الثاني `created` يميّز الحالتين).
        عام بما يكفي ليُستخدَم مباشرة بـuser_id (الـ12 دومين، مصدره
        User.referred_by_user_id) أو عبر `track_referral` (commerce/
        academy، مصدره referral_code نصي)."""
        if referrer_user_id == referred_user_id:
            return None, False

        existing = await self.repo.get_referral_tree(referred_user_id, self.tenant_id, scope_id)
        if existing:
            return existing, False

        referrer_tree = await self.repo.get_referral_tree(referrer_user_id, self.tenant_id, scope_id)
        depth = getattr(referrer_tree, "depth", 0) + 1 if referrer_tree else 1

        new_tree = await self.repo.create_referral_tree(
            tenant_id=self.tenant_id,
            referrer_id=referrer_user_id,
            referred_id=referred_user_id,
            entity_type="SCOPE",
            entity_id=scope_id,
            depth=depth,
        )
        return new_tree, True

    async def track_referral(
        self,
        referrer_code: str,
        referred_user_id: int,
        scope_id: int,
    ) -> Optional[ReferralTree]:
        referrer = await self.repo.get_affiliate_by_code(referrer_code, self.tenant_id)
        if not referrer or not getattr(referrer, "is_active", False):
            return None

        user_repo = UserRepository(self.db)
        referred_user = await user_repo.get_by_id(referred_user_id, self.tenant_id)
        if not referred_user:
            return None

        referrer_id = cast(int, referrer.user_id)
        tree, created = await self.ensure_referral_link(referrer_id, referred_user_id, scope_id)
        if not created:
            return None

        await self.repo.update_affiliate_stats(
            referrer_id,
            self.tenant_id,
            total_conversions=getattr(referrer, "total_conversions", 0) + 1,
        )
        return tree

    # ==========================================
    # 3.ب نطاقات العمولة (Affiliate Scopes)
    # ==========================================

    async def get_default_scope_id(self) -> Optional[int]:
        """النطاق الافتراضي (ENTITY_WIDE) لهذا الـtenant — يُنشأ تلقائيًا
        وقت تفعيل خدمة affiliate كـSaaS (Phase 7). `None` يعني الخدمة
        غير مفعَّلة لهذا الـtenant بعد."""
        scope = await self.repo.get_default_scope(self.tenant_id)
        return cast(int, scope.id) if scope else None

    async def resolve_scope_id_for_member(
        self,
        member_type: str,
        member_id: Optional[int] = None,
    ) -> Optional[int]:
        """يحل النطاق الواجب تطبيقه على "شيء قابل للبيع" (منتج/كورس/حدث
        دومين): يفضّل عضوية محدَّدة (AffiliateScopeMember) لو موجودة،
        وإلا يسقط للنطاق الافتراضي (ENTITY_WIDE) لنفس الـtenant. `None`
        يعني لا نطاق محدَّد ولا نطاق افتراضي — الخدمة غير مفعَّلة."""
        member = await self.repo.get_scope_member(self.tenant_id, member_type, member_id)
        if member:
            return cast(int, member.scope_id)
        return await self.get_default_scope_id()

    async def list_scopes(self):
        return await self.repo.list_scopes(self.tenant_id)

    async def create_scope(self, name: str, scope_type: str):
        return await self.repo.create_scope(self.tenant_id, name, scope_type)

    async def add_scope_member(self, scope_id: int, member_type: str, member_id: Optional[int] = None):
        scope = await self.repo.get_scope(scope_id, self.tenant_id)
        if not scope:
            raise NotFoundError("النطاق غير موجود")
        return await self.repo.add_scope_member(scope_id, member_type, member_id)

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

    async def distribute_commissions_for_order(
        self,
        order_id: int,
        affiliate_code: Optional[str] = None,
    ) -> List[Commission]:
        """توزيع عمولات طلب commerce — لكل عنصر في السلة، يُحلّ نطاقه
        (scope) عبر AffiliateScopeMember، وتُقسَّم العمولة حسب نطاق كل
        منتج على حدة (قرار معتمد: سلة بنطاقات مختلطة تُقسَّم لا تُرفَض).
        لو affiliate_code مُمرَّر (كود الإحالة وقت الـcheckout)، يُنشئ
        رابط الإحالة أولًا (idempotent) قبل التوزيع — بديل استدعاء
        register_affiliate/distribute_commissions المنفصلين في نظام
        commerce القديم (النظام B، محذوف بالكامل)."""
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

        customer_id = cast(int, getattr(order, "customer_id", 0))
        referrer_id: Optional[int] = None
        if affiliate_code:
            referrer_profile = await self.repo.get_affiliate_by_code(affiliate_code, self.tenant_id)
            if referrer_profile and getattr(referrer_profile, "is_active", False):
                referrer_id = cast(int, referrer_profile.user_id)

        all_commissions: List[Commission] = []
        tiers = await self.repo.get_commission_tiers(self.tenant_id)

        for item in order_items:
            product_id = cast(int, getattr(item, "product_id", 0))
            scope_id = await self.resolve_scope_id_for_member("PRODUCT", product_id)
            if not scope_id:
                # لا نطاق افتراضي لهذا الـtenant — خدمة affiliate غير
                # مفعَّلة (Phase 7)، تخطَّ هذا العنصر بصمت (نفس نمط
                # "لا referral موجود" الأصلي)
                continue

            if referrer_id is not None:
                await self.ensure_referral_link(referrer_id, customer_id, scope_id)

            referral = await self.repo.get_referral_tree(customer_id, self.tenant_id, scope_id)
            if not referral:
                continue

            item_amount = Decimal(str(getattr(item, "total_price_mrusdt", 0)))
            level_commissions = await self._distribute_levels(
                referral=referral,
                item_amount=item_amount,
                scope_id=scope_id,
                tiers=tiers,
                source_type="COMMERCE_ORDER",
                source_id=cast(int, getattr(item, "id", 0)),
                order_id=order_id,
                order_item_id=cast(int, getattr(item, "id", 0)),
                product_id=product_id,
            )

            all_commissions.extend(level_commissions)

        return all_commissions

    async def distribute_commissions_for_sale_event(
        self,
        referred_user_id: int,
        scope_id: int,
        sale_amount: Decimal,
        source_type: str,
        source_id: Optional[int] = None,
    ) -> List[Commission]:
        """نقطة الدخول العامة لأي حدث بيع بلا Order تجاري — academy
        enrollment، أو حدث من أحد الـ12 دومين. تفترض إن ReferralTree
        موجود بالفعل لهذا (referred_user_id × scope_id) — استدعِ
        `ensure_referral_link` أولًا لو لسه غير مؤكَّد."""
        tiers = await self.repo.get_commission_tiers(self.tenant_id)
        referral = await self.repo.get_referral_tree(referred_user_id, self.tenant_id, scope_id)
        if not referral:
            return []
        return await self._distribute_levels(
            referral=referral,
            item_amount=sale_amount,
            scope_id=scope_id,
            tiers=tiers,
            source_type=source_type,
            source_id=source_id,
        )

    async def _distribute_levels(
        self,
        referral: ReferralTree,
        item_amount: Decimal,
        scope_id: int,
        tiers: Optional[CommissionTier],
        source_type: str,
        source_id: Optional[int] = None,
        order_id: Optional[int] = None,
        order_item_id: Optional[int] = None,
        product_id: Optional[int] = None,
    ) -> List[Commission]:
        commissions: List[Commission] = []
        current_referral = referral

        for level in range(1, 11):
            if not current_referral:
                break

            referrer_id = cast(int, current_referral.referrer_id)
            referrer_profile = await self.repo.get_affiliate_profile(referrer_id, self.tenant_id)
            if not referrer_profile or not getattr(referrer_profile, "is_active", False):
                current_referral = await self.repo.get_referral_tree(referrer_id, self.tenant_id, scope_id)
                continue

            rate = await self._get_commission_rate(
                tiers=tiers,
                level=level,
                scope_id=scope_id,
            )

            if rate <= 0:
                current_referral = await self.repo.get_referral_tree(referrer_id, self.tenant_id, scope_id)
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
                    source_type=source_type,
                    source_id=source_id,
                    scope_id=scope_id,
                    item_amount=item_amount,
                    order_amount=Decimal(0),
                    commission_rate=Decimal(rate),
                    commission_amount=commission_amount,
                    currency="MR_USDT",
                    referral_level=level,
                    entity_type="SCOPE",
                    status="PENDING",
                )
                commissions.append(commission)

            current_referral = await self.repo.get_referral_tree(referrer_id, self.tenant_id, scope_id)

        return commissions

    async def _get_commission_rate(
        self,
        tiers: Optional[CommissionTier],
        level: int,
        scope_id: int,
    ) -> Decimal:
        scope_tier = await self.repo.get_commission_tier_by_scope(
            tenant_id=self.tenant_id,
            scope_id=scope_id,
        )
        if scope_tier:
            return getattr(scope_tier, f"level_{level}_pct", Decimal(0))

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
        system_account = await get_or_create_system_account(self.db, self.tenant_id)

        async with self.db.begin_nested():
            tx = await self.finance.transfer(
                sender_id=cast(int, system_account.id),
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

    async def get_referral_tree(self, user_id: int, scope_id: int, max_depth: int = 5) -> List[dict]:
        return await self.repo.get_referral_tree_with_sponsors(user_id, self.tenant_id, scope_id, max_depth)

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

    async def create_scope_tier(
        self,
        data: CommissionTierCreate,
    ) -> CommissionTier:
        scope_id = data.target_scope_id
        if scope_id is None:
            raise ValidationError("يجب تحديد معرف النطاق (scope)")

        existing = await self.repo.get_commission_tier_by_scope(
            tenant_id=self.tenant_id,
            scope_id=scope_id,
        )
        if existing:
            raise ValidationError("توجد بالفعل إعدادات عمولات لهذا النطاق")

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

    # ==========================================
    # 11. عمولات الأحداث العابرة للدومينات (Backlog #10)
    # ==========================================
    # `register_commission`/`ActionCommission` (مستوى واحد مباشر،
    # منفصل عن التصعيد متعدد المستويات) حُذفا بالكامل في migration 045
    # — الـ12 دومين تستخدم الآن نفس خط أنابيب Commission الموحَّد عبر
    # `distribute_commissions_for_sale_event` (+ `ensure_referral_link`
    # أولًا لو الرابط غير مؤكَّد بعد)، بنفس منطق تصعيد 10 مستويات
    # المطبَّق على commerce/academy — قرار معتمد صراحة من المستخدم.

    async def get_user_by_code(self, referral_code: str) -> Optional[AffiliateProfile]:
        """جلب ملف الداعي عبر كود الإحالة (wrapper حول repo)."""
        return await self.repo.get_affiliate_by_code(referral_code, self.tenant_id)