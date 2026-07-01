// components/tenders-auctions/LiveBidCard.tsx
'use client';

import { format } from 'date-fns/ar';
import { Crown } from 'lucide-react';
import type { LiveBid } from '@/types/tenders-auctions';

interface LiveBidCardProps {
  bid: LiveBid;
  isHighest?: boolean;
}

export default function LiveBidCard({ bid, isHighest = false }: LiveBidCardProps) {
  return (
    <div className={cn(
      "flex items-center justify-between p-3 rounded-xl border transition-all",
      isHighest ? "border-emerald-500/30 bg-emerald-500/5" : "border-white/5 bg-white/5"
    )}>
      <div className="flex items-center gap-3">
        {isHighest && <Crown className="w-4 h-4 text-emerald-500" />}
        <div>
          <p className="text-sm font-medium text-foreground/80">
            {bid.bidder_name || `المستخدم #${bid.bidder_id}`}
          </p>
          <p className="text-xs text-muted-foreground/50">
            {format(new Date(bid.created_at), 'HH:mm:ss')}
          </p>
        </div>
      </div>
      <div className="text-right">
        <p className="text-lg font-bold text-primary">{bid.bid_amount_mrusdt} MR_USDT</p>
        {bid.bid_tx_hash && (
          <p className="text-[10px] text-muted-foreground/30 font-mono truncate max-w-[100px]">
            {bid.bid_tx_hash.slice(0, 10)}...
          </p>
        )}
      </div>
    </div>
  );
}