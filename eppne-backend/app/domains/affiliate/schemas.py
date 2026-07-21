# app/domains/affiliate/schemas.py
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

# استيراد الـ Pagination من الملف المركزي
from app.core.pagination import PaginatedResponse

# ==========================================
# 1. ملف الداعي (Affiliate Profile)
# ==========================================

class AffiliateProfileBase(BaseModel):
    referral_code: str = Field(description="كود الدعوة الفريد", min_length=4, max_length=20)
    custom_slug: Optional[str] = Field(None, description="اسم مخصص للرابط", max_length=50)
    default_commission_rate: Decimal = Field(Decimal('5.0'), description="نسبة العمولة الافتراضية")

class AffiliateProfileCreate(AffiliateProfileBase):
    user_id: int
    tenant_id: int

class AffiliateProfileUpdate(BaseModel):
    custom_slug: Optional[str] = None
    default_commission_rate: Optional[Decimal] = None
    is_active: Optional[bool] = None

class AffiliateProfileResponse(AffiliateProfileBase):
    id: int
    user_id: int
    tenant_id: int
    is_active: bool
    total_clicks: int
    total_conversions: int
    total_earned: float
    total_paid: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 2. شجرة الإحالة (Referral Tree)
# ==========================================

class ReferralTreeBase(BaseModel):
    referrer_id: int
    referred_id: int
    entity_type: str = Field("GLOBAL", description="GLOBAL, PRODUCT, SERVICE_CATEGORY")
    entity_id: Optional[int] = None

class ReferralTreeCreate(ReferralTreeBase):
    depth: int = 1

class ReferralTreeResponse(ReferralTreeBase):
    id: int
    depth: int
    path: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 3. العمولات (Commissions)
# ==========================================

class CommissionBase(BaseModel):
    affiliate_id: int
    user_id: int
    order_id: int
    order_item_id: int
    product_id: int
    tenant_id: int
    item_amount: Decimal
    order_amount: Decimal
    commission_rate: Decimal
    commission_amount: Decimal
    currency: str = "MR_USDT"
    referral_level: int = Field(..., ge=1, le=10)
    entity_type: str = "PRODUCT"

class CommissionCreate(CommissionBase):
    status: str = "PENDING"

class CommissionUpdate(BaseModel):
    status: Optional[str] = None
    paid_at: Optional[datetime] = None
    paid_tx_hash: Optional[str] = None

class CommissionResponse(CommissionBase):
    id: int
    status: str
    paid_at: Optional[datetime] = None
    paid_tx_hash: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 4. إعدادات العمولات (Commission Tiers)
# ==========================================

class CommissionTierBase(BaseModel):
    tenant_id: int
    entity_type: str = "GLOBAL"
    target_product_id: Optional[int] = None
    level_1_pct: Decimal = Decimal('10.0')
    level_2_pct: Decimal = Decimal('5.0')
    level_3_pct: Decimal = Decimal('3.0')
    level_4_pct: Decimal = Decimal('2.0')
    level_5_pct: Decimal = Decimal('2.0')
    level_6_pct: Decimal = Decimal('1.0')
    level_7_pct: Decimal = Decimal('1.0')
    level_8_pct: Decimal = Decimal('0.5')
    level_9_pct: Decimal = Decimal('0.5')
    level_10_pct: Decimal = Decimal('0.0')
    system_fee_pct: Decimal = Decimal('5.0')
    min_withdrawal: Decimal = Decimal('10.0')

class CommissionTierCreate(CommissionTierBase):
    pass

class CommissionTierUpdate(BaseModel):
    entity_type: Optional[str] = None
    target_product_id: Optional[int] = None
    level_1_pct: Optional[Decimal] = None
    level_2_pct: Optional[Decimal] = None
    level_3_pct: Optional[Decimal] = None
    level_4_pct: Optional[Decimal] = None
    level_5_pct: Optional[Decimal] = None
    level_6_pct: Optional[Decimal] = None
    level_7_pct: Optional[Decimal] = None
    level_8_pct: Optional[Decimal] = None
    level_9_pct: Optional[Decimal] = None
    level_10_pct: Optional[Decimal] = None
    system_fee_pct: Optional[Decimal] = None
    min_withdrawal: Optional[Decimal] = None

class CommissionTierResponse(CommissionTierBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 5. روابط الدعوة (Affiliate Links)
# ==========================================

class AffiliateLinkBase(BaseModel):
    target: str = Field(description="المسار المستهدف")
    target_id: Optional[int] = None
    product_id: Optional[int] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None

class AffiliateLinkCreate(AffiliateLinkBase):
    pass

class AffiliateLinkUpdate(BaseModel):
    target: Optional[str] = None
    product_id: Optional[int] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    is_active: Optional[bool] = None

class AffiliateLinkResponse(AffiliateLinkBase):
    id: int
    affiliate_id: int
    clicks: int
    conversions: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 6. سحب العمولات (Withdrawal)
# ==========================================

class WithdrawRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="المبلغ المراد سحبه")
    idempotency_key: Optional[str] = Field(None, description="مفتاح عدم التكرار")

class WithdrawResponse(BaseModel):
    message: str
    tx_hash: str
    amount: float
    currency: str
    paid_commissions: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 7. إحصائيات الداعي (Affiliate Stats)
# ==========================================

class AffiliateStatsResponse(BaseModel):
    user_id: int
    referral_code: str
    total_referrals: int
    active_referrals: int
    total_clicks: int
    total_conversions: int
    total_earned: float
    pending_earned: float
    paid_earned: float
    conversion_rate: float
    top_performing_product: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 8. إدارة العمولات (Admin)
# ==========================================

class CommissionBulkReleaseRequest(BaseModel):
    commission_ids: List[int] = Field(..., min_length=1, description="قائمة معرفات العمولات للإفراج")
    notes: Optional[str] = None

class CommissionBulkReleaseResponse(BaseModel):
    released_count: int
    failed_count: int
    total_amount: float
    currency: str
    tx_hash: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)