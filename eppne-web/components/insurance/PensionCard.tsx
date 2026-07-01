// components/insurance/PensionCard.tsx
'use client';

import { DollarSign, Calendar, User, CheckCircle, XCircle } from 'lucide-react';
import { format } from 'date-fns/ar';
import { cn } from '@/lib/utils';
import type { PensionRecord } from '@/types/insurance';

export default function PensionCard({ pension }: { pension: PensionRecord }) {
  const isActive = pension.status === 'ACTIVE';

  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">{pension.pension_type}</h4>
          <p className="text-sm text-muted-foreground/60">
            <User className="w-3 h-3 inline mr-1" />
            المستفيد: {pension.beneficiary_name || `#${pension.beneficiary_id}`}
          </p>
        </div>
        <span className={cn(
          "text-xs px-2 py-0.5 rounded-full border",
          isActive ? "border-emerald-500/30 text-emerald-500" : "border-red-500/30 text-red-500"
        )}>
          {isActive ? 'نشط' : pension.status}
        </span>
      </div>
      <div className="mt-2 space-y-1 text-xs text-muted-foreground/50">
        <div className="flex items-center gap-2">
          <DollarSign className="w-3 h-3" />
          المبلغ الشهري: {pension.monthly_amount_mrusdt} MR_USDT
        </div>
        <div className="flex items-center gap-2">
          <DollarSign className="w-3 h-3" />
          الإجمالي المصروف: {pension.total_disbursed_mrusdt} MR_USDT
        </div>
        <div className="flex items-center gap-2">
          <Calendar className="w-3 h-3" />
          {format(new Date(pension.start_date), 'dd/MM/yyyy')}
          {pension.end_date && ` - ${format(new Date(pension.end_date), 'dd/MM/yyyy')}`}
        </div>
      </div>
    </div>
  );
}