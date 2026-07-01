# app/domains/affiliate/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from decimal import Decimal
import uuid
import random
import hashlib

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
    CommissionCreate,
    WithdrawRequest,
    AffiliateLinkCreate,
)
from app.domains.finance.service import FinanceService
from app.domains.commerce.repository import CommerceRepository
from app.core.errors import (
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
    InsufficientBalanceError,
)
from app.core.logging import logger

class AffiliateService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AffiliateRepository(db)
        self.finance = FinanceService(db)
        self.commerce_repo = CommerceRepository(db)

    # ==========================================
    # 1. ملف الداعي (Affiliate Profile)
    # ==========================================
    async def get_or_create_profile(self, user_id: int, tenant_id: int) -> AffiliateProfile:
        profile = await self.repo.get_affiliate_profile(user_id)
        if not profile:
            referral_code = await self._generate_referral_code(user_id)
            profile = await self.repo.create_affiliate_profile(
                user_id=user_id,
                tenant_id=tenant_id,
                referral_code=referral_code,
            )
        return profile

    async def _generate_referral_code(self, user_id: int) -> str:
        """توليد كود دعوة فريد (8 أحرف)"""
        base = f"EPPNE-{user_id}-{uuid.uuid4().hex[:6].upper()}"
        return base[:8].upper()

    # ==========================================
    # 2. تتبع الإحالة (Referral Tracking)
    # ==========================================
    async def track_referral(
        self,
        referrer_code: str,
        referred_user_id: int,
        entity_type: str = "GLOBAL",
        entity_id: Optional[int] = None,
    ) -> Optional[ReferralTree]:
        """تتبع الإحالة عند تسجيل مستخدم جديد"""
        referrer = await self.repo.get_affiliate_by_code(referrer_code)
        if not referrer or not referrer.is_active:
            return None

        # التحقق من عدم وجود إحالة سابقة لهذا النطاق
        existing = await self.repo.get_referral_by_scope(
            referred_id=referred_user_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        if existing:
            return None

        # حساب المستوى في الشجرة
        referrer_tree = await self.repo.get_referral_tree(referrer.user_id)
        depth = referrer_tree.depth + 1 if referrer_tree else 1

        return await self.repo.create_referral_tree(
            referrer_id=referrer.user_id,
            referred_id=referred_user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            depth=depth,
        )

    # ==========================================
    # 3. توزيع العمولات (مع تصحيح حسب المنتج)
    # ==========================================
    async def distribute_commissions(self, order_id: int, tenant_id: int) -> List[Commission]:
        """
        توزيع العمولات على الداعين عند إتمام عملية شراء.
        ✅ التصحيح: يتم التوزيع على مستوى المنتج الفردي.
        """
        # جلب الطلب مع العناصر
        order = await self.commerce_repo.get_order_with_items(order_id)
        if not order:
            return []

        all_commissions = []

        # جلب إعدادات العمولات للمستأجر
        tiers = await self.repo.get_commission_tiers(tenant_id)

        # التكرار على كل عنصر في الطلب
        for item in order.items:
            product = await self.commerce_repo.get_product(item.product_id)

            # ✅ البحث عن الداعي الخاص بهذا المنتج (PRODUCT)
            referral = await self.repo.get_referral_by_scope(
                referred_id=order.customer_id,
                entity_type="PRODUCT",
                entity_id=item.product_id,
            )

            # ✅ إذا لم يوجد، البحث عن الداعي العام (GLOBAL)
            if not referral:
                referral = await self.repo.get_referral_by_scope(
                    referred_id=order.customer_id,
                    entity_type="GLOBAL",
                )

            if not referral:
                continue

            # ✅ توزيع العمولات على مستويات الإحالة (1-10)
            level_commissions = await self._distribute_levels(
                referral=referral,
                item_amount=item.total_price_mrusdt,
                order_id=order.id,
                product_id=item.product_id,
                order_item_id=item.id,
                tenant_id=tenant_id,
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
        tenant_id: int,
        tiers: CommissionTier,
    ) -> List[Commission]:
        """توزيع العمولات على مستويات الإحالة (1-10)"""
        commissions = []
        current_referral = referral

        for level in range(1, 11):
            if not current_referral:
                break

            referrer_profile = await self.repo.get_affiliate_profile(current_referral.referrer_id)
            if not referrer_profile or not referrer_profile.is_active:
                current_referral = await self.repo.get_referral_tree(current_referral.referrer_id)
                continue

            # ✅ جلب نسبة العمولة لهذا المستوى (مع مراعاة التخصيص حسب المنتج)
            rate = await self._get_commission_rate(
                tiers=tiers,
                level=level,
                product_id=product_id,
                tenant_id=tenant_id,
            )

            if rate <= 0:
                current_referral = await self.repo.get_referral_tree(current_referral.referrer_id)
                continue

            # ✅ حساب قيمة العمولة على سعر العنصر الفردي
            commission_amount = item_amount * Decimal(rate) / Decimal(100)

            if commission_amount > 0:
                commission = await self.repo.create_commission(
                    affiliate_id=referrer_profile.id,
                    user_id=referrer_profile.user_id,
                    order_id=order_id,
                    order_item_id=order_item_id,
                    product_id=product_id,
                    tenant_id=tenant_id,
                    item_amount=item_amount,
                    order_amount=0,
                    commission_rate=rate,
                    commission_amount=commission_amount,
                    currency="MR_USDT",
                    referral_level=level,
                    entity_type="PRODUCT",
                    status="PENDING",
                )
                commissions.append(commission)

            current_referral = await self.repo.get_referral_tree(current_referral.referrer_id)

        return commissions

    async def _get_commission_rate(
        self,
        tiers: CommissionTier,
        level: int,
        product_id: int,
        tenant_id: int,
    ) -> Decimal:
        """جلب نسبة العمولة المناسبة حسب الأولوية: PRODUCT → GLOBAL"""
        # 1. البحث عن نسبة مخصصة للمنتج
        product_tier = await self.repo.get_commission_tier_by_product(
            tenant_id=tenant_id,
            product_id=product_id,
        )
        if product_tier:
            return getattr(product_tier, f"level_{level}_pct", 0)

        # 2. البحث عن النسبة العامة
        return getattr(tiers, f"level_{level}_pct", 0)

    # ==========================================
    # 4. سحب العمولات (Withdrawal)
    # ==========================================
    async def withdraw_commissions(
        self,
        user_id: int,
        amount: Decimal,
        idempotency_key: Optional[str] = None,
    ) -> dict:
        """سحب العمولات المستحقة إلى المحفظة"""
        # جلب الداعي
        profile = await self.repo.get_affiliate_profile(user_id)
        if not profile:
            raise NotFoundError("ليس لديك ملف داعي")

        # جلب إعدادات السحب
        tiers = await self.repo.get_commission_tiers(profile.tenant_id)
        min_withdrawal = tiers.min_withdrawal

        if amount < min_withdrawal:
            raise ValidationError(f"الحد الأدنى للسحب هو {min_withdrawal} MR_USDT")

        # جلب العمولات المعلقة
        pending_commissions = await self.repo.get_pending_commissions(user_id)
        total_pending = sum(c.commission_amount for c in pending_commissions)

        if amount > total_pending:
            raise InsufficientBalanceError("الرصيد غير كافٍ للسحب")

        # توليد idempotency_key
        idempotency_key = idempotency_key or f"WITHDRAW-{uuid.uuid4().hex[:12].upper()}"

        # تحويل الأموال من حساب النظام إلى المحفظة
        tx = await self.finance.transfer(
            sender_id=1,  # حساب النظام
            receiver_id=user_id,
            amount=amount,
            currency="MR_USDT",
            notes=f"سحب عمولات الداعي {profile.referral_code}",
            idempotency_key=idempotency_key,
        )

        # تحديث حالة العمولات إلى PAID (FIFO)
        remaining = amount
        paid_commissions = []
        for commission in pending_commissions:
            if remaining <= 0:
                break
            if commission.commission_amount <= remaining:
                remaining -= commission.commission_amount
                await self.repo.update_commission_status(
                    commission.id,
                    status="PAID",
                    paid_at=datetime.now(timezone.utc),
                    paid_tx_hash=tx.tx_hash,
                )
                paid_commissions.append(commission)

        # تحديث إحصائيات الداعي
        await self.repo.update_affiliate_stats(
            user_id,
            total_paid=profile.total_paid + amount,
        )

        return {
            "message": "تم سحب العمولات بنجاح",
            "tx_hash": tx.tx_hash,
            "amount": float(amount),
            "currency": "MR_USDT",
            "paid_commissions": len(paid_commissions),
            "created_at": datetime.now(timezone.utc),
        }

    # ==========================================
    # 5. روابط الدعوة (Affiliate Links)
    # ==========================================
    async def create_affiliate_link(self, user_id: int, data: AffiliateLinkCreate) -> AffiliateLink:
        profile = await self.get_or_create_profile(user_id, 1)  # tenant_id مؤقت
        link = await self.repo.create_affiliate_link(
            affiliate_id=profile.id,
            target=data.target,
            target_id=data.target_id,
            product_id=data.product_id,
            utm_source=data.utm_source,
            utm_medium=data.utm_medium,
            utm_campaign=data.utm_campaign,
        )
        return link

    # ==========================================
    # 6. إحصائيات الداعي
    # ==========================================
    async def get_affiliate_stats(self, user_id: int) -> dict:
        profile = await self.repo.get_affiliate_profile(user_id)
        if not profile:
            return None

        pending_commissions = await self.repo.get_pending_commissions(user_id)
        total_pending = sum(c.commission_amount for c in pending_commissions)

        return {
            "user_id": user_id,
            "referral_code": profile.referral_code,
            "total_referrals": profile.total_conversions,
            "active_referrals": 0,  # TODO: حساب عدد الإحالات النشطة
            "total_clicks": profile.total_clicks,
            "total_conversions": profile.total_conversions,
            "total_earned": float(profile.total_earned),
            "pending_earned": float(total_pending),
            "paid_earned": float(profile.total_paid),
            "conversion_rate": float(profile.total_conversions / profile.total_clicks * 100) if profile.total_clicks > 0 else 0,
        }