// components/invitations/CampaignPerformanceChart.tsx
'use client';

import { TrendingUp, Users, DollarSign, Target } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { MarketingCampaign } from '@/types/invitations';

interface CampaignPerformanceChartProps {
  campaign: MarketingCampaign;
  className?: string;
}

export default function CampaignPerformanceChart({ campaign, className }: CampaignPerformanceChartProps) {
  const conversionRate = campaign.total_leads > 0
    ? (campaign.converted_leads / campaign.total_leads) * 100
    : 0;

  const budgetUsed = campaign.budget_mrusdt > 0
    ? (campaign.spent_mrusdt / campaign.budget_mrusdt) * 100
    : 0;

  const metrics = [
    {
      label: 'نسبة التحويل',
      value: `${conversionRate.toFixed(1)}%`,
      icon: Target,
      color: 'text-purple-500',
    },
    {
      label: 'إجمالي العملاء',
      value: campaign.total_leads,
      icon: Users,
      color: 'text-blue-500',
    },
    {
      label: 'العملاء المحولون',
      value: campaign.converted_leads,
      icon: TrendingUp,
      color: 'text-emerald-500',
    },
    {
      label: 'الميزانية المستخدمة',
      value: `${campaign.spent_mrusdt.toFixed(2)} / ${campaign.budget_mrusdt.toFixed(2)} MR_USDT`,
      icon: DollarSign,
      color: 'text-amber-500',
    },
  ];

  return (
    <div className={cn("space-y-4", className)}>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {metrics.map((metric, idx) => (
          <div key={idx} className="p-3 rounded-xl bg-white/5 border border-white/10">
            <div className="flex items-center gap-2">
              <metric.icon className={cn("w-4 h-4", metric.color)} />
              <span className="text-xs text-muted-foreground/50">{metric.label}</span>
            </div>
            <p className="mt-1 text-sm font-bold text-foreground/90">{metric.value}</p>
          </div>
        ))}
      </div>

      <div className="space-y-2">
        <div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground/50">تقدم الميزانية</span>
            <span className="text-foreground/70">{budgetUsed.toFixed(0)}%</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden mt-0.5">
            <div
              className="h-full rounded-full bg-gradient-to-r from-primary to-secondary transition-all duration-1000"
              style={{ width: `${Math.min(budgetUsed, 100)}%` }}
            />
          </div>
        </div>
        <div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground/50">نسبة التحويل</span>
            <span className="text-foreground/70">{conversionRate.toFixed(1)}%</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden mt-0.5">
            <div
              className="h-full rounded-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-1000"
              style={{ width: `${Math.min(conversionRate, 100)}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}