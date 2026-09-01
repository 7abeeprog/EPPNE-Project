// components/zamakana/PledgeCard.tsx
'use client';

import { Clock, User, CheckCircle, XCircle } from 'lucide-react';
import { format } from 'date-fns';
import { ar } from 'date-fns/locale';
import { cn } from '@/lib/utils';
import type { TimePledge } from '@/types/zamakana';

export default function PledgeCard({ pledge }: { pledge: TimePledge }) {
  const isFulfilled = pledge.status === 'FULFILLED';
  const isCancelled = pledge.status === 'CANCELLED';

  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2 text-sm text-foreground/80">
          <User className="w-4 h-4 text-muted-foreground/50" />
          {pledge.user_name || `مستخدم #${pledge.user_id}`}
        </div>
        <span className={cn(
          "text-xs px-2 py-0.5 rounded-full border flex items-center gap-1",
          isFulfilled ? "border-emerald-500/30 text-emerald-500" :
          isCancelled ? "border-red-500/30 text-red-500" :
          "border-blue-500/30 text-blue-500"
        )}>
          {isFulfilled ? <CheckCircle className="w-3 h-3" /> : isCancelled ? <XCircle className="w-3 h-3" /> : null}
          {isFulfilled ? 'مُنجَز' : isCancelled ? 'مُلغى' : 'معلَّق'}
        </span>
      </div>
      <div className="mt-2 space-y-1 text-xs text-muted-foreground/50">
        <div className="flex items-center gap-2">
          <Clock className="w-3 h-3" />
          {pledge.pledged_hours} ساعة
          {pledge.skill_category && <span>· {pledge.skill_category}</span>}
        </div>
        <div>{format(new Date(pledge.created_at), 'dd/MM/yyyy', { locale: ar })}</div>
      </div>
    </div>
  );
}
