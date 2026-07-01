// app/(dashboard)/command/page.tsx
'use client';

import { useState } from 'react';
import { useCommandStats, useDashboardMetrics } from '@/hooks/command/useCommandStats';
import { useSystemAlerts } from '@/hooks/command/useAlerts';
import MetricCard from '@/components/command/MetricCard';
import AlertList from '@/components/command/AlertList';
import { Loader2, Activity, Users, Building2, DollarSign, AlertTriangle } from 'lucide-react';
import Link from 'next/link';

export default function CommandDashboard() {
  const [period, setPeriod] = useState<'DAILY' | 'WEEKLY' | 'MONTHLY' | 'YEARLY'>('MONTHLY');

  const { data: stats, isLoading: statsLoading } = useCommandStats();
  const { data: metrics, isLoading: metricsLoading } = useDashboardMetrics(period);
  const { data: alerts, isLoading: alertsLoading } = useSystemAlerts({ is_resolved: false, limit: 5 });

  const isLoading = statsLoading || metricsLoading || alertsLoading;

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const mainStats = [
    { label: 'المستخدمون', value: stats?.total_users || 0, icon: '👥', color: 'text-blue-500' },
    { label: 'البراندات', value: stats?.total_tenants || 0, icon: '🏢', color: 'text-emerald-500' },
    { label: 'الإيرادات', value: `${(stats?.total_revenue || 0).toFixed(2)} MR_USDT`, icon: '💰', color: 'text-amber-500' },
    { label: 'المعاملات', value: stats?.total_transactions || 0, icon: '📊', color: 'text-purple-500' },
    { label: 'الجلسات النشطة', value: stats?.active_sessions || 0, icon: '🟢', color: 'text-emerald-500' },
    { label: 'صحة النظام', value: `${stats?.system_health || 100}%`, icon: '❤️', color: 'text-red-500' },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">🏛️ القيادة الاستراتيجية</h1>
          <p className="text-sm text-muted-foreground/70">لوحة التحكم المركزية لإدارة المنصة</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground/50">الفترة:</span>
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value as any)}
            className="bg-white/5 border border-white/10 rounded-xl px-3 py-1.5 text-sm text-foreground/80 outline-none focus:border-primary/30"
          >
            <option value="DAILY">يومي</option>
            <option value="WEEKLY">أسبوعي</option>
            <option value="MONTHLY">شهري</option>
            <option value="YEARLY">سنوي</option>
          </select>
        </div>
      </div>

      {/* الإحصائيات الرئيسية */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {mainStats.map((stat, idx) => (
          <div key={idx} className="p-3 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
            <div className="flex items-center gap-2">
              <span className="text-lg">{stat.icon}</span>
              <span className="text-xs text-muted-foreground/50">{stat.label}</span>
            </div>
            <p className="mt-1 text-base font-bold text-foreground/90">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* المقاييس التفصيلية */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics?.map((metric) => (
          <MetricCard key={metric.id} metric={metric} />
        ))}
      </div>

      {/* صف السريع: التنبيهات + روابط سريعة */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2 p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-foreground/70 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              التنبيهات النشطة
              {alerts && alerts.length > 0 && (
                <span className="text-xs bg-red-500/20 text-red-500 px-2 py-0.5 rounded-full">
                  {alerts.length}
                </span>
              )}
            </h3>
            <Link href="/command/alerts" className="text-xs text-primary/70 hover:text-primary">
              عرض الكل
            </Link>
          </div>
          <AlertList alerts={alerts || []} />
        </div>

        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <h3 className="text-sm font-medium text-foreground/70 mb-3">🚀 روابط سريعة</h3>
          <div className="space-y-2">
            <Link href="/command/brands" className="flex items-center gap-2 p-2 rounded-xl hover:bg-white/5 transition-colors text-sm text-foreground/70">
              <Building2 className="w-4 h-4 text-primary/60" />
              إدارة البراندات
            </Link>
            <Link href="/command/users" className="flex items-center gap-2 p-2 rounded-xl hover:bg-white/5 transition-colors text-sm text-foreground/70">
              <Users className="w-4 h-4 text-primary/60" />
              إدارة المستخدمين
            </Link>
            <Link href="/command/reports" className="flex items-center gap-2 p-2 rounded-xl hover:bg-white/5 transition-colors text-sm text-foreground/70">
              <DollarSign className="w-4 h-4 text-primary/60" />
              التقارير المالية
            </Link>
            <Link href="/command/monitoring" className="flex items-center gap-2 p-2 rounded-xl hover:bg-white/5 transition-colors text-sm text-foreground/70">
              <Activity className="w-4 h-4 text-primary/60" />
              مراقبة النظام
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}