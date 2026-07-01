# app/domains/affiliate/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.api.deps import get_current_active_user, require_subscription
from app.domains.identity.models import User
from app.domains.affiliate.service import AffiliateService
from app.domains.affiliate.repository import AffiliateRepository
from app.domains.affiliate.schemas import *
from app.core.rate_limiter import rate_limit
from app.core.logging import logger

router = APIRouter(prefix="/affiliate", tags=["Sovereign Affiliate"])

# ==========================================
# 1. ملف الداعي
# ==========================================

@router.get("/profile", response_model=AffiliateProfileResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_affiliate_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """جلب ملف الداعي السيادي"""
    service = AffiliateService(db)
    profile = await service.get_or_create_profile(current_user.id, current_user.tenant_id)
    return profile


@router.put("/profile", response_model=AffiliateProfileResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_affiliate_profile(
    data: AffiliateProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """تحديث ملف الداعي"""
    service = AffiliateService(db)
    profile = await service.repo.update_affiliate_profile(current_user.id, **data.model_dump(exclude_unset=True))
    return profile


# ==========================================
# 2. روابط الدعوة (مع حماية الاشتراك)
# ==========================================

@router.post("/links", response_model=AffiliateLinkResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=20, window_seconds=60)
async def create_affiliate_link(
    data: AffiliateLinkCreate,
    current_user: User = Depends(require_subscription("affiliate")),
    db: AsyncSession = Depends(get_db),
):
    """إنشاء رابط دعوة مخصص"""
    service = AffiliateService(db)
    link = await service.create_affiliate_link(current_user.id, data)
    return link


@router.get("/links", response_model=PaginatedResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_affiliate_links(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """جلب روابط الدعوة الخاصة بالمستخدم"""
    repo = AffiliateRepository(db)
    profile = await repo.get_affiliate_profile(current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="ملف الداعي غير موجود")
    return await repo.get_affiliate_links(profile.id, skip, limit)


# ==========================================
# 3. العمولات (مع حماية الاشتراك)
# ==========================================

@router.get("/commissions", response_model=PaginatedResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_commissions(
    status: Optional[str] = Query(None, description="PENDING, CONFIRMED, PAID, CANCELLED"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_subscription("affiliate")),
    db: AsyncSession = Depends(get_db),
):
    """جلب سجل العمولات حسب الحالة"""
    repo = AffiliateRepository(db)
    return await repo.get_commissions_by_user(current_user.id, status, skip, limit)


@router.post("/commissions/release", status_code=status.HTTP_202_ACCEPTED)
@rate_limit(max_requests=5, window_seconds=300)
async def release_commissions(
    current_user: User = Depends(require_subscription("affiliate")),
    db: AsyncSession = Depends(get_db),
):
    """إفراج العمولات المعلقة (يتم تحويلها إلى العمليات الحسابية)"""
    # يتم تنفيذها في الخلفية عبر Celery
    from app.tasks.affiliate import release_commissions_task
    release_commissions_task.delay(current_user.id)
    return {"message": "تم بدء عملية إفراج العمولات، سيتم إشعارك عند الانتهاء"}


# ==========================================
# 4. سحب العمولات (مع حماية الاشتراك)
# ==========================================

@router.post("/withdraw", response_model=WithdrawResponse, status_code=status.HTTP_202_ACCEPTED)
@rate_limit(max_requests=5, window_seconds=300)
async def withdraw_commissions(
    data: WithdrawRequest,
    current_user: User = Depends(require_subscription("affiliate")),
    db: AsyncSession = Depends(get_db),
):
    """طلب سحب العمولات المستحقة إلى المحفظة"""
    service = AffiliateService(db)
    result = await service.withdraw_commissions(
        user_id=current_user.id,
        amount=data.amount,
        idempotency_key=data.idempotency_key,
    )
    return result


# ==========================================
# 5. إحصائيات (Stats)
# ==========================================

@router.get("/stats", response_model=AffiliateStatsResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_affiliate_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """جلب إحصائيات الأداء (النقرات، التحويلات، الأرباح)"""
    service = AffiliateService(db)
    stats = await service.get_affiliate_stats(current_user.id)
    if not stats:
        raise HTTPException(status_code=404, detail="ملف الداعي غير موجود")
    return stats


# ==========================================
# 6. شجرة الإحالة (Tree)
# ==========================================

@router.get("/tree", response_model=List[dict])
@rate_limit(max_requests=10, window_seconds=60)
async def get_referral_tree(
    max_depth: int = Query(5, ge=1, le=10),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """جلب شجرة الإحالة الخاصة بالمستخدم"""
    repo = AffiliateRepository(db)
    tree = await repo.get_referral_tree_with_sponsors(current_user.id, max_depth)
    return tree


# ==========================================
# 7. المسار العام لتتبع الإحالة (بدون مصادقة)
# ==========================================

@router.get("/track/{referral_code}")
async def track_referral_click(
    request: Request,
    referral_code: str,
    target: Optional[str] = Query(None),
    product_id: Optional[int] = Query(None),
    utm_source: Optional[str] = Query(None),
    utm_medium: Optional[str] = Query(None),
    utm_campaign: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """تتبع نقرات روابط الدعوة (مسار عام للمستخدمين غير المسجلين)"""
    repo = AffiliateRepository(db)
    profile = await repo.get_affiliate_by_code(referral_code)
    if not profile or not profile.is_active:
        raise HTTPException(status_code=404, detail="كود الدعوة غير صالح")

    # البحث عن الرابط المطابق
    link = None
    if target:
        links = await repo.get_affiliate_links(profile.id, 0, 100)
        for l in links.data:
            if l.target == target and (product_id is None or l.product_id == product_id):
                link = l
                break

    # تسجيل النقرة
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    click_log = await repo.create_click_log(
        link_id=link.id if link else None,
        affiliate_id=profile.id,
        ip_address=ip,
        user_agent=ua,
        referer_url=request.headers.get("referer"),
    )

    if link:
        await repo.increment_link_clicks(link.id)

    # تحديث إحصائيات الداعي
    await repo.update_affiliate_stats(profile.user_id, total_clicks=profile.total_clicks + 1)

    return {"message": "تم تسجيل النقرة", "click_id": click_log.id}