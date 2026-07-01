// components/zamakana/ScenarioCard.tsx
'use client';

import { Calendar, Brain, CheckCircle, Clock, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { FutureScenario } from '@/types/zamakana';

const statusConfig: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  DRAFTING: {
    label: 'قيد التحليل',
    color: 'border-amber-500/30 text-amber-500 bg-amber-500/5',
    icon: <Clock className="w-3.5 h-3.5 animate-pulse" />,
  },
  HUMAN_REVIEW: {
    label: 'مراجعة بشرية',
    color: 'border-blue-500/30 text-blue-500 bg-blue-500/5',
    icon: <Brain className="w-3.5 h-3.5" />,
  },
  CONFIRMED: {
    label: 'معتمد',
    color: 'border-emerald-500/30 text-emerald-500 bg-emerald-500/5',
    icon: <CheckCircle className="w-3.5 h-3.5" />,
  },
};

export default function ScenarioCard({ scenario }: { scenario: FutureScenario }) {
  const config = statusConfig[scenario.status] || statusConfig.DRAFTING;

  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">{scenario.scenario_title}</h4>
          <p className="text-sm text-muted-foreground/60 line-clamp-2">{scenario.description}</p>
        </div>
        <span className={cn("inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full border", config.color)}>
          {config.icon}
          {config.label}
        </span>
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground/50">
        <span className="flex items-center gap-1">
          <Calendar className="w-3 h-3" />
          {scenario.target_year}
        </span>
        <span className="flex items-center gap-1">
          <Brain className="w-3 h-3" />
          {scenario.ai_analysis_report ? 'تحليل AI متاح' : 'بانتظار التحليل'}
        </span>
      </div>
    </div>
  );
}