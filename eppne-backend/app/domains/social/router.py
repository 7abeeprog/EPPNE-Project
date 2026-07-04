# app/domains/social/router.py (الإصدار النهائي المتكامل)
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser
from app.domains.identity.models import User
from app.domains.social.service import SocialService
from app.domains.social.repository import SocialRepository
from app.domains.social.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/social", tags=["Sovereign Social"])

# ========== Posts ==========
@router.post("/posts", response_model=PostResponse, status_code=201)
@rate_limit(max_requests=20, window_seconds=60)
async def create_post(
    data: PostCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SocialService(db)
    post = await service.create_post(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data={**data.model_dump(), "tenant_id": tenant.id}
    )
    return post

@router.get("/feed", response_model=list[PostResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_feed(
    skip: int = 0,
    limit: int = 20,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = SocialRepository(db)
    posts = await repo.get_global_feed(skip, limit)
    return posts

@router.post("/posts/{post_id}/like")
@rate_limit(max_requests=10, window_seconds=60)
async def like_post(
    post_id: int,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SocialService(db)
    result = await service.like_post(
        user_id=current_user.id,
        tenant_id=tenant.id,
        post_id=post_id,
        idempotency_key=idempotency_key
    )
    return result

@router.post("/posts/{post_id}/share")
@rate_limit(max_requests=5, window_seconds=60)
async def share_post(
    post_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SocialService(db)
    result = await service.share_post(
        user_id=current_user.id,
        tenant_id=tenant.id,
        post_id=post_id
    )
    return result

# ========== Groups & Pages ==========
@router.post("/groups", response_model=SocialGroupResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_group(
    data: SocialGroupCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = SocialRepository(db)
    group = await repo.create_group(tenant_id=tenant.id, creator_id=current_user.id, **data.model_dump())
    return group

@router.post("/groups/{group_id}/join")
@rate_limit(max_requests=20, window_seconds=60)
async def join_group(
    group_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = SocialRepository(db)
    await repo.add_group_member(group_id, current_user.id)
    return {"message": "انضممت إلى المجموعة"}

# ========== Social Contracts ==========
@router.post("/contracts", response_model=SocialContractResponse, status_code=201)
@rate_limit(max_requests=5, window_seconds=60)
async def create_contract(
    data: SocialContractCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = SocialRepository(db)
    contract = await repo.create_contract(
        tenant_id=tenant.id,
        creator_id=current_user.id,
        **data.model_dump()
    )
    return contract

@router.post("/contracts/{contract_id}/sign")
@rate_limit(max_requests=5, window_seconds=60)
async def sign_contract(
    contract_id: int,
    signature: ContractSignRequest,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SocialService(db)
    result = await service.sign_contract(
        user_id=current_user.id,
        tenant_id=tenant.id,
        contract_id=contract_id,
        signature_hash=signature.digital_signature_hash
    )
    return result

# ========== AI Matchmaking ==========
@router.post("/match/profile", response_model=AIMatchProfileResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def setup_match_profile(
    data: AIMatchProfileCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = SocialRepository(db)
    profile = await repo.create_or_update_match_profile(
        user_id=current_user.id,
        data={**data.model_dump(), "tenant_id": tenant.id}
    )
    return profile

@router.get("/match/suggestions", response_model=list[dict])
@rate_limit(max_requests=10, window_seconds=60)
async def get_match_suggestions(
    limit: int = 20,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SocialService(db)
    suggestions = await service.get_match_suggestions(
        user_id=current_user.id,
        tenant_id=tenant.id,
        limit=limit
    )
    return suggestions

@router.post("/connections/request", response_model=ConnectionResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def request_connection(
    data: ConnectionRequest,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = SocialRepository(db)
    conn = await repo.create_connection(
        user_a_id=current_user.id,
        user_b_id=data.target_user_id,
        connection_type=data.connection_type.value,
        tenant_id=tenant.id
    )
    return conn

@router.get("/connections", response_model=list[ConnectionResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def get_my_connections(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = SocialRepository(db)
    conns = await repo.get_user_connections(current_user.id)
    return conns

# ========== المناسبات والتذكيرات ==========
@router.post("/occasions", response_model=UserOccasionResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_occasion(
    data: UserOccasionCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SocialService(db)
    occasion = await service.create_occasion(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump()
    )
    return occasion

@router.get("/occasions/upcoming", response_model=list[UserOccasionResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def get_upcoming_occasions(
    days_ahead: int = 30,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = SocialRepository(db)
    occasions = await repo.get_upcoming_occasions(
        user_id=current_user.id,
        tenant_id=tenant.id,
        days_ahead=days_ahead
    )
    return occasions

# ========== الهدايا ==========
@router.post("/gifts/digital", response_model=DigitalGiftResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def send_digital_gift(
    data: DigitalGiftCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SocialService(db)
    gift = await service.send_digital_gift(
        sender_id=current_user.id,
        tenant_id=tenant.id,
        receiver_id=data.receiver_id,
        occasion_id=data.occasion_id,
        gift_type=data.gift_type,
        gift_value=data.gift_value_mrusdt,
        message=data.gift_message,
        metadata=data.gift_metadata,
        idempotency_key=idempotency_key
    )
    return gift

@router.post("/gifts/physical", response_model=PhysicalGiftResponse, status_code=201)
@rate_limit(max_requests=5, window_seconds=60)
async def request_physical_gift(
    data: PhysicalGiftCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SocialService(db)
    gift = await service.request_physical_gift(
        sender_id=current_user.id,
        tenant_id=tenant.id,
        receiver_id=data.receiver_id,
        occasion_id=data.occasion_id,
        product_id=data.product_id,
        product_name=data.product_name,
        product_price=data.product_price_mrusdt,
        shipping_address=data.shipping_address,
        idempotency_key=idempotency_key
    )
    return gift

# ========== SaaS للمجموعات ==========
@router.post("/groups/subscriptions/plans", response_model=GroupSubscriptionPlanResponse, status_code=201)
@rate_limit(max_requests=5, window_seconds=60)
async def create_subscription_plan(
    data: GroupSubscriptionPlanCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = SocialService(db)
    plan = await service.create_group_subscription_plan(
        tenant_id=tenant.id,
        data=data.model_dump()
    )
    return plan

@router.post("/groups/{group_id}/subscribe", response_model=GroupSubscriptionResponse, status_code=201)
@rate_limit(max_requests=5, window_seconds=60)
async def subscribe_group(
    group_id: int,
    data: GroupSubscriptionCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SocialService(db)
    sub = await service.subscribe_group_to_plan(
        group_id=group_id,
        tenant_id=tenant.id,
        plan_id=data.plan_id,
        duration_months=data.duration_months,
        idempotency_key=idempotency_key
    )
    return sub

@router.get("/groups/{group_id}/features", response_model=list[str])
@rate_limit(max_requests=30, window_seconds=60)
async def get_group_features(
    group_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = SocialService(db)
    features = await service.get_group_features(
        group_id=group_id,
        tenant_id=tenant.id
    )
    return features