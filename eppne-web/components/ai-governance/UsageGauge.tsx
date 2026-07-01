// components/ai-governance/UsageGauge.tsx
'use client';

import { cn } from '@/lib/utils';

interface UsageGaugeProps {
  used: number;
  limit: number;
  label: string;
  unit?: string;
  className?: string;
}

export default function UsageGauge({ used, limit, label, unit = '', className }: UsageGaugeProps) {
  const percentage = limit > 0 ? Math.min((used / limit) * 100, 100) : 0;
  const isWarning = percentage >= 80 && percentage < 100;
  const isExceeded = percentage >= 100;

  const colorClass = isExceeded
    ? 'from-red-500 to-red-600'
    : isWarning
    ? 'from-amber-500 to-amber-600'
    : 'from-primary to-secondary';

  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground/70">{label}</span>
        <span className={cn(
          "font-mono text-sm",
          isExceeded ? "text-red-500" : isWarning ? "text-amber-500" : "text-foreground/80"
        )}>
          {used.toFixed(2)} / {limit.toFixed(2)} {unit}
          {isExceeded && <span className="ml-2 text-xs text-red-500">⚠️ تجاوز</span>}
          {isWarning && !isExceeded && <span className="ml-2 text-xs text-amber-500">⚠️ 80%</span>}
        </span>
      </div>
      <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden">
        <div
          className={cn("h-full rounded-full bg-gradient-to-r transition-all duration-500", colorClass)}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
    </div>
  );
}