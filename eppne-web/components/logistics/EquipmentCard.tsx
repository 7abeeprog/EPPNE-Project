// components/logistics/EquipmentCard.tsx
'use client';

import { Wrench, MapPin, Calendar, DollarSign } from 'lucide-react';
import { format } from 'date-fns/ar';
import { cn } from '@/lib/utils';
import type { Equipment } from '@/types/logistics';

const statusColors: Record<string, string> = {
  AVAILABLE: 'border-emerald-500/30 text-emerald-500',
  IN_USE: 'border-blue-500/30 text-blue-500',
  MAINTENANCE: 'border-amber-500/30 text-amber-500',
  DAMAGED: 'border-red-500/30 text-red-500',
  RETIRED: 'border-gray-500/30 text-gray-400',
};

export default function EquipmentCard({ equipment, onClick }: { equipment: Equipment; onClick?: () => void }) {
  return (
    <div
      onClick={onClick}
      className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all cursor-pointer"
    >
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">{equipment.name}</h4>
          <p className="text-sm text-muted-foreground/60">{equipment.equipment_type}</p>
        </div>
        <span className={cn("text-xs px-2 py-0.5 rounded-full border", statusColors[equipment.status] || 'border-white/10')}>
          {equipment.status}
        </span>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-1 text-xs text-muted-foreground/50">
        {equipment.serial_number && (
          <div className="flex items-center gap-2 col-span-2">
            <Wrench className="w-3 h-3" />
            {equipment.serial_number}
          </div>
        )}
        {equipment.warehouse_name && (
          <div className="flex items-center gap-2 col-span-2">
            <MapPin className="w-3 h-3" />
            {equipment.warehouse_name}
          </div>
        )}
        {equipment.next_maintenance_date && (
          <div className="flex items-center gap-2 col-span-2">
            <Calendar className="w-3 h-3" />
            الصيانة القادمة: {format(new Date(equipment.next_maintenance_date), 'dd/MM/yyyy')}
          </div>
        )}
        {equipment.purchase_price_mrusdt > 0 && (
          <div className="flex items-center gap-2">
            <DollarSign className="w-3 h-3" />
            {equipment.purchase_price_mrusdt} MR_USDT
          </div>
        )}
      </div>
    </div>
  );
}