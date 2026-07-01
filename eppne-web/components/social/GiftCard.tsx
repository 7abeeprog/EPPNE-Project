// components/social/GiftCard.tsx
'use client';

import { Gift, Wallet, Package, Check, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { DigitalGift, PhysicalGiftRequest } from '@/types/social';

interface GiftCardProps {
  gift: DigitalGift | PhysicalGiftRequest;
  type: 'digital' | 'physical';
}

export default function GiftCard({ gift, type }: GiftCardProps) {
  if (type === 'digital') {
    const digital = gift as DigitalGift;
    return (
      <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Wallet className="w-4 h-4 text-primary" />
              <h4 className="font-medium text-foreground/80">هدية رقمية</h4>
            </div>
            <p className="text-sm text-muted-foreground/60">
              من {digital.sender_name || `#${digital.sender_id}`} → {digital.receiver_name || `#${digital.receiver_id}`}
            </p>
            <p className="text-xs text-muted-foreground/40">{digital.gift_type}</p>
            {digital.gift_message && (
              <p className="text-xs text-muted-foreground/60 mt-1">💬 {digital.gift_message}</p>
            )}
          </div>
          <div className="text-right">
            {digital.gift_value_mrusdt > 0 && (
              <span className="text-primary font-medium">{digital.gift_value_mrusdt} MR_USDT</span>
            )}
            <p className={cn(
              "text-xs mt-1",
              digital.is_redeemed ? "text-emerald-500" : "text-amber-500"
            )}>
              {digital.is_redeemed ? <Check className="w-3 h-3 inline" /> : <Clock className="w-3 h-3 inline" />}
              {digital.is_redeemed ? 'تم الاستلام' : 'في الانتظار'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const physical = gift as PhysicalGiftRequest;
  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Package className="w-4 h-4 text-primary" />
            <h4 className="font-medium text-foreground/80">{physical.product_name}</h4>
          </div>
          <p className="text-sm text-muted-foreground/60">
            من {physical.sender_name || `#${physical.sender_id}`} → {physical.receiver_name || `#${physical.receiver_id}`}
          </p>
          {physical.order_tracking_number && (
            <p className="text-xs text-muted-foreground/40">تتبع: {physical.order_tracking_number}</p>
          )}
        </div>
        <div className="text-right">
          <span className="text-primary font-medium">{physical.product_price_mrusdt} MR_USDT</span>
          <p className={cn(
            "text-xs mt-1",
            physical.shipping_status === 'DELIVERED' ? "text-emerald-500" : "text-amber-500"
          )}>
            {physical.shipping_status === 'DELIVERED' ? '✅ تم التسليم' : `📦 ${physical.shipping_status}`}
          </p>
        </div>
      </div>
    </div>
  );
}