// components/tenders-auctions/AuctionDetail.tsx
'use client';

import { useAuction } from '@/hooks/tenders-auctions/useAuctions';
import { useAuctionBids } from '@/hooks/tenders-auctions/useLiveBids';
import { useState } from 'react';
import { Loader2, Clock, DollarSign, Gavel, TrendingUp, Users } from 'lucide-react';
import { format } from 'date-fns/ar';
import { cn } from '@/lib/utils';
import PlaceBidModal from './PlaceBidModal';
import CloseAuctionModal from './CloseAuctionModal';
import LiveBidCard from './LiveBidCard';
import type { SovereignAuction } from '@/types/tenders-auctions';

interface AuctionDetailProps {
  auction: SovereignAuction;
  isOwner?: boolean;
}

const statusColors: Record<string, string> = {
  SCHEDULED: 'text-blue-500',
  LIVE: 'text-emerald-500 animate-pulse',
  CLOSED_WITH_WINNER: 'text-purple-500',
  CLOSED_NO_WINNER: 'text-gray-400',
  CANCELLED: 'text-red-500',
};

export default function AuctionDetail({ auction, isOwner = false }: AuctionDetailProps) {
  const [placeBidOpen, setPlaceBidOpen] = useState(false);
  const [closeModalOpen, setCloseModalOpen] = useState(false);
  const { data: bids, isLoading: bLoading } = useAuctionBids(auction.id);

  if (bLoading) {
    return <div className="flex justify-center items-center h-32"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;
  }

  return (
    <div className="space-y-6">
      <div className="p-6 rounded-3xl bg-card/20 backdrop-blur-2xl border border-white/10">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground/90">{auction.title}</h1>
            <p className="text-sm text-muted-foreground/60 mt-1">{auction.description}</p>
            <div className="flex flex-wrap gap-4 mt-2 text-sm text-muted-foreground/50">
              <span className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                {format(new Date(auction.start_time), 'dd/MM/yyyy HH:mm')} - {format(new Date(auction.end_time), 'HH:mm')}
              </span>
              <span className="flex items-center gap-1">
                <DollarSign className="w-4 h-4" />
                البداية: {auction.starting_price_mrusdt} MR_USDT
              </span>
              <span className="flex items-center gap-1">
                <TrendingUp className="w-4 h-4" />
                الأعلى: {auction.current_highest_bid_mrusdt} MR_USDT
              </span>
              <span className="flex items-center gap-1">
                <Users className="w-4 h-4" />
                {bids?.length || 0} مزايدة
              </span>
            </div>
          </div>
          <div className="text-right">
            <span className={cn("text-sm font-medium", statusColors[auction.status] || 'text-muted-foreground')}>
              {auction.status}
            </span>
            {auction.status === 'LIVE' && !isOwner && (
              <button
                onClick={() => setPlaceBidOpen(true)}
                className="mt-2 block px-4 py-2 rounded-xl bg-emerald-500 text-white text-sm font-medium shadow-[0_0_30px_rgba(52,211,153,0.3)] hover:shadow-[0_0_50px_rgba(52,211,153,0.5)] transition-all duration-300"
              >
                وضع مزايدة
              </button>
            )}
            {(auction.status === 'LIVE' || auction.status === 'SCHEDULED') && isOwner && (
              <button
                onClick={() => setCloseModalOpen(true)}
                className="mt-2 block px-4 py-2 rounded-xl bg-red-500/20 text-red-500 border border-red-500/30 hover:bg-red-500/30 transition-colors text-sm"
              >
                إغلاق المزاد
              </button>
            )}
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-foreground/80 mb-3">📊 المزايدات</h3>
        {bids?.length === 0 ? (
          <p className="text-muted-foreground/60 text-center py-8">لا توجد مزايدات بعد</p>
        ) : (
          <div className="space-y-2">
            {bids?.map((bid, idx) => (
              <LiveBidCard key={bid.id} bid={bid} isHighest={idx === 0} />
            ))}
          </div>
        )}
      </div>

      <PlaceBidModal
        isOpen={placeBidOpen}
        onClose={() => setPlaceBidOpen(false)}
        auctionId={auction.id}
        currentHighest={auction.current_highest_bid_mrusdt}
        minIncrement={auction.minimum_increment_mrusdt}
      />
      <CloseAuctionModal
        isOpen={closeModalOpen}
        onClose={() => setCloseModalOpen(false)}
        auctionId={auction.id}
      />
    </div>
  );
}