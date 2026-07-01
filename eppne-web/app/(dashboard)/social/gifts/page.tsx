// app/(dashboard)/social/gifts/page.tsx
'use client';

import { useDigitalGifts, usePhysicalGifts } from '@/hooks/social/useGifts';
import { Loader2, Gift, Package, Wallet } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function GiftsPage() {
  const { data: digitalGifts, isLoading: dLoading } = useDigitalGifts();
  const { data: physicalGifts, isLoading: pLoading } = usePhysicalGifts();

  if (dLoading || pLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-foreground/90">🎁 الهدايا</h1>

      {/* الهدايا الرقمية */}
      <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <h3 className="text-sm font-medium text-foreground/70 flex items-center gap-2 mb-3">
          <Wallet className="w-4 h-4 text-primary" />
          الهدايا الرقمية
        </h3>
        {digitalGifts?.length === 0 ? (
          <p className="text-center text-muted-foreground/50 text-sm py-4">لا توجد هدايا رقمية</p>
        ) : (
          <div className="space-y-2">
            {digitalGifts?.map((gift) => (
              <div key={gift.id} className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10">
                <div>
                  <p className="text-sm font-medium text-foreground/80">
                    من {gift.sender_name || `#${gift.sender_id}`} → {gift.receiver_name || `#${gift.receiver_id}`}
                  </p>
                  <p className="text-xs text-muted-foreground/50">{gift.gift_type}</p>
                  {gift.gift_message && <p className="text-xs text-muted-foreground/60 mt-1">💬 {gift.gift_message}</p>}
                </div>
                <div className="text-right">
                  {gift.gift_value_mrusdt > 0 && (
                    <span className="text-primary text-sm font-medium">{gift.gift_value_mrusdt} MR_USDT</span>
                  )}
                  <p className="text-xs text-muted-foreground/30">
                    {gift.is_redeemed ? '✅ تم الاستلام' : '⏳ في الانتظار'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* الهدايا الملموسة */}
      <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <h3 className="text-sm font-medium text-foreground/70 flex items-center gap-2 mb-3">
          <Package className="w-4 h-4 text-primary" />
          الهدايا الملموسة
        </h3>
        {physicalGifts?.length === 0 ? (
          <p className="text-center text-muted-foreground/50 text-sm py-4">لا توجد هدايا ملموسة</p>
        ) : (
          <div className="space-y-2">
            {physicalGifts?.map((gift) => (
              <div key={gift.id} className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10">
                <div>
                  <p className="text-sm font-medium text-foreground/80">
                    🛒 {gift.product_name}
                  </p>
                  <p className="text-xs text-muted-foreground/50">
                    من {gift.sender_name || `#${gift.sender_id}`} → {gift.receiver_name || `#${gift.receiver_id}`}
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-primary text-sm font-medium">{gift.product_price_mrusdt} MR_USDT</span>
                  <p className="text-xs text-muted-foreground/30">
                    {gift.shipping_status === 'DELIVERED' ? '✅ تم التسليم' : `📦 ${gift.shipping_status}`}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}