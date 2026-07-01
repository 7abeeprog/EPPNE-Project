// components/ai-governance/UsageDashboard.tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { getAgentUsageSummary, getAgentQuotas } from '@/services/ai-governance';
import UsageGauge from './UsageGauge';
import { Loader2, TrendingUp, Clock, DollarSign, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';

interface UsageDashboardProps {
  agentId: number;
  agentName: string;
}

export default function UsageDashboard({ agentId, agentName }: UsageDashboardProps) {
  const { data: summary, isLoading: isLoadingSummary } = useQuery({
    queryKey: ['governance-usage', agentId],
    queryFn: () => getAgentUsageSummary(agentId).then(res => res.data),
    refetchInterval: 30000,
    staleTime: 10000,
  });

  const { data: quotas, isLoading: isLoadingQuotas } = useQuery({
    queryKey: ['governance-quotas', agentId],
    queryFn: () => getAgentQuotas(agentId).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  if (isLoadingSummary || isLoadingQuotas) {
    return (
      <div className="flex justify-center items-center h-48">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  const metrics = [
    {
      label: 'إجمالي الطلبات',
      value: summary?.total_requests || 0,
      icon: Zap,
      color: 'text-blue-500 bg-blue-500/10',
    },
    {
      label: 'إجمالي التوكنات',
      value: (summary?.total_tokens || 0).toLocaleString(),
      icon: TrendingUp,
      color: 'text-purple-500 bg-purple-500/10',
    },
    {
      label: 'التكلفة الإجمالية',
      value: `${(summary?.total_cost_mrusdt || 0).toFixed(4)} MR_USDT`,
      icon: DollarSign,
      color: 'text-emerald-500 bg-emerald-500/10',
    },
    {
      label: 'متوسط زمن الاستجابة',
      value: `${(summary?.avg_response_time_ms || 0).toFixed(0)} ms`,
      icon: Clock,
      color: 'text-amber-500 bg-amber-500/10',
    },
  ];

  return (
    <div className="space-y-6">
      {/* بطاقات المقاييس */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {metrics.map((metric, idx) => (
          <div
            key={idx}
            className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10"
          >
            <div className="flex items-center gap-2">
              <div className={cn("p-2 rounded-xl", metric.color)}>
                <metric.icon className="w-4 h-4" />
              </div>
              <span className="text-xs text-muted-foreground/50">{metric.label}</span>
            </div>
            <p className="mt-2 text-lg font-bold text-foreground/90">{metric.value}</p>
          </div>
        ))}
      </div>

      {/* الحصص */}
      {quotas && quotas.length > 0 && (
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <h4 className="text-sm font-medium text-foreground/70 mb-4">📊 استهلاك الحصص</h4>
          <div className="space-y-3">
            {quotas.map((quota) => (
              <UsageGauge
                key={quota.id}
                used={quota.current_usage}
                limit={quota.limit_value}
                label={`${quota.limit_type.replace(/_/g, ' ')} (${quota.period})`}
                unit={quota.limit_type === 'COST_MRUSDT' ? 'MR_USDT' : ''}
              />
            ))}
          </div>
          <p className="text-[10px] text-muted-foreground/30 mt-3">
            يتم إعادة تعيين الحصص في {quotas[0]?.reset_at ? new Date(quotas[0].reset_at).toLocaleDateString('ar-EG') : '—'}
          </p>
        </div>
      )}
    </div>
  );
}