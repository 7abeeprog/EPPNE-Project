"""
مستودع قطاع المزايدات والمناقصات (تم تصحيح التوافق مع النماذج)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

from app.domains.tenders_auctions.models import (
    SovereignTender, TenderBid, SovereignAuction, LiveBid,
    TenderStatus, BidStatus, AuctionStatus
)
from app.core.errors import NotFoundError


class TendersAuctionsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ========== Tenders ==========
    async def create_tender(self, **kwargs) -> SovereignTender:
        tender = SovereignTender(**kwargs)
        self.db.add(tender)
        await self.db.commit()
        await self.db.refresh(tender)
        return tender

    async def get_tender(self, tender_id: int) -> Optional[SovereignTender]:
        result = await self.db.execute(
            select(SovereignTender).where(SovereignTender.id == tender_id, SovereignTender.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def list_tenders(
        self,
        tenant_id: int,
        status: Optional[TenderStatus] = None,
        project_id: Optional[int] = None,  # تم التعديل من entity_id إلى project_id
        skip: int = 0,
        limit: int = 50
    ) -> List[SovereignTender]:
        query = select(SovereignTender).where(SovereignTender.tenant_id == tenant_id, SovereignTender.is_deleted == False)
        if status:
            query = query.where(SovereignTender.status == status)
        if project_id:
            query = query.where(SovereignTender.project_id == project_id)
        query = query.order_by(SovereignTender.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_tender(self, tender_id: int, **kwargs) -> SovereignTender:
        await self.db.execute(update(SovereignTender).where(SovereignTender.id == tender_id).values(**kwargs))
        await self.db.commit()
        tender = await self.get_tender(tender_id)
        if not tender:
            raise NotFoundError("Tender not found")
        return tender

    async def delete_tender(self, tender_id: int, soft: bool = True) -> None:
        if soft:
            await self.db.execute(
                update(SovereignTender).where(SovereignTender.id == tender_id).values(is_deleted=True, deleted_at=func.now())
            )
        else:
            await self.db.execute(delete(SovereignTender).where(SovereignTender.id == tender_id))
        await self.db.commit()

    # ========== Tender Bids ==========
    async def create_bid(self, **kwargs) -> TenderBid:
        bid = TenderBid(**kwargs)
        self.db.add(bid)
        await self.db.commit()
        await self.db.refresh(bid)
        return bid

    async def get_bid(self, bid_id: int) -> Optional[TenderBid]:
        result = await self.db.execute(select(TenderBid).where(TenderBid.id == bid_id))
        return result.scalar_one_or_none()

    async def get_bid_by_tender_and_bidder(self, tender_id: int, bidder_id: int) -> Optional[TenderBid]:
        result = await self.db.execute(
            select(TenderBid).where(TenderBid.tender_id == tender_id, TenderBid.bidder_id == bidder_id)
        )
        return result.scalar_one_or_none()

    async def list_bids_for_tender(self, tender_id: int, status: Optional[BidStatus] = None) -> List[TenderBid]:
        query = select(TenderBid).where(TenderBid.tender_id == tender_id)
        if status:
            query = query.where(TenderBid.status == status)
        query = query.order_by(TenderBid.created_at)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_bid(self, bid_id: int, **kwargs) -> TenderBid:
        await self.db.execute(update(TenderBid).where(TenderBid.id == bid_id).values(**kwargs))
        await self.db.commit()
        return await self.get_bid(bid_id)

    # ========== Auctions ==========
    async def create_auction(self, **kwargs) -> SovereignAuction:
        auction = SovereignAuction(**kwargs)
        self.db.add(auction)
        await self.db.commit()
        await self.db.refresh(auction)
        return auction

    async def get_auction(self, auction_id: int) -> Optional[SovereignAuction]:
        result = await self.db.execute(
            select(SovereignAuction).where(SovereignAuction.id == auction_id, SovereignAuction.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def list_auctions(
        self,
        tenant_id: int,
        status: Optional[AuctionStatus] = None,
        asset_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[SovereignAuction]:
        query = select(SovereignAuction).where(SovereignAuction.tenant_id == tenant_id, SovereignAuction.is_deleted == False)
        if status:
            query = query.where(SovereignAuction.status == status)
        if asset_type:
            query = query.where(SovereignAuction.asset_type == asset_type)
        query = query.order_by(SovereignAuction.start_time).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_auction(self, auction_id: int, **kwargs) -> SovereignAuction:
        await self.db.execute(update(SovereignAuction).where(SovereignAuction.id == auction_id).values(**kwargs))
        await self.db.commit()
        return await self.get_auction(auction_id)

    # تم تصحيح دالة الإغلاق لتتوافق مع الـ Enum والحقول الموجودة
    async def close_auction(self, auction_id: int, has_winner: bool, winning_bid_id: Optional[int] = None) -> SovereignAuction:
        status = AuctionStatus.SOLD if has_winner else AuctionStatus.CLOSED
        values = {"status": status}
        if winning_bid_id:
            values["winning_bid_id"] = winning_bid_id
        await self.db.execute(update(SovereignAuction).where(SovereignAuction.id == auction_id).values(**values))
        await self.db.commit()
        return await self.get_auction(auction_id)

    # ========== Live Bids ==========
    async def create_live_bid(self, **kwargs) -> LiveBid:
        bid = LiveBid(**kwargs)
        self.db.add(bid)
        await self.db.commit()
        await self.db.refresh(bid)
        return bid

    async def get_live_bids_for_auction(self, auction_id: int, limit: int = 100) -> List[LiveBid]:
        result = await self.db.execute(
            select(LiveBid).where(LiveBid.auction_id == auction_id)
            .order_by(LiveBid.created_at.desc()).limit(limit)
        )
        return result.scalars().all()