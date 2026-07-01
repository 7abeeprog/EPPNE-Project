// components/tenders-auctions/AuctionCard.tsx
'use client';

import { Clock, DollarSign, TrendingUp, Gavel } from 'lucide-react';
import { format } from 'date-fns/ar';
import { cn } from '@/lib/utils';
import type { SovereignAuction } from '@/types/tenders-auctions';

const statusColors: Record<string, string> = {
  SCHEDULED: 'border-blue-500/30 text-blue-500',
  LIVE: 'border-emerald-500/30 text-emerald-500 animate-pulse',
  CLOSED_WITH_WINNER: 'border-purple-500/30 text-purple-500',
  CLOSED_NO_WINNER: 'border-gray-500/30 text-gray-400',
  CANCELLED: 'border-red-500/30 text-red-500',
};

export default function AuctionCard({ auction }: { auction: SovereignAuction }) {
  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">{auction.title}</h4>
          <p className="text-sm text-muted-foreground/60 line-clamp-2">{auction.description}</p>
        </div>
        <span className={cn("text-xs px-2 py-0.5 rounded-full border", statusColors[auction.status] || 'border-white/10')}>
          {auction.status}
        </span>
      </div>
      <div className="mt-2 space-y-1 text-xs text-muted-foreground/50">
        <div className="flex items-center gap-2">
          <Clock className="w-3 h-3" />
          {format(new Date(auction.start_time), 'dd/MM/yyyy HH:mm')} - {format(new Date(auction.end_time), 'HH:mm')}
        </div>
        <div className="flex items-center gap-2">
          <DollarSign className="w-3 h-3" />
          البداية: {auction.starting_price_mrusdt} MR_USDT
        </div>
        <div className="flex items-center gap-2">
          <TrendingUp className="w-3 h-3" />
          الأعلى: {auction.current_highest_bid_mrusdt} MR_USDT
        </div>
        <div className="flex items-center gap-2">
          <Gavel className="w-3 h-3" />
          {auction.asset_type} #{auction.asset_id}
        </div>
      </div>
    </div>
  );
}