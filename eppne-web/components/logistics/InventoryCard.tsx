// components/logistics/InventoryCard.tsx
'use client';

import { Package, DollarSign, Calendar, Box } from 'lucide-react';
import { format } from 'date-fns/ar';
import InventoryStatusBadge from './InventoryStatusBadge';
import type { InventoryItem } from '@/types/logistics';

export default function InventoryCard({ item, onClick }: { item: InventoryItem; onClick?: () => void }) {
  const isLowStock = item.quantity <= item.min_stock_threshold;
  const isExpired = item.expiry_date && new Date(item.expiry_date) < new Date();

  return (
    <div
      onClick={onClick}
      className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all cursor-pointer"
    >
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">{item.product_name}</h4>
          <p className="text-sm text-muted-foreground/60">{item.product_sku || 'بدون SKU'}</p>
        </div>
        <InventoryStatusBadge status={item.status} />
      </div>
      <div className="mt-2 grid grid-cols-2 gap-1 text-xs text-muted-foreground/50">
        <div className="flex items-center gap-2">
          <Package className="w-3 h-3" />
          {item.quantity} {item.unit}
        </div>
        <div className="flex items-center gap-2">
          <DollarSign className="w-3 h-3" />
          {item.unit_price_mrusdt} MR_USDT
        </div>
        {item.batch_number && (
          <div className="flex items-center gap-2 col-span-2">
            <Box className="w-3 h-3" />
            دفعة: {item.batch_number}
          </div>
        )}
        {item.expiry_date && (
          <div className="flex items-center gap-2 col-span-2">
            <Calendar className="w-3 h-3" />
            {format(new Date(item.expiry_date), 'dd/MM/yyyy')}
            {isExpired && <span className="text-red-500"> (منتهي)</span>}
          </div>
        )}
        {isLowStock && (
          <div className="col-span-2 text-amber-500 text-[10px]">⚠️ مخزون منخفض</div>
        )}
      </div>
    </div>
  );
}