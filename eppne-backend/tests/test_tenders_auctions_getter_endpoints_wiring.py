"""
regression test لجلسة `frontend-category-b-phase2-remaining-domains` (2026-09-02).
تقرير الجلسة: .claude/reports/frontend-category-b-phase2-session-log.md

السياق: `TendersAuctionsRepository` كانت تملك get_tender, list_tenders,
update_tender, list_bids_for_tender, get_auction, list_auctions,
get_live_bids_for_auction جاهزة بالكامل بدون service wrapper ولا router
endpoint، وupdate_tender/update_auction العامتين استُخدِمتا لبناء
open_tender/start_auction كعمليتي نقل حالة مخصَّصتين (بنفس نمط
close_auction الموجود بالفعل). هذا الاختبار يتحقق حيًا (DB حقيقية) من
كل الإضافات، بما فيها تحقق عزل tenant_id.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timedelta

import pytest
from sqlalchemy import delete

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.core.errors import NotFoundError, PermissionDeniedError

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.tenders_auctions.service import TendersAuctionsService
from app.domains.tenders_auctions.repository import TendersAuctionsRepository
from app.domains.tenders_auctions.models import (
    SovereignTender, TenderBid, SovereignAuction, LiveBid,
    TenderStatus, AuctionStatus,
)

TENANT_ID = 1
OTHER_TENANT_ID = 2


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


@pytest.mark.asyncio
async def test_tender_get_update_open_and_bids(db):
    creator = await _create_user(db, "p_regtest_ta_tender_creator")
    bidder = await _create_user(db, "p_regtest_ta_tender_bidder")
    repo = TendersAuctionsRepository(db)
    tender = await repo.create_tender(
        tenant_id=TENANT_ID, created_by=creator.id, title=f"REGTEST-TENDER-{_suffix()}",
        description="REGTEST", scope_of_work={}, estimated_budget_mrusdt=Decimal("1000"),
        submission_start=datetime.utcnow(), submission_deadline=datetime.utcnow() + timedelta(days=1),
        status=TenderStatus.DRAFT,
    )
    bid = await repo.create_bid(
        tenant_id=TENANT_ID, tender_id=tender.id, bidder_id=bidder.id,
        technical_envelope={}, encrypted_financial_envelope="enc",
    )
    tender_id, bid_id = tender.id, bid.id

    service = TendersAuctionsService(db)
    try:
        result = await service.get_tender(tender_id, TENANT_ID)
        assert result.id == tender_id

        with pytest.raises(NotFoundError):
            await service.get_tender(tender_id, OTHER_TENANT_ID)

        listed = await service.list_tenders(TENANT_ID)
        assert any(t.id == tender_id for t in listed)
        listed_other_tenant = await service.list_tenders(OTHER_TENANT_ID)
        assert not any(t.id == tender_id for t in listed_other_tenant)

        updated = await service.update_tender(tender_id, TENANT_ID, {"title": "REGTEST-UPDATED"})
        assert updated.title == "REGTEST-UPDATED"

        bids = await service.get_tender_bids(tender_id, TENANT_ID)
        assert any(b.id == bid_id for b in bids)

        opened = await service.open_tender(tender_id, TENANT_ID)
        assert opened.status == TenderStatus.PUBLISHED

        with pytest.raises(PermissionDeniedError):
            await service.open_tender(tender_id, TENANT_ID)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(TenderBid).where(TenderBid.id == bid_id))
            await cleanup_db.execute(delete(SovereignTender).where(SovereignTender.id == tender_id))
            await cleanup_db.execute(delete(User).where(User.id.in_([creator.id, bidder.id])))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_auction_get_start_and_bids(db):
    creator = await _create_user(db, "p_regtest_ta_auction_creator")
    bidder = await _create_user(db, "p_regtest_ta_auction_bidder")
    repo = TendersAuctionsRepository(db)
    auction = await repo.create_auction(
        tenant_id=TENANT_ID, created_by=creator.id, title=f"REGTEST-AUCTION-{_suffix()}",
        asset_type="LAND", start_price_mrusdt=Decimal("100"),
        start_time=datetime.utcnow(), end_time=datetime.utcnow() + timedelta(days=1),
        status=AuctionStatus.DRAFT,
    )
    live_bid = await repo.create_live_bid(
        tenant_id=TENANT_ID, auction_id=auction.id, bidder_id=bidder.id, bid_amount_mrusdt=Decimal("150"),
    )
    auction_id, live_bid_id = auction.id, live_bid.id

    service = TendersAuctionsService(db)
    try:
        result = await service.get_auction(auction_id, TENANT_ID)
        assert result.id == auction_id

        with pytest.raises(NotFoundError):
            await service.get_auction(auction_id, OTHER_TENANT_ID)

        listed = await service.list_auctions(TENANT_ID)
        assert any(a.id == auction_id for a in listed)
        listed_other_tenant = await service.list_auctions(OTHER_TENANT_ID)
        assert not any(a.id == auction_id for a in listed_other_tenant)

        bids = await service.get_auction_bids(auction_id, TENANT_ID)
        assert any(b.id == live_bid_id for b in bids)

        started = await service.start_auction(auction_id, TENANT_ID)
        assert started.status == AuctionStatus.OPEN

        with pytest.raises(PermissionDeniedError):
            await service.start_auction(auction_id, TENANT_ID)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(LiveBid).where(LiveBid.id == live_bid_id))
            await cleanup_db.execute(delete(SovereignAuction).where(SovereignAuction.id == auction_id))
            await cleanup_db.execute(delete(User).where(User.id.in_([creator.id, bidder.id])))
            await cleanup_db.commit()
