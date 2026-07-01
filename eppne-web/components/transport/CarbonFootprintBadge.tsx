// components/transport/CarbonFootprintBadge.tsx
'use client';

import { Leaf, TrendingDown, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';

interface CarbonFootprintBadgeProps {
  carbonKg: number;
  distanceKm: number;
  className?: string;
}

export default function CarbonFootprintBadge({
  carbonKg,
  distanceKm,
  className,
}: CarbonFootprintBadgeProps) {
  const isLow = carbonKg < 10;
  const isMedium = carbonKg >= 10 && carbonKg < 50;
  const isHigh = carbonKg >= 50;

  const colorClass = isLow
    ? 'border-emerald-500/30 text-emerald-500 bg-emerald-500/5'
    : isMedium
    ? 'border-amber-500/30 text-amber-500 bg-amber-500/5'
    : 'border-red-500/30 text-red-500 bg-red-500/5';

  const icon = isLow ? <Leaf className="w-4 h-4" /> : isMedium ? <TrendingDown className="w-4 h-4" /> : <TrendingUp className="w-4 h-4" />;

  return (
    <div className={cn("flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-medium", colorClass, className)}>
      {icon}
      <span>{carbonKg.toFixed(2)} كجم CO₂</span>
      <span className="text-muted-foreground/50">·</span>
      <span>{distanceKm.toFixed(1)} كم</span>
    </div>
  );
}