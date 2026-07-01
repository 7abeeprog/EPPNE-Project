// components/projects/ProjectAnalytics.tsx
'use client';

import { TrendingUp, Users, Wallet, Target, CheckCircle, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ProjectAnalytics } from '@/types/projects';

interface ProjectAnalyticsProps {
  analytics: ProjectAnalytics;
  className?: string;
}

export default function ProjectAnalytics({ analytics, className }: ProjectAnalyticsProps) {
  const cards = [
    {
      label: 'نسبة التمويل',
      value: `${analytics.funding_percentage.toFixed(0)}%`,
      icon: TrendingUp,
      color: 'text-emerald-500 bg-emerald-500/10',
      trend: analytics.funding_percentage > 50 ? 'up' : 'down',
    },
    {
      label: 'المساهمون',
      value: analytics.total_contributors,
      icon: Users,
      color: 'text-blue-500 bg-blue-500/10',
    },
    {
      label: 'إجمالي التمويل',
      value: `${analytics.total_funding_mrusdt.toFixed(2)} MR_USDT`,
      icon: Wallet,
      color: 'text-primary bg-primary/10',
    },
    {
      label: 'المعالم المنجزة',
      value: `${analytics.milestones_completed}/${analytics.milestones_total}`,
      icon: CheckCircle,
      color: 'text-purple-500 bg-purple-500/10',
    },
    {
      label: 'المتبقي للهدف',
      value: `${analytics.remaining_to_goal.toFixed(2)} MR_USDT`,
      icon: Target,
      color: 'text-amber-500 bg-amber-500/10',
    },
  ];

  return (
    <div className={cn("grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4", className)}>
      {cards.map((card, idx) => (
        <div
          key={idx}
          className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all duration-300"
        >
          <div className="flex items-center gap-2">
            <div className={cn("p-2 rounded-xl", card.color)}>
              <card.icon className="w-4 h-4" />
            </div>
            <span className="text-xs text-muted-foreground/50">{card.label}</span>
          </div>
          <p className="mt-2 text-lg font-bold text-foreground/90">{card.value}</p>
        </div>
      ))}
    </div>
  );
}