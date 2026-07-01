// components/projects/ProjectAnalysisDashboard.tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { getProjectAnalytics } from '@/services/projects';
import { 
  TrendingUp, TrendingDown, Users, Wallet, 
  Target, CheckCircle, Clock, Leaf,
  PieChart, BarChart3, LineChart
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

interface ProjectAnalysisDashboardProps {
  projectId: number;
}

interface MetricCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  color?: string;
}

function MetricCard({ label, value, icon, trend, color = 'text-primary' }: MetricCardProps) {
  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all duration-300">
      <div className="flex items-center justify-between">
        <div className={cn("p-2 rounded-xl bg-white/5", color)}>
          {icon}
        </div>
        {trend && (
          <span className={cn(
            "text-xs flex items-center gap-1",
            trend === 'up' ? 'text-emerald-500' : 'text-red-500'
          )}>
            {trend === 'up' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          </span>
        )}
      </div>
      <p className="mt-2 text-lg font-bold text-foreground/90">{value}</p>
      <p className="text-xs text-muted-foreground/50">{label}</p>
    </div>
  );
}

export default function ProjectAnalysisDashboard({ projectId }: ProjectAnalysisDashboardProps) {
  const { data: analytics, isLoading } = useQuery({
    queryKey: ['project-analytics', projectId],
    queryFn: () => getProjectAnalytics(projectId).then(res => res.data),
    refetchInterval: 30000,
    staleTime: 10000,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="text-center py-16 text-muted-foreground/60">
        <p>لا توجد بيانات تحليلية متاحة</p>
      </div>
    );
  }

  const metrics = [
    {
      label: 'نسبة التمويل',
      value: `${analytics.funding_percentage.toFixed(0)}%`,
      icon: <Target className="w-4 h-4" />,
      trend: analytics.funding_percentage > 50 ? 'up' : 'neutral',
      color: 'text-emerald-500',
    },
    {
      label: 'إجمالي التمويل',
      value: `${analytics.total_funding_mrusdt.toFixed(2)} MR_USDT`,
      icon: <Wallet className="w-4 h-4" />,
      color: 'text-primary',
    },
    {
      label: 'المساهمون',
      value: analytics.total_contributors,
      icon: <Users className="w-4 h-4" />,
      color: 'text-blue-500',
    },
    {
      label: 'المعالم المنجزة',
      value: `${analytics.milestones_completed}/${analytics.milestones_total}`,
      icon: <CheckCircle className="w-4 h-4" />,
      color: 'text-purple-500',
    },
    {
      label: 'المتبقي للهدف',
      value: `${analytics.remaining_to_goal.toFixed(2)} MR_USDT`,
      icon: <Target className="w-4 h-4" />,
      color: 'text-amber-500',
    },
    {
      label: 'قيمة المساهمات العينية',
      value: `${analytics.total_in_kind_value.toFixed(2)} MR_USDT`,
      icon: <Leaf className="w-4 h-4" />,
      color: 'text-emerald-400',
    },
  ];

  return (
    <div className="space-y-6">
      {/* بطاقات المؤشرات */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {metrics.map((metric, idx) => (
          <MetricCard key={idx} {...metric} />
        ))}
      </div>

      {/* رسوم بيانية (مكان مبدئي، سيتم استبدالها بـ Recharts/Chart.js لاحقاً) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <h4 className="text-sm font-medium text-foreground/80 mb-3 flex items-center gap-2">
            <PieChart className="w-4 h-4 text-muted-foreground/50" />
            توزيع المساهمات
          </h4>
          <div className="h-32 flex items-center justify-center text-muted-foreground/40 text-sm">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-primary" /> مالية</span>
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-emerald-500" /> عينية</span>
            </div>
            {/* هنا سيتم إضافة رسم بياني دائري باستخدام Recharts */}
          </div>
        </div>
        
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <h4 className="text-sm font-medium text-foreground/80 mb-3 flex items-center gap-2">
            <LineChart className="w-4 h-4 text-muted-foreground/50" />
            تقدم التمويل
          </h4>
          <div className="h-32 flex items-center justify-center text-muted-foreground/40 text-sm">
            <span className="flex items-center gap-2">
              <span className="text-primary font-bold">{analytics.funding_percentage.toFixed(0)}%</span>
              من الهدف
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}