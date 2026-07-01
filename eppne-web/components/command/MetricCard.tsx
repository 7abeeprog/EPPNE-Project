// components/command/MetricCard.tsx
'use client';

import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { DashboardMetric } from '@/types/command';

interface MetricCardProps {
  metric: DashboardMetric;
  onClick?: () => void;
}

export default function MetricCard({ metric, onClick }: MetricCardProps) {
  const isPositive = metric.trend === 'up';
  const isNegative = metric.trend === 'down';

  return (
    <div
      onClick={onClick}
      className={cn(
        "p-4 rounded-2xl bg-card/20 backdrop-blur-xl border transition-all cursor-pointer",
        "border-white/10 hover:border-primary/20 hover:shadow-[0_0_40px_-15px_rgba(var(--primary-rgb),0.15)]"
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm text-foreground/60">{metric.label}</span>
        <span className="text-2xl">{metric.icon}</span>
      </div>
      <p className="mt-2 text-2xl font-bold text-foreground/90">{metric.value.toLocaleString()}</p>
      <div className="flex items-center gap-2 mt-1">
        <span className={cn(
          "text-xs flex items-center gap-0.5",
          isPositive ? "text-emerald-500" : isNegative ? "text-red-500" : "text-muted-foreground/50"
        )}>
          {isPositive && <TrendingUp className="w-3 h-3" />}
          {isNegative && <TrendingDown className="w-3 h-3" />}
          {!isPositive && !isNegative && <Minus className="w-3 h-3" />}
          {metric.change > 0 ? '+' : ''}{metric.change}%
        </span>
        <span className="text-xs text-muted-foreground/40">مقارنة بالفترة السابقة</span>
      </div>
    </div>
  );
}