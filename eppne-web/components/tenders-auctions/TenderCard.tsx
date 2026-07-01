// components/tenders-auctions/TenderCard.tsx
'use client';

import { Calendar, DollarSign, Building2, FileText } from 'lucide-react';
import { format } from 'date-fns/ar';
import { cn } from '@/lib/utils';
import type { SovereignTender } from '@/types/tenders-auctions';

const statusColors: Record<string, string> = {
  DRAFT: 'border-gray-500/30 text-gray-400',
  OPEN: 'border-emerald-500/30 text-emerald-500',
  EVALUATING: 'border-amber-500/30 text-amber-500',
  AWARDED: 'border-blue-500/30 text-blue-500',
  CANCELLED: 'border-red-500/30 text-red-500',
};

export default function TenderCard({ tender }: { tender: SovereignTender }) {
  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">{tender.title}</h4>
          <p className="text-sm text-muted-foreground/60 line-clamp-2">{tender.description}</p>
        </div>
        <span className={cn("text-xs px-2 py-0.5 rounded-full border", statusColors[tender.status] || 'border-white/10')}>
          {tender.status}
        </span>
      </div>
      <div className="mt-2 space-y-1 text-xs text-muted-foreground/50">
        <div className="flex items-center gap-2">
          <Calendar className="w-3 h-3" />
          {format(new Date(tender.opening_date), 'dd/MM/yyyy')} - {format(new Date(tender.closing_date), 'dd/MM/yyyy')}
        </div>
        <div className="flex items-center gap-2">
          <DollarSign className="w-3 h-3" />
          التأمين: {tender.bid_bond_mrusdt} MR_USDT
        </div>
        <div className="flex items-center gap-2">
          <Building2 className="w-3 h-3" />
          الكيان: #{tender.entity_id}
        </div>
      </div>
    </div>
  );
}