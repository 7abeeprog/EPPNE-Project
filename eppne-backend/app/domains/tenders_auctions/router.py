# app/domains/tenders_auctions/router.py
from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, cast

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant
from app.domains.identity.models import User
from app.domains.tenders_auctions.service import TendersAuctionsService
from app.domains.tenders_auctions.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/tenders-auctions", tags=["Sovereign Tenders & Auctions"])


# ========== المناقصات ==========
@router.post("/tenders", response_model=TenderResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_tender(
    data: TenderCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    user_id = cast(int, current_user.id)
    tender = await service.create_tender(user_id, cast(int, tenant.id), data.model_dump())  # ✅ cast
    return tender


@router.post("/bids", response_model=TenderBidResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=20, window_seconds=60)
async def submit_bid(
    data: TenderBidCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    user_id = cast(int, current_user.id)
    bid = await service.submit_bid(user_id, cast(int, tenant.id), data.model_dump(), idempotency_key)  # ✅ cast
    return bid


@router.post("/bids/{bid_id}/evaluate", response_model=TenderBidResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def evaluate_bid(
    bid_id: int,
    data: TenderBidEvaluate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    user_id = cast(int, current_user.id)
    bid = await service.evaluate_bid_technically(user_id, cast(int, tenant.id), bid_id, data.technical_score, idempotency_key)  # ✅ cast
    return bid


# ========== المزادات ==========
@router.post("/auctions", response_model=AuctionResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_auction(
    data: AuctionCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    user_id = cast(int, current_user.id)
    auction = await service.create_auction(user_id, cast(int, tenant.id), data.model_dump())  # ✅ cast
    return auction


@router.post("/auctions/{auction_id}/bids", response_model=LiveBidResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def place_bid(
    auction_id: int,
    data: LiveBidCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    user_id = cast(int, current_user.id)
    bid = await service.place_bid(user_id, cast(int, tenant.id), auction_id, data.bid_amount_mrusdt, idempotency_key)  # ✅ cast
    return bid


@router.post("/auctions/{auction_id}/close")
@rate_limit(max_requests=5, window_seconds=60)
async def close_auction(
    auction_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    user_id = cast(int, current_user.id)
    result = await service.close_auction(auction_id, user_id, cast(int, tenant.id))  # ✅ cast
    return result