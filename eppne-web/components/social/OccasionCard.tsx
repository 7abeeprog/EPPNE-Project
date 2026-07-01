// components/social/OccasionCard.tsx
'use client';

import { Calendar, Trash2, Globe, Lock } from 'lucide-react';
import { format } from 'date-fns/ar';
import { useDeleteOccasion } from '@/hooks/social/useOccasions';
import type { UserOccasion } from '@/types/social';

export default function OccasionCard({ occasion }: { occasion: UserOccasion }) {
  const deleteOccasion = useDeleteOccasion();

  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">{occasion.title || occasion.occasion_type}</h4>
          {occasion.description && (
            <p className="text-sm text-muted-foreground/60">{occasion.description}</p>
          )}
          <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground/50">
            <span className="flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              {format(new Date(occasion.occasion_date), 'dd/MM/yyyy')}
            </span>
            <span className="flex items-center gap-1">
              {occasion.is_public ? <Globe className="w-3 h-3" /> : <Lock className="w-3 h-3" />}
              {occasion.is_public ? 'عامة' : 'خاصة'}
            </span>
            <span>تذكير قبل {occasion.remind_days_before} يوم</span>
          </div>
        </div>
        <button
          onClick={() => deleteOccasion.mutate(occasion.id)}
          className="p-1.5 rounded-lg hover:bg-red-500/10 transition-colors"
        >
          <Trash2 className="w-4 h-4 text-red-500/50 hover:text-red-500" />
        </button>
      </div>
    </div>
  );
}