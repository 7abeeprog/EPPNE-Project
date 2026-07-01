// components/tenders-auctions/PlaceBidModal.tsx
'use client';

import { useState } from 'react';
import { usePlaceBid } from '@/hooks/tenders-auctions/useLiveBids';
import { X, Loader2, Gavel, DollarSign } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';

interface PlaceBidModalProps {
  isOpen: boolean;
  onClose: () => void;
  auctionId: number;
  currentHighest: number;
  minIncrement: number;
}

export default function PlaceBidModal({ isOpen, onClose, auctionId, currentHighest, minIncrement }: PlaceBidModalProps) {
  const [amount, setAmount] = useState(currentHighest + minIncrement);
  const placeBid = usePlaceBid();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const idempotencyKey = `bid-${auctionId}-${uuidv4()}`;
    placeBid.mutate(
      {
        auctionId,
        data: { bid_amount_mrusdt: amount },
        idempotencyKey,
      },
      {
        onSuccess: () => {
          onClose();
        },
      }
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200 p-4">
      <div className="relative w-full max-w-md p-6 rounded-3xl bg-card/80 backdrop-blur-3xl border border-white/15 shadow-[0_20px_80px_-20px_rgba(0,0,0,0.6)] animate-in zoom-in-95 duration-200">
        <button onClick={onClose} className="absolute top-3 right-3 p-1 rounded-lg hover:bg-white/10 transition-colors">
          <X className="w-4 h-4 text-muted-foreground/60" />
        </button>

        <h3 className="text-lg font-bold text-foreground/90 flex items-center gap-2">
          <Gavel className="w-5 h-5 text-primary" />
          وضع مزايدة
        </h3>

        <div className="mt-2 text-sm text-muted-foreground/60">
          أعلى عرض حالياً: <span className="text-foreground/80 font-medium">{currentHighest} MR_USDT</span>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="text-sm text-muted-foreground/60">مبلغ المزايدة (MR_USDT)</label>
            <div className="relative mt-1">
              <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/50" />
              <input
                type="number"
                step="0.01"
                min={currentHighest + minIncrement}
                value={amount}
                onChange={(e) => setAmount(parseFloat(e.target.value) || 0)}
                className="w-full pl-9 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                required
              />
            </div>
            <p className="text-xs text-muted-foreground/40 mt-1">الحد الأدنى: {currentHighest + minIncrement} MR_USDT</p>
          </div>

          <button
            type="submit"
            disabled={placeBid.isPending || amount < currentHighest + minIncrement}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
          >
            {placeBid.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Gavel className="w-4 h-4" />}
            تأكيد المزايدة
          </button>
        </form>
      </div>
    </div>
  );
}