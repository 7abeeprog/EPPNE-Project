# app/domains/affiliate/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, cast, List
import uuid

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, require_subscription, get_current_tenant
from app.domains.identity.models import User
from app.domains.affiliate.service import AffiliateService
from app.domains.affiliate.schemas import *
from app.core.rate_limiter import rate_limit
from app.core.logging_conf import logger

router = APIRouter(prefix="/affiliate", tags=["Sovereign Affiliate"])


# ==========================================
# 1. ملف الداعي (Affiliate Profile)
# ==========================================

@router.get("/profile", response_model=AffiliateProfileResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_affiliate_profile(
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db, tenant_id)
    profile = await service.get_or_create_profile(cast(int, current_user.id))
    return profile


@router.put("/profile", response_model=AffiliateProfileResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_affiliate_profile(
    data: AffiliateProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db, tenant_id)
    profile = await service.update_profile(
        user_id=cast(int, current_user.id),
        data=data
    )
    return profile


# ==========================================
# 2. روابط الدعوة (مع حماية الاشتراك)
# ==========================================

@router.post("/links", response_model=AffiliateLinkResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=20, window_seconds=60)
async def create_affiliate_link(
    data: AffiliateLinkCreate,
    current_user: User = Depends(require_subscription("affiliate")),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db, tenant_id)
    link = await service.create_affiliate_link(
        user_id=cast(int, current_user.id),
        data=data
    )
    return link


@router.get("/links", response_model=PaginatedResponse[AffiliateLinkResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_affiliate_links(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db, tenant_id)
    return await service.get_affiliate_links(
        user_id=cast(int, current_user.id),
        skip=skip,
        limit=limit
    )


@router.patch("/links/{link_id}", response_model=AffiliateLinkResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_affiliate_link(
    link_id: int,
    data: AffiliateLinkUpdate,
    current_user: User = Depends(require_subscription("affiliate")),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db, tenant_id)
    link = await service.update_affiliate_link(
        user_id=cast(int, current_user.id),
        link_id=link_id,
        data=data
    )
    return link


# ==========================================
# 3. العمولات (مع حماية الاشتراك)
# ==========================================

@router.get("/commissions", response_model=PaginatedResponse[CommissionResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_commissions(
    status: Optional[str] = Query(None, description="PENDING, CONFIRMED, PAID, CANCELLED"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_subscription("affiliate")),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db, tenant_id)
    return await service.get_commissions_by_user(
        user_id=cast(int, current_user.id),
        status=status,
        skip=skip,
        limit=limit
    )


@router.post("/commissions/release", status_code=status.HTTP_202_ACCEPTED)
@rate_limit(max_requests=5, window_seconds=300)
async def release_commissions(
    current_user: User = Depends(require_subscription("affiliate")),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db, tenant_id)
    result = await service.release_commissions(
        user_id=cast(int, current_user.id)
    )
    return result


# ==========================================
# 4. سحب العمولات (مع حماية الاشتراك)
# ==========================================

@router.post("/withdraw", response_model=WithdrawResponse, status_code=status.HTTP_202_ACCEPTED)
@rate_limit(max_requests=5, window_seconds=300)
async def withdraw_commissions(
    data: WithdrawRequest,
    current_user: User = Depends(require_subscription("affiliate")),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db, tenant_id)
    idempotency_key = data.idempotency_key or f"WITHDRAW-{uuid.uuid4().hex[:12].upper()}"
    result = await service.withdraw_commissions(
        user_id=cast(int, current_user.id),
        amount=data.amount,
        idempotency_key=idempotency_key,
    )
    return result


# ==========================================
# 5. إحصائيات (Stats)
# ==========================================

@router.get("/stats", response_model=AffiliateStatsResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_affiliate_stats(
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db, tenant_id)
    stats = await service.get_affiliate_stats(cast(int, current_user.id))
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
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db, tenant_id)
    return await service.get_referral_tree(
        user_id=cast(int, current_user.id),
        max_depth=max_depth
    )


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
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    service = AffiliateService(db, tenant_id)
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    referer = request.headers.get("referer")

    result = await service.track_click(
        referral_code=referral_code,
        target=target,
        product_id=product_id,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        ip_address=ip,
        user_agent=ua,
        referer_url=referer,
    )
    return result


# ==========================================
# 8. إدارة العمولات (Admin Only)
# ==========================================

@router.get("/admin/tiers", response_model=CommissionTierResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def get_commission_tiers(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    service = AffiliateService(db, tenant_id)
    tiers = await service.get_commission_tiers()
    if not tiers:
        raise HTTPException(status_code=404, detail="إعدادات العمولات غير موجودة")
    return tiers


@router.put("/admin/tiers", response_model=CommissionTierResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_commission_tiers(
    data: CommissionTierUpdate,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    service = AffiliateService(db, tenant_id)
    return await service.update_commission_tiers(data)


@router.post("/admin/tiers/product", response_model=CommissionTierResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def create_product_commission_tier(
    data: CommissionTierCreate,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    service = AffiliateService(db, tenant_id)
    return await service.create_product_tier(data)


@router.post("/admin/commissions/bulk-release", status_code=status.HTTP_202_ACCEPTED)
@rate_limit(max_requests=5, window_seconds=300)
async def bulk_release_commissions(
    data: CommissionBulkReleaseRequest,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    service = AffiliateService(db, tenant_id)
    result = await service.bulk_release_commissions(
        commission_ids=data.commission_ids,
        admin_id=cast(int, current_user.id),
        notes=data.notes,
    )
    return result