// app/(dashboard)/command/alerts/page.tsx
'use client';

import { useState } from 'react';
import { useSystemAlerts, useResolveAlert, useDismissAlert } from '@/hooks/command/useAlerts';
import AlertList from '@/components/command/AlertList';
import { Loader2, AlertTriangle, Filter, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AlertSeverity } from '@/types/command';

const severityOptions: { value: AlertSeverity | ''; label: string }[] = [
  { value: '', label: 'كل المستويات' },
  { value: 'INFO', label: 'معلومات' },
  { value: 'WARNING', label: 'تحذير' },
  { value: 'CRITICAL', label: 'حرج' },
  { value: 'SUCCESS', label: 'نجاح' },
];

export default function AlertsPage() {
  const [severityFilter, setSeverityFilter] = useState<AlertSeverity | ''>('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'resolved'>('active');

  const { data: alerts, isLoading } = useSystemAlerts({
    ...(severityFilter && { severity: severityFilter }),
    ...(statusFilter === 'active' && { is_resolved: false }),
    ...(statusFilter === 'resolved' && { is_resolved: true }),
  });

  const resolveAlert = useResolveAlert();
  const dismissAlert = useDismissAlert();

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">🔔 التنبيهات</h1>
          <p className="text-sm text-muted-foreground/70">مراقبة وإدارة تنبيهات النظام</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value as AlertSeverity | '')}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-foreground/80 outline-none focus:border-primary/30"
        >
          {severityOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        <div className="flex gap-1 bg-white/5 rounded-xl p-1">
          <button
            onClick={() => setStatusFilter('active')}
            className={cn(
              "px-3 py-1.5 rounded-lg text-xs transition-all",
              statusFilter === 'active' ? "bg-primary/20 text-primary" : "text-muted-foreground/50 hover:text-foreground/80"
            )}
          >
            نشطة
          </button>
          <button
            onClick={() => setStatusFilter('resolved')}
            className={cn(
              "px-3 py-1.5 rounded-lg text-xs transition-all",
              statusFilter === 'resolved' ? "bg-emerald-500/20 text-emerald-500" : "text-muted-foreground/50 hover:text-foreground/80"
            )}
          >
            محلولة
          </button>
          <button
            onClick={() => setStatusFilter('all')}
            className={cn(
              "px-3 py-1.5 rounded-lg text-xs transition-all",
              statusFilter === 'all' ? "bg-white/10 text-foreground/80" : "text-muted-foreground/50 hover:text-foreground/80"
            )}
          >
            الكل
          </button>
        </div>
        <span className="text-xs text-muted-foreground/40 mr-auto">
          {alerts?.length || 0} تنبيه
        </span>
      </div>

      <AlertList
        alerts={alerts || []}
        onResolve={(id) => resolveAlert.mutate(id)}
        onDismiss={(id) => dismissAlert.mutate(id)}
      />
    </div>
  );
}