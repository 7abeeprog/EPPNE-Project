// components/ai-governance/QuotaManager.tsx
'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAgentQuotas, setAgentQuota, getAgentRateLimits, updateAgentRateLimits } from '@/services/ai-governance';
import { Loader2, Plus, Edit, Save, X, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { LimitType, UsagePeriod, QuotaFormData, RateLimitFormData } from '@/types/ai-governance';

interface QuotaManagerProps {
  agentId: number;
}

const limitTypeLabels: Record<LimitType, string> = {
  REQUEST_COUNT: 'عدد الطلبات',
  TOKEN_COUNT: 'عدد التوكنات',
  COST_MRUSDT: 'التكلفة (MR_USDT)',
  CONCURRENT: 'التزامن',
};

const periodLabels: Record<UsagePeriod, string> = {
  DAILY: 'يومي',
  WEEKLY: 'أسبوعي',
  MONTHLY: 'شهري',
  YEARLY: 'سنوي',
};

export default function QuotaManager({ agentId }: QuotaManagerProps) {
  const queryClient = useQueryClient();
  const [editingQuota, setEditingQuota] = useState<number | null>(null);
  const [newQuota, setNewQuota] = useState<QuotaFormData>({
    limit_type: 'REQUEST_COUNT',
    period: 'MONTHLY',
    limit_value: 1000,
  });
  const [editingRateLimit, setEditingRateLimit] = useState(false);
  const [rateLimitData, setRateLimitData] = useState<RateLimitFormData>({
    requests_per_minute: 60,
    requests_per_hour: 1000,
    concurrent_limit: 10,
  });

  const { data: quotas, isLoading: isLoadingQuotas } = useQuery({
    queryKey: ['governance-quotas', agentId],
    queryFn: () => getAgentQuotas(agentId).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  const { data: rateLimits, isLoading: isLoadingRateLimits } = useQuery({
    queryKey: ['governance-rate-limits', agentId],
    queryFn: () => getAgentRateLimits(agentId).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  const addQuotaMutation = useMutation({
    mutationFn: (data: QuotaFormData) => setAgentQuota(agentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['governance-quotas', agentId] });
    },
  });

  const updateRateLimitMutation = useMutation({
    mutationFn: (data: RateLimitFormData) => updateAgentRateLimits(agentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['governance-rate-limits', agentId] });
      setEditingRateLimit(false);
    },
  });

  if (isLoadingQuotas || isLoadingRateLimits) {
    return <div className="flex justify-center p-8"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;
  }

  return (
    <div className="space-y-6">
      {/* الحصص الحالية */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-medium text-foreground/70">📋 الحصص</h4>
          <button
            onClick={() => {
              setNewQuota({ limit_type: 'REQUEST_COUNT', period: 'MONTHLY', limit_value: 1000 });
              setEditingQuota(-1);
            }}
            className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-full bg-primary/20 text-primary hover:bg-primary/30 transition-colors"
          >
            <Plus className="w-3 h-3" />
            إضافة حصة
          </button>
        </div>

        <div className="space-y-2">
          {quotas?.map((q) => (
            <div
              key={q.id}
              className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10"
            >
              <div>
                <span className="text-sm text-foreground/80">
                  {limitTypeLabels[q.limit_type]} ({periodLabels[q.period]})
                </span>
                <span className="text-sm font-mono text-primary/80 ml-2">
                  {q.limit_value.toFixed(2)}
                </span>
                <span className="text-xs text-muted-foreground/40 ml-1">
                  (المستخدم: {q.current_usage.toFixed(2)})
                </span>
              </div>
              <div className="flex gap-1">
                <button
                  onClick={() => setEditingQuota(q.id)}
                  className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
                >
                  <Edit className="w-3.5 h-3.5 text-muted-foreground/50" />
                </button>
              </div>
            </div>
          ))}
          {quotas?.length === 0 && (
            <div className="text-center text-muted-foreground/40 text-sm py-4">
              لا توجد حصص مضافة
            </div>
          )}
        </div>
      </div>

      {/* حدود المعدل */}
      <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium text-foreground/70">⏱️ حدود المعدل</h4>
          <button
            onClick={() => {
              if (rateLimits) {
                setRateLimitData({
                  requests_per_minute: rateLimits.requests_per_minute,
                  requests_per_hour: rateLimits.requests_per_hour,
                  concurrent_limit: rateLimits.concurrent_limit,
                });
              }
              setEditingRateLimit(true);
            }}
            className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-full bg-blue-500/20 text-blue-500 hover:bg-blue-500/30 transition-colors"
          >
            <Edit className="w-3 h-3" />
            تعديل
          </button>
        </div>

        {editingRateLimit ? (
          <div className="mt-3 space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-xs text-muted-foreground/50">طلبات/دقيقة</label>
                <input
                  type="number"
                  value={rateLimitData.requests_per_minute}
                  onChange={(e) => setRateLimitData(prev => ({ ...prev, requests_per_minute: parseInt(e.target.value) || 0 }))}
                  className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                  min="1"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground/50">طلبات/ساعة</label>
                <input
                  type="number"
                  value={rateLimitData.requests_per_hour}
                  onChange={(e) => setRateLimitData(prev => ({ ...prev, requests_per_hour: parseInt(e.target.value) || 0 }))}
                  className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                  min="1"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground/50">الحد الأقصى للتزامن</label>
                <input
                  type="number"
                  value={rateLimitData.concurrent_limit}
                  onChange={(e) => setRateLimitData(prev => ({ ...prev, concurrent_limit: parseInt(e.target.value) || 0 }))}
                  className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                  min="1"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => updateRateLimitMutation.mutate(rateLimitData)}
                disabled={updateRateLimitMutation.isPending}
                className="flex items-center gap-1 px-4 py-1.5 rounded-xl bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50"
              >
                {updateRateLimitMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                حفظ
              </button>
              <button
                onClick={() => setEditingRateLimit(false)}
                className="px-4 py-1.5 rounded-xl border border-white/10 hover:bg-white/5 transition-colors text-sm"
              >
                إلغاء
              </button>
            </div>
          </div>
        ) : (
          <div className="flex gap-4 mt-3 text-sm">
            <span className="text-muted-foreground/60">
              طلبات/دقيقة: <span className="text-foreground/80 font-medium">{rateLimits?.requests_per_minute || 60}</span>
            </span>
            <span className="text-muted-foreground/60">
              طلبات/ساعة: <span className="text-foreground/80 font-medium">{rateLimits?.requests_per_hour || 1000}</span>
            </span>
            <span className="text-muted-foreground/60">
              أقصى تزامن: <span className="text-foreground/80 font-medium">{rateLimits?.concurrent_limit || 10}</span>
            </span>
          </div>
        )}
      </div>
    </div>
  );
}