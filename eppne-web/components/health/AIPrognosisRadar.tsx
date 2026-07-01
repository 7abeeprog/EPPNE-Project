// components/health/AIPrognosisRadar.tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { getAIPrognosis } from '@/services/health';
import { Loader2, AlertTriangle, CheckCircle, Activity, Brain } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns/ar';
import type { AIHealthPrognosis, RiskLevel } from '@/types/health';

const riskColors: Record<RiskLevel, string> = {
  SAFE: 'border-emerald-500/30 bg-emerald-500/5 text-emerald-500',
  MONITOR: 'border-amber-500/30 bg-amber-500/5 text-amber-500',
  WARNING: 'border-orange-500/30 bg-orange-500/5 text-orange-500',
  CRITICAL: 'border-red-500/30 bg-red-500/5 text-red-500',
};

const riskLabels: Record<RiskLevel, string> = {
  SAFE: 'آمن',
  MONITOR: 'مراقبة',
  WARNING: 'تحذير',
  CRITICAL: 'حرج',
};

export default function AIPrognosisRadar() {
  const { data, isLoading } = useQuery({
    queryKey: ['ai-prognosis'],
    queryFn: () => getAIPrognosis().then(res => res.data),
    refetchInterval: 30000,
    staleTime: 10000,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-32">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground/60">
        <Brain className="w-8 h-8 mx-auto mb-2 opacity-30" />
        <p>لا توجد توقعات صحية من الذكاء الاصطناعي</p>
      </div>
    );
  }

  const latest = data[0];

  return (
    <div className="space-y-4">
      {/* أحدث توقعات */}
      <div className={cn(
        "p-4 rounded-2xl border-2 backdrop-blur-xl transition-all duration-500",
        riskColors[latest.risk_level]
      )}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-white/5">
              <Brain className="w-5 h-5" />
            </div>
            <div>
              <h4 className="font-medium text-foreground/90">التشخيص المتوقع</h4>
              <p className="text-sm text-foreground/70">{latest.predicted_condition}</p>
            </div>
          </div>
          <div className="text-right">
            <span className={cn(
              "text-xs px-3 py-1 rounded-full border font-medium",
              riskColors[latest.risk_level]
            )}>
              {riskLabels[latest.risk_level]}
            </span>
            <p className="text-xs text-muted-foreground/40 mt-1">
              ثقة {latest.confidence_score}%
            </p>
          </div>
        </div>

        {/* التوصيات */}
        {latest.preventive_recommendations && (
          <div className="mt-3 p-3 rounded-xl bg-white/5 border border-white/10">
            <p className="text-xs text-muted-foreground/60 flex items-center gap-1">
              <Activity className="w-3 h-3" />
              التوصيات:
            </p>
            <ul className="mt-1 space-y-1 text-sm text-foreground/70">
              {Object.entries(latest.preventive_recommendations).map(([key, value]) => (
                <li key={key} className="flex items-start gap-2">
                  <span className="text-primary/50">•</span>
                  <span>{String(value)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <p className="text-[10px] text-muted-foreground/30 mt-2 text-left">
          {formatDistanceToNow(new Date(latest.created_at), { addSuffix: true })}
        </p>
      </div>

      {/* التاريخ */}
      {data.length > 1 && (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground/50">التاريخ السابق</p>
          {data.slice(1, 4).map((prognosis) => (
            <div
              key={prognosis.id}
              className="flex items-center justify-between p-2 rounded-xl bg-white/5 border border-white/5 text-sm"
            >
              <span className="text-foreground/70">{prognosis.predicted_condition}</span>
              <span className={cn("text-xs px-2 py-0.5 rounded-full border", riskColors[prognosis.risk_level])}>
                {riskLabels[prognosis.risk_level]}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}