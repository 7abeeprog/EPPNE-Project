// components/manufacturing/MaintenanceRadar.tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { getPendingMaintenance } from '@/services/manufacturing';
import { Loader2, AlertTriangle, Wrench, Clock, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns/ar';

interface MaintenanceRadarProps {
  lineId: number;
}

export default function MaintenanceRadar({ lineId }: MaintenanceRadarProps) {
  const { data: logs, isLoading } = useQuery({
    queryKey: ['manufacturing-pending-maintenance', lineId],
    queryFn: () => getPendingMaintenance(lineId).then((res) => res.data),
    enabled: !!lineId,
    refetchInterval: 30000,
  });

  if (isLoading) {
    return <div className="flex justify-center items-center h-32"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;
  }

  if (!logs || logs.length === 0) {
    return (
      <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 text-center text-muted-foreground/50 text-sm">
        <CheckCircle className="w-8 h-8 mx-auto mb-2 text-emerald-500/30" />
        لا توجد أعمال صيانة معلقة
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {logs.map((log) => {
        const probability = log.ai_prediction?.failure_probability || 0;
        const isCritical = probability > 0.8;
        const isWarning = probability > 0.5 && probability <= 0.8;

        return (
          <div
            key={log.id}
            className={cn(
              "p-4 rounded-2xl border transition-all",
              isCritical
                ? "border-red-500/30 bg-red-500/5"
                : isWarning
                ? "border-amber-500/30 bg-amber-500/5"
                : "border-blue-500/30 bg-blue-500/5"
            )}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3">
                <div className={cn(
                  "p-2 rounded-xl",
                  isCritical ? "bg-red-500/10 text-red-500" :
                  isWarning ? "bg-amber-500/10 text-amber-500" :
                  "bg-blue-500/10 text-blue-500"
                )}>
                  {isCritical ? <AlertTriangle className="w-5 h-5" /> : <Wrench className="w-5 h-5" />}
                </div>
                <div>
                  <h4 className="font-medium text-foreground/80">
                    {isCritical ? '⚠️ عطل وشيك' : isWarning ? '⚠️ صيانة موصى بها' : 'مراقبة'}
                  </h4>
                  <p className="text-sm text-foreground/70">
                    احتمال العطل: {(probability * 100).toFixed(0)}%
                  </p>
                  {log.recommended_action && (
                    <p className="text-xs text-muted-foreground/60 mt-1">
                      التوصية: {log.recommended_action}
                    </p>
                  )}
                  {log.ai_prediction?.expected_remaining_hours && (
                    <p className="text-xs text-muted-foreground/50 mt-0.5">
                      الوقت المتبقي المتوقع: {log.ai_prediction.expected_remaining_hours} ساعة
                    </p>
                  )}
                </div>
              </div>
              <span className="text-xs text-muted-foreground/30">
                {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
              </span>
            </div>
            {log.status === 'PENDING' && !isCritical && (
              <button className="mt-2 px-3 py-1 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors text-xs">
                جدولة الصيانة
              </button>
            )}
            {isCritical && (
              <button className="mt-2 px-3 py-1 rounded-xl bg-red-500/20 text-red-500 border border-red-500/30 hover:bg-red-500/30 transition-colors text-xs animate-pulse">
                ⚠️ جدولة عاجلة
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}