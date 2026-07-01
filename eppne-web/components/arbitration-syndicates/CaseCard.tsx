// components/arbitration-syndicates/CaseCard.tsx
'use client';

import { Scale, User, Calendar, AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import { format } from 'date-fns/ar';
import { cn } from '@/lib/utils';
import type { ArbitrationCase } from '@/types/arbitration-syndicates';

const statusConfig: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  OPEN: {
    label: 'مفتوحة',
    color: 'border-amber-500/30 text-amber-500 bg-amber-500/5',
    icon: <AlertTriangle className="w-3.5 h-3.5" />,
  },
  IN_REVIEW: {
    label: 'قيد المراجعة',
    color: 'border-blue-500/30 text-blue-500 bg-blue-500/5',
    icon: <Clock className="w-3.5 h-3.5 animate-pulse" />,
  },
  RESOLVED: {
    label: 'محلولة',
    color: 'border-emerald-500/30 text-emerald-500 bg-emerald-500/5',
    icon: <CheckCircle className="w-3.5 h-3.5" />,
  },
  APPEALED: {
    label: 'مستأنفة',
    color: 'border-purple-500/30 text-purple-500 bg-purple-500/5',
    icon: <Scale className="w-3.5 h-3.5" />,
  },
};

export default function CaseCard({ caseItem }: { caseItem: ArbitrationCase }) {
  const config = statusConfig[caseItem.status] || statusConfig.OPEN;

  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">قضية #{caseItem.id}</h4>
          <p className="text-sm text-muted-foreground/60 line-clamp-2">{caseItem.dispute_reason}</p>
          <div className="flex flex-wrap gap-3 mt-1 text-xs text-muted-foreground/50">
            <span className="flex items-center gap-1">
              <User className="w-3 h-3" />
              المدعي: {caseItem.claimant_name || `#${caseItem.claimant_id}`}
            </span>
            <span className="flex items-center gap-1">
              <User className="w-3 h-3" />
              المدعى عليه: {caseItem.respondent_name || `#${caseItem.respondent_id}`}
            </span>
            <span className="flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              {format(new Date(caseItem.created_at), 'dd/MM/yyyy')}
            </span>
          </div>
        </div>
        <span className={cn("inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full border", config.color)}>
          {config.icon}
          {config.label}
        </span>
      </div>
    </div>
  );
}