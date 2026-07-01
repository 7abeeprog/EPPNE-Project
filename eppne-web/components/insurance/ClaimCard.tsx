// components/insurance/ClaimCard.tsx
'use client';

import { AlertTriangle, DollarSign, Calendar, FileText, CheckCircle, XCircle, Clock } from 'lucide-react';
import { format } from 'date-fns/ar';
import { cn } from '@/lib/utils';
import type { InsuranceClaim } from '@/types/insurance';

const statusConfig: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  SUBMITTED: {
    label: 'مقدمة',
    color: 'border-amber-500/30 text-amber-500 bg-amber-500/5',
    icon: <Clock className="w-3.5 h-3.5" />,
  },
  UNDER_INVESTIGATION: {
    label: 'قيد التحقيق',
    color: 'border-blue-500/30 text-blue-500 bg-blue-500/5',
    icon: <Clock className="w-3.5 h-3.5 animate-pulse" />,
  },
  APPROVED: {
    label: 'معتمدة',
    color: 'border-emerald-500/30 text-emerald-500 bg-emerald-500/5',
    icon: <CheckCircle className="w-3.5 h-3.5" />,
  },
  REJECTED: {
    label: 'مرفوضة',
    color: 'border-red-500/30 text-red-500 bg-red-500/5',
    icon: <XCircle className="w-3.5 h-3.5" />,
  },
  PAID: {
    label: 'مدفوعة',
    color: 'border-purple-500/30 text-purple-500 bg-purple-500/5',
    icon: <DollarSign className="w-3.5 h-3.5" />,
  },
};

export default function ClaimCard({ claim }: { claim: InsuranceClaim }) {
  const config = statusConfig[claim.status] || statusConfig.SUBMITTED;

  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">مطالبة #{claim.id}</h4>
          <p className="text-sm text-muted-foreground/60 line-clamp-2">{claim.incident_description}</p>
        </div>
        <span className={cn("inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full border", config.color)}>
          {config.icon}
          {config.label}
        </span>
      </div>
      <div className="mt-2 space-y-1 text-xs text-muted-foreground/50">
        <div className="flex items-center gap-2">
          <DollarSign className="w-3 h-3" />
          المطالب به: {claim.claimed_amount_mrusdt} MR_USDT
        </div>
        {claim.approved_amount_mrusdt > 0 && (
          <div className="flex items-center gap-2 text-emerald-500">
            <CheckCircle className="w-3 h-3" />
            المعتمد: {claim.approved_amount_mrusdt} MR_USDT
          </div>
        )}
        <div className="flex items-center gap-2">
          <Calendar className="w-3 h-3" />
          {format(new Date(claim.incident_date), 'dd/MM/yyyy')}
        </div>
        {claim.evidence_urls.length > 0 && (
          <div className="flex items-center gap-2">
            <FileText className="w-3 h-3" />
            {claim.evidence_urls.length} مستند
          </div>
        )}
      </div>
    </div>
  );
}