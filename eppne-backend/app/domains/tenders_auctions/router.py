# app/domains/tenders_auctions/router.py
from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, cast

from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.domains.identity.models import User
from app.domains.tenders_auctions.service import TendersAuctionsService
from app.domains.tenders_auctions.schemas import *
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/tenders-auctions", tags=["Sovereign Tenders & Auctions"])


# ========== المناقصات ==========
@router.post("/tenders", response_model=TenderResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_tender(
    data: TenderCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    user_id = cast(int, current_user.id)
    tender = await service.create_tender(user_id, cast(int, current_user.tenant_id), data.model_dump())  # ✅ cast
    return tender


@router.get("/tenders", response_model=list[TenderResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_tenders(
    status_filter: Optional[str] = None,
    project_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    tenders = await service.list_tenders(cast(int, current_user.tenant_id), status_filter, project_id, skip, limit)
    return tenders


@router.get("/tenders/{tender_id}", response_model=TenderResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_tender(
    tender_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    tender = await service.get_tender(tender_id, cast(int, current_user.tenant_id))
    return tender


@router.patch("/tenders/{tender_id}", response_model=TenderResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_tender(
    tender_id: int,
    data: TenderUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    tender = await service.update_tender(
        tender_id, cast(int, current_user.tenant_id), data.model_dump(exclude_unset=True)
    )
    return tender


@router.post("/tenders/{tender_id}/open", response_model=TenderResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def open_tender(
    tender_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    tender = await service.open_tender(tender_id, cast(int, current_user.tenant_id))
    return tender


@router.get("/tenders/{tender_id}/bids", response_model=list[TenderBidResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_tender_bids(
    tender_id: int,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    bids = await service.get_tender_bids(tender_id, cast(int, current_user.tenant_id), status_filter)
    return bids


@router.post("/bids", response_model=TenderBidResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=20, window_seconds=60)
async def submit_bid(
    data: TenderBidCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    user_id = cast(int, current_user.id)
    bid = await service.submit_bid(user_id, cast(int, current_user.tenant_id), data.model_dump(), idempotency_key)  # ✅ cast
    return bid


@router.post("/bids/{bid_id}/evaluate", response_model=TenderBidResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def evaluate_bid(
    bid_id: int,
    data: TenderBidEvaluate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    user_id = cast(int, current_user.id)
    bid = await service.evaluate_bid_technically(user_id, cast(int, current_user.tenant_id), bid_id, data.technical_score, idempotency_key)  # ✅ cast
    return bid


# ========== المزادات ==========
@router.post("/auctions", response_model=AuctionResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_auction(
    data: AuctionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    user_id = cast(int, current_user.id)
    auction = await service.create_auction(user_id, cast(int, current_user.tenant_id), data.model_dump())  # ✅ cast
    return auction


@router.get("/auctions", response_model=list[AuctionResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_auctions(
    status_filter: Optional[str] = None,
    asset_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    auctions = await service.list_auctions(cast(int, current_user.tenant_id), status_filter, asset_type, skip, limit)
    return auctions


@router.get("/auctions/{auction_id}", response_model=AuctionResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_auction(
    auction_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    auction = await service.get_auction(auction_id, cast(int, current_user.tenant_id))
    return auction


@router.post("/auctions/{auction_id}/start", response_model=AuctionResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def start_auction(
    auction_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    auction = await service.start_auction(auction_id, cast(int, current_user.tenant_id))
    return auction


@router.get("/auctions/{auction_id}/bids", response_model=list[LiveBidResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_auction_bids(
    auction_id: int,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    bids = await service.get_auction_bids(auction_id, cast(int, current_user.tenant_id), limit)
    return bids


@router.post("/auctions/{auction_id}/bids", response_model=LiveBidResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def place_bid(
    auction_id: int,
    data: LiveBidCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    user_id = cast(int, current_user.id)
    bid = await service.place_bid(user_id, cast(int, current_user.tenant_id), auction_id, data.bid_amount_mrusdt, idempotency_key)  # ✅ cast
    return bid


@router.post("/auctions/{auction_id}/close")
@rate_limit(max_requests=5, window_seconds=60)
async def close_auction(
    auction_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TendersAuctionsService(db)
    user_id = cast(int, current_user.id)
    result = await service.close_auction(auction_id, user_id, cast(int, current_user.tenant_id))  # ✅ cast
    return result