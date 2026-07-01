// components/insurance/PolicyCard.tsx
'use client';

import { Shield, DollarSign, Calendar, Building2, CheckCircle, XCircle } from 'lucide-react';
import { format } from 'date-fns/ar';
import { cn } from '@/lib/utils';
import type { InsurancePolicy } from '@/types/insurance';

const policyTypeLabels: Record<string, string> = {
  MEDICAL: 'صحي',
  ACCIDENT: 'حوادث',
  LIFE: 'حياة',
  FLEET: 'أساطيل',
  CARGO: 'شحنات',
  PROJECT: 'مشاريع',
  EMPLOYEE_BENEFITS: 'تأمينات موظفين',
};

export default function PolicyCard({ policy, onSubscribe }: { policy: InsurancePolicy; onSubscribe?: () => void }) {
  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">{policy.name}</h4>
          <p className="text-sm text-muted-foreground/60 line-clamp-2">{policy.description}</p>
          <span className="text-xs px-2 py-0.5 rounded-full border-primary/30 text-primary bg-primary/5">
            {policyTypeLabels[policy.policy_type] || policy.policy_type}
          </span>
        </div>
        <div className="text-right">
          <Shield className="w-5 h-5 text-primary/60 mx-auto" />
          <span className={cn(
            "text-xs px-2 py-0.5 rounded-full border mt-1 block",
            policy.is_active ? "border-emerald-500/30 text-emerald-500" : "border-red-500/30 text-red-500"
          )}>
            {policy.is_active ? 'نشط' : 'غير نشط'}
          </span>
        </div>
      </div>
      <div className="mt-2 space-y-1 text-xs text-muted-foreground/50">
        <div className="flex items-center gap-2">
          <DollarSign className="w-3 h-3" />
          القسط: {policy.base_premium_mrusdt} MR_USDT
        </div>
        <div className="flex items-center gap-2">
          <DollarSign className="w-3 h-3" />
          الحد الأقصى: {policy.max_coverage_limit_mrusdt} MR_USDT
        </div>
        <div className="flex items-center gap-2">
          <Calendar className="w-3 h-3" />
          دورة: {policy.premium_cycle}
        </div>
        <div className="flex items-center gap-2">
          <Building2 className="w-3 h-3" />
          الجهة المصدرة: #{policy.issuer_entity_id}
        </div>
      </div>
      {policy.is_active && onSubscribe && (
        <button
          onClick={onSubscribe}
          className="mt-3 w-full px-3 py-1.5 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors text-sm"
        >
          اشتراك
        </button>
      )}
    </div>
  );
}