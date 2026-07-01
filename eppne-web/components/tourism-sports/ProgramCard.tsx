// components/tourism-sports/ProgramCard.tsx
'use client';

import { Calendar, Users, DollarSign } from 'lucide-react';
import { format } from 'date-fns/ar';
import { cn } from '@/lib/utils';
import type { TourismProgram } from '@/types/tourism-sports';

export default function ProgramCard({ program }: { program: TourismProgram }) {
  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <h4 className="font-medium text-foreground/80">{program.title}</h4>
      <div className="flex flex-wrap gap-2 mt-1">
        <span className="text-xs px-2 py-0.5 rounded-full border-primary/30 text-primary bg-primary/5">
          {program.program_tier}
        </span>
        <span className="text-xs px-2 py-0.5 rounded-full border-white/10 text-muted-foreground/60">
          {program.status}
        </span>
      </div>
      <div className="mt-2 space-y-1 text-xs text-muted-foreground/50">
        <div className="flex items-center gap-2">
          <Calendar className="w-3 h-3" />
          {format(new Date(program.start_date), 'dd/MM/yyyy')} - {format(new Date(program.end_date), 'dd/MM/yyyy')}
        </div>
        <div className="flex items-center gap-2">
          <Users className="w-3 h-3" />
          {program.max_capacity} مقعد
        </div>
        <div className="flex items-center gap-2">
          <DollarSign className="w-3 h-3" />
          {program.base_price_mrusdt} MR_USDT
        </div>
      </div>
    </div>
  );
}