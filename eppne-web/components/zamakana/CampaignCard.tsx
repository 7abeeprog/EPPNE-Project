// components/zamakana/CampaignCard.tsx
'use client';

import { Clock, Users, Calendar, CheckCircle, AlertCircle } from 'lucide-react';
import { format } from 'date-fns/ar';
import { cn } from '@/lib/utils';
import type { PlanetaryCampaign } from '@/types/zamakana';

export default function CampaignCard({ campaign }: { campaign: PlanetaryCampaign }) {
  const progress = campaign.target_time_hours > 0
    ? (campaign.collected_time_hours / campaign.target_time_hours) * 100
    : 0;

  const isCompleted = campaign.status === 'COMPLETED';
  const isActive = campaign.status === 'ACTIVE';

  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">{campaign.title}</h4>
          <p className="text-sm text-muted-foreground/60 line-clamp-2">{campaign.description}</p>
        </div>
        <span className={cn(
          "text-xs px-2 py-0.5 rounded-full border",
          isCompleted ? "border-emerald-500/30 text-emerald-500" :
          isActive ? "border-blue-500/30 text-blue-500" :
          "border-red-500/30 text-red-500"
        )}>
          {isCompleted ? 'مكتملة' : isActive ? 'نشطة' : campaign.status}
        </span>
      </div>
      <div className="mt-2 space-y-1 text-xs text-muted-foreground/50">
        <div className="flex items-center gap-2">
          <Clock className="w-3 h-3" />
          {campaign.collected_time_hours} / {campaign.target_time_hours} ساعة
        </div>
        <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-primary to-secondary transition-all duration-1000"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
        <div className="flex items-center gap-2">
          <Calendar className="w-3 h-3" />
          {format(new Date(campaign.start_date), 'dd/MM/yyyy')} - {format(new Date(campaign.end_date), 'dd/MM/yyyy')}
        </div>
        <div className="flex items-center gap-2">
          <Users className="w-3 h-3" />
          {campaign.pledges?.length || 0} مشارك
        </div>
      </div>
    </div>
  );
}