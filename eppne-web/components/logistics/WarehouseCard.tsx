// components/logistics/WarehouseCard.tsx
'use client';

import { Building2, MapPin, Package, Users, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Warehouse } from '@/types/logistics';

export default function WarehouseCard({ warehouse, onClick }: { warehouse: Warehouse; onClick?: () => void }) {
  const usage = warehouse.total_capacity_units > 0
    ? (warehouse.used_capacity_units / warehouse.total_capacity_units) * 100
    : 0;

  return (
    <div
      onClick={onClick}
      className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all cursor-pointer"
    >
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">{warehouse.name}</h4>
          <p className="text-sm text-muted-foreground/60">{warehouse.warehouse_type}</p>
        </div>
        <span className={cn(
          "text-xs px-2 py-0.5 rounded-full border",
          warehouse.is_active ? "border-emerald-500/30 text-emerald-500" : "border-red-500/30 text-red-500"
        )}>
          {warehouse.is_active ? 'نشط' : 'غير نشط'}
        </span>
      </div>
      <div className="mt-2 space-y-1 text-xs text-muted-foreground/50">
        <div className="flex items-center gap-2">
          <MapPin className="w-3 h-3" />
          {warehouse.location}
        </div>
        <div className="flex items-center gap-2">
          <Package className="w-3 h-3" />
          {warehouse.used_capacity_units} / {warehouse.total_capacity_units} وحدة
        </div>
        <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-primary to-secondary transition-all duration-1000"
            style={{ width: `${Math.min(usage, 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}