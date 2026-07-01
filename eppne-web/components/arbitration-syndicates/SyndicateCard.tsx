// components/arbitration-syndicates/SyndicateCard.tsx
'use client';

import { Building2, Users, DollarSign, Shield } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SovereignSyndicate } from '@/types/arbitration-syndicates';

const typeLabels: Record<string, string> = {
  PROFESSIONAL: 'نقابة مهنية',
  TRADE: 'غرفة تجارية',
  LABOR: 'نقابة عمالية',
  COMMUNITY: 'نقابة مجتمعية',
};

export default function SyndicateCard({ syndicate, onJoin }: { syndicate: SovereignSyndicate; onJoin?: () => void }) {
  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">{syndicate.name}</h4>
          <p className="text-sm text-muted-foreground/60">{typeLabels[syndicate.syndicate_type]}</p>
          {syndicate.description && (
            <p className="text-xs text-muted-foreground/50 mt-1 line-clamp-2">{syndicate.description}</p>
          )}
        </div>
        <Shield className="w-5 h-5 text-primary/60" />
      </div>
      <div className="mt-2 space-y-1 text-xs text-muted-foreground/50">
        <div className="flex items-center gap-2">
          <Users className="w-3 h-3" />
          {syndicate.member_count || 0} عضو
        </div>
        {syndicate.annual_fee_mrusdt > 0 && (
          <div className="flex items-center gap-2">
            <DollarSign className="w-3 h-3" />
            الرسوم السنوية: {syndicate.annual_fee_mrusdt} MR_USDT
          </div>
        )}
        <div className="flex items-center gap-2">
          <Building2 className="w-3 h-3" />
          {syndicate.is_active ? 'نشطة' : 'غير نشطة'}
        </div>
      </div>
      {!syndicate.is_member && syndicate.is_active && onJoin && (
        <button
          onClick={onJoin}
          className="mt-3 w-full px-3 py-1.5 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors text-sm"
        >
          انضمام
        </button>
      )}
      {syndicate.is_member && (
        <div className="mt-3 text-xs text-emerald-500/70 flex items-center gap-1">
          <Shield className="w-3 h-3" />
          عضو نشط
        </div>
      )}
    </div>
  );
}