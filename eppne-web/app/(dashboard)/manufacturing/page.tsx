// app/(dashboard)/manufacturing/page.tsx
'use client';

import { useFacilities } from '@/hooks/manufacturing/useFacilities';
import { useManufacturingStats } from '@/hooks/manufacturing/useStats';
import { usePendingMaintenance } from '@/hooks/manufacturing/usePendingMaintenance';
import { Loader2, Plus, Factory, Package, AlertTriangle, CheckCircle, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

export default function ManufacturingDashboard() {
  const { data: facilities, isLoading: facilitiesLoading } = useFacilities({ limit: 5 });
  const { data: stats, isLoading: statsLoading } = useManufacturingStats();
  const { data: maintenance, isLoading: maintenanceLoading } = usePendingMaintenance();

  const isLoading = facilitiesLoading || statsLoading || maintenanceLoading;

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const statCards = [
    { label: 'المنشآت', value: stats?.total_facilities || 0, icon: Factory, color: 'text-blue-500' },
    { label: 'الدفعات النشطة', value: stats?.active_batches || 0, icon: Package, color: 'text-amber-500' },
    { label: 'صيانة معلقة', value: stats?.pending_maintenance || 0, icon: AlertTriangle, color: 'text-red-500' },
    { label: 'إجمالي التكلفة', value: `${stats?.total_material_cost?.toFixed(2) || 0} MR_USDT`, icon: TrendingUp, color: 'text-emerald-500' },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90 flex items-center gap-2">
            🏭 التصنيع السيادي
          </h1>
          <p className="text-sm text-muted-foreground/70">إدارة المنشآت، الإنتاج، والصيانة التنبؤية</p>
        </div>
        <Link
          href="/manufacturing/facilities/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          منشأة جديدة
        </Link>
      </div>

      {/* الإحصائيات */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {statCards.map((stat, idx) => (
          <div key={idx} className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
            <div className="flex items-center gap-2">
              <stat.icon className={cn("w-4 h-4", stat.color)} />
              <span className="text-xs text-muted-foreground/50">{stat.label}</span>
            </div>
            <p className="mt-2 text-lg font-bold text-foreground/90">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* المنشآت الأخيرة */}
      <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <h3 className="text-sm font-medium text-foreground/70 mb-3">🏗️ المنشآت</h3>
        {facilities?.slice(0, 4).map((facility) => (
          <Link
            key={facility.id}
            href={`/manufacturing/facilities/${facility.id}`}
            className="flex items-center justify-between p-3 rounded-xl hover:bg-white/10 transition-colors border-b border-white/5 last:border-0"
          >
            <div>
              <p className="text-sm font-medium text-foreground/80">{facility.name}</p>
              <p className="text-xs text-muted-foreground/50">{facility.facility_type}</p>
            </div>
            <span className={cn(
              "text-xs px-2 py-0.5 rounded-full border",
              facility.is_active ? "border-emerald-500/30 text-emerald-500" : "border-red-500/30 text-red-500"
            )}>
              {facility.is_active ? 'نشط' : 'موقف'}
            </span>
          </Link>
        ))}
      </div>

      {/* التنبيهات */}
      {maintenance && maintenance.length > 0 && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/30">
          <h3 className="text-sm font-medium text-red-500 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            تنبيهات الصيانة التنبؤية
          </h3>
          <div className="mt-2 space-y-1">
            {maintenance.slice(0, 3).map((log) => (
              <div key={log.id} className="text-sm text-red-500/80 flex items-center gap-2">
                <span>•</span>
                {log.ai_prediction?.failure_probability && log.ai_prediction.failure_probability > 0.8
                  ? `خط إنتاج #${log.production_line_id} - خطر عطل عالٍ (${(log.ai_prediction.failure_probability * 100).toFixed(0)}%)`
                  : `خط إنتاج #${log.production_line_id} - صيانة موصى بها`}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}