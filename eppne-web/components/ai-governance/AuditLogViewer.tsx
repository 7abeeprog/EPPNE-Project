// components/ai-governance/AuditLogViewer.tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { getAgentAuditLogs } from '@/services/ai-governance';
import { formatDistanceToNow } from 'date-fns/ar';
import { Loader2, Shield, User, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AuditLogViewerProps {
  agentId: number;
}

const actionColors: Record<string, string> = {
  CREATE: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30',
  UPDATE: 'text-blue-500 bg-blue-500/10 border-blue-500/30',
  SUSPEND: 'text-red-500 bg-red-500/10 border-red-500/30',
  ACTIVATE: 'text-green-500 bg-green-500/10 border-green-500/30',
  CHANGE_QUOTA: 'text-amber-500 bg-amber-500/10 border-amber-500/30',
  CHANGE_RATE_LIMIT: 'text-purple-500 bg-purple-500/10 border-purple-500/30',
};

const actionLabels: Record<string, string> = {
  CREATE: 'إنشاء',
  UPDATE: 'تحديث',
  SUSPEND: 'تعليق',
  ACTIVATE: 'تفعيل',
  CHANGE_QUOTA: 'تغيير الحصة',
  CHANGE_RATE_LIMIT: 'تغيير حد المعدل',
};

export default function AuditLogViewer({ agentId }: AuditLogViewerProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['governance-audit-logs', agentId],
    queryFn: () => getAgentAuditLogs(agentId, { limit: 50 }).then(res => res.data),
    refetchInterval: 60000,
    staleTime: 30000,
  });

  if (isLoading) {
    return <div className="flex justify-center p-8"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;
  }

  if (!data || data.length === 0) {
    return (
      <div className="text-center text-muted-foreground/40 text-sm py-8">
        <Shield className="w-8 h-8 mx-auto mb-2 opacity-30" />
        لا توجد سجلات تدقيق
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {data.map((log) => (
        <div
          key={log.id}
          className={cn(
            "p-3 rounded-xl border transition-all duration-200",
            actionColors[log.action] || 'border-white/10 bg-white/5'
          )}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
              <div className={cn(
                "p-1.5 rounded-lg",
                actionColors[log.action]?.replace(/border-.*$/, '') || 'bg-white/5'
              )}>
                <Shield className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-foreground/80">
                    {actionLabels[log.action] || log.action}
                  </span>
                  <span className="text-xs text-muted-foreground/50">
                    بواسطة المستخدم #{log.admin_user_id}
                  </span>
                  {log.ip_address && (
                    <span className="text-xs text-muted-foreground/40 font-mono">
                      • {log.ip_address}
                    </span>
                  )}
                </div>
                {(log.old_value || log.new_value) && (
                  <div className="mt-1 text-xs font-mono text-muted-foreground/50 space-y-0.5">
                    {log.old_value && (
                      <div>
                        <span className="text-red-500/50">قبل: </span>
                        {JSON.stringify(log.old_value).slice(0, 100)}
                        {JSON.stringify(log.old_value).length > 100 && '...'}
                      </div>
                    )}
                    {log.new_value && (
                      <div>
                        <span className="text-emerald-500/50">بعد: </span>
                        {JSON.stringify(log.new_value).slice(0, 100)}
                        {JSON.stringify(log.new_value).length > 100 && '...'}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
            <span className="text-[10px] text-muted-foreground/30 whitespace-nowrap ml-2">
              {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}