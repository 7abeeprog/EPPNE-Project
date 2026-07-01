// components/command/AlertList.tsx
'use client';

import { formatDistanceToNow } from 'date-fns/ar';
import { AlertCircle, CheckCircle, Info, AlertTriangle, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SystemAlert } from '@/types/command';

interface AlertListProps {
  alerts: SystemAlert[];
  onResolve?: (id: number) => void;
  onDismiss?: (id: number) => void;
  className?: string;
}

const severityConfig = {
  INFO: { icon: Info, color: 'text-blue-500 border-blue-500/30 bg-blue-500/5' },
  WARNING: { icon: AlertTriangle, color: 'text-amber-500 border-amber-500/30 bg-amber-500/5' },
  CRITICAL: { icon: AlertCircle, color: 'text-red-500 border-red-500/30 bg-red-500/5' },
  SUCCESS: { icon: CheckCircle, color: 'text-emerald-500 border-emerald-500/30 bg-emerald-500/5' },
};

export default function AlertList({ alerts, onResolve, onDismiss, className }: AlertListProps) {
  if (alerts.length === 0) {
    return (
      <div className={cn("p-8 text-center text-muted-foreground/50", className)}>
        <CheckCircle className="w-8 h-8 mx-auto mb-2 text-emerald-500/30" />
        <p>لا توجد تنبيهات</p>
        <p className="text-xs">جميع الأنظمة تعمل بشكل طبيعي</p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-2", className)}>
      {alerts.map((alert) => {
        const config = severityConfig[alert.severity] || severityConfig.INFO;
        const Icon = config.icon;

        return (
          <div
            key={alert.id}
            className={cn(
              "flex items-start gap-3 p-3 rounded-xl border transition-all",
              config.color,
              alert.is_resolved && "opacity-60"
            )}
          >
            <Icon className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium text-foreground/80">{alert.title}</span>
                <span className="text-xs text-muted-foreground/50">{alert.source}</span>
                {alert.is_resolved && (
                  <span className="text-xs text-emerald-500/70">✓ محلولة</span>
                )}
              </div>
              <p className="text-sm text-muted-foreground/60">{alert.description}</p>
              <span className="text-[10px] text-muted-foreground/30">
                {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
              </span>
            </div>
            {!alert.is_resolved && (
              <div className="flex gap-1">
                {onResolve && (
                  <button
                    onClick={() => onResolve(alert.id)}
                    className="p-1 rounded-lg hover:bg-white/10 transition-colors text-emerald-500/50 hover:text-emerald-500"
                  >
                    <CheckCircle className="w-4 h-4" />
                  </button>
                )}
                {onDismiss && (
                  <button
                    onClick={() => onDismiss(alert.id)}
                    className="p-1 rounded-lg hover:bg-white/10 transition-colors text-muted-foreground/50 hover:text-red-500"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}