// app/(dashboard)/automation/executions/[executionId]/page.tsx
'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { getExecution, getExecutionLogs } from '@/services/automation';
import { useExecutionWebSocket } from '@/hooks/automation/useExecutionWebSocket';
import ExecutionStatusBadge from '@/components/automation/ExecutionStatusBadge';
import { ArrowLeft, Loader2, Clock, Database, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns/ar';
import { useEffect, useState } from 'react';

export default function ExecutionDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const executionId = parseInt(params.executionId as string);

  // ===== جلب البيانات =====
  const { data: execution, isLoading: isLoadingExecution } = useQuery({
    queryKey: ['execution', executionId],
    queryFn: () => getExecution(executionId).then(res => res.data),
    refetchInterval: 5000, // تحديث دوري احتياطي (بالإضافة إلى WebSocket)
  });

  const { data: logs, isLoading: isLoadingLogs } = useQuery({
    queryKey: ['execution-logs', executionId],
    queryFn: () => getExecutionLogs(executionId).then(res => res.data),
    refetchInterval: 5000,
  });

  // ===== WebSocket للتحديث الفوري =====
  const { isConnected, lastMessage } = useExecutionWebSocket(executionId);
  const [liveNodeStatus, setLiveNodeStatus] = useState<Record<string, string>>({});

  useEffect(() => {
    if (lastMessage?.type === 'node_update' || lastMessage?.type === 'execution_update') {
      // تحديث حالة العقدة بناءً على الرسالة الواردة
      if (lastMessage.data?.node_id) {
        setLiveNodeStatus(prev => ({
          ...prev,
          [lastMessage.data.node_id]: lastMessage.data.status || 'RUNNING',
        }));
      }
    }
  }, [lastMessage]);

  if (isLoadingExecution || isLoadingLogs) {
    return (
      <div className="flex justify-center items-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!execution) {
    return (
      <div className="flex flex-col items-center justify-center h-screen text-muted-foreground/60">
        <p className="text-lg">التنفيذ غير موجود</p>
        <button onClick={() => router.back()} className="mt-4 text-primary hover:underline">
          العودة
        </button>
      </div>
    );
  }

  // بناء خريطة العقد من سجل التنفيذ
  const nodeLogsMap = logs?.reduce((acc, log) => {
    acc[log.node_id] = log;
    return acc;
  }, {} as Record<string, any>);

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* الهيدر */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.back()}
            className="p-2 rounded-xl hover:bg-white/10 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-muted-foreground/60" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-foreground/90">📊 تفاصيل التنفيذ</h1>
            <div className="flex items-center gap-3 mt-1">
              <span className="font-mono text-sm text-muted-foreground/60">#{execution.id}</span>
              <ExecutionStatusBadge status={execution.status} />
              <span className="text-xs text-muted-foreground/40">
                {execution.status === 'RUNNING' && isConnected ? (
                  <span className="flex items-center gap-1 text-emerald-500">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    متصل (تحديث فوري)
                  </span>
                ) : null}
              </span>
            </div>
          </div>
        </div>
        <div className="text-xs text-muted-foreground/40 text-left">
          <div>بدأ: {new Date(execution.started_at).toLocaleString('ar-EG')}</div>
          {execution.finished_at && (
            <div>انتهى: {new Date(execution.finished_at).toLocaleString('ar-EG')}</div>
          )}
        </div>
      </div>

      {/* ملخص سريع */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 text-center">
          <div className="text-xs text-muted-foreground/50">المحفز</div>
          <div className="text-sm font-medium text-foreground/80 mt-1">{execution.triggered_by}</div>
        </div>
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 text-center">
          <div className="text-xs text-muted-foreground/50">عدد المحاولات</div>
          <div className="text-sm font-medium text-foreground/80 mt-1">{execution.retry_count}</div>
        </div>
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 text-center">
          <div className="text-xs text-muted-foreground/50">عدد العقد</div>
          <div className="text-sm font-medium text-foreground/80 mt-1">{logs?.length || 0}</div>
        </div>
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 text-center">
          <div className="text-xs text-muted-foreground/50">المدة</div>
          <div className="text-sm font-medium text-foreground/80 mt-1">
            {execution.finished_at 
              ? formatDistanceToNow(new Date(execution.finished_at), { addSuffix: true })
              : 'جاري...'}
          </div>
        </div>

        {/* ===== المود الجديد: عنوان IP ===== */}
        {execution.trigger_ip && (
          <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 text-center">
            <div className="text-xs text-muted-foreground/50">عنوان IP</div>
            <div className="text-sm font-mono text-foreground/80 mt-1">{execution.trigger_ip}</div>
          </div>
        )}

        {/* ===== المود الجديد: User-Agent ===== */}
        {execution.trigger_user_agent && (
          <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 text-center col-span-2">
            <div className="text-xs text-muted-foreground/50">نوع المتصفح (User-Agent)</div>
            <div className="text-sm font-mono text-foreground/60 mt-1 truncate">{execution.trigger_user_agent}</div>
          </div>
        )}
      </div>

      {/* مسار التنفيذ (العقد) */}
      <div>
        <h2 className="text-lg font-semibold text-foreground/90 mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-primary" />
          مسار التنفيذ
        </h2>
        <div className="space-y-3">
          {logs?.map((log) => {
            const liveStatus = liveNodeStatus[log.node_id] || log.status;
            const isRunning = liveStatus === 'RUNNING' || (execution.status === 'RUNNING' && log.status === 'PENDING');
            
            return (
              <div
                key={log.id}
                className={cn(
                  "p-4 rounded-2xl border transition-all duration-500 bg-card/20 backdrop-blur-sm",
                  isRunning ? "border-blue-500/50 shadow-[0_0_30px_rgba(59,130,246,0.1)]" : "border-white/10",
                  liveStatus === 'SUCCESS' ? "border-emerald-500/30" : "",
                  liveStatus === 'FAILED' ? "border-red-500/30 shadow-[0_0_30px_rgba(239,68,68,0.1)]" : "",
                )}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      "w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold",
                      isRunning ? "bg-blue-500/20 text-blue-500 animate-pulse" : "bg-white/5 text-muted-foreground/60"
                    )}>
                      {log.node_type.substring(0, 2)}
                    </div>
                    <div>
                      <div className="font-medium text-foreground/80 text-sm">
                        {log.node_id}
                        <span className="text-xs text-muted-foreground/40 mr-2">({log.node_type})</span>
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <ExecutionStatusBadge 
                          status={isRunning ? 'RUNNING' : liveStatus as any} 
                          showLabel={false}
                        />
                        <span className="text-[10px] text-muted-foreground/40">
                          {log.started_at && formatDistanceToNow(new Date(log.started_at), { addSuffix: true })}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* إظهار المدخلات/المخرجات عند التوسيع (اختياري) */}
                {(log.input_data || log.output_data || log.error_message) && (
                  <div className="mt-3 pt-3 border-t border-white/10 text-xs space-y-1 font-mono">
                    {log.input_data && (
                      <div>
                        <span className="text-muted-foreground/50">📥 المدخلات: </span>
                        <span className="text-foreground/60">{JSON.stringify(log.input_data)}</span>
                      </div>
                    )}
                    {log.output_data && (
                      <div>
                        <span className="text-muted-foreground/50">📤 المخرجات: </span>
                        <span className="text-foreground/60">{JSON.stringify(log.output_data)}</span>
                      </div>
                    )}
                    {log.error_message && (
                      <div className="text-red-500/80">
                        ❌ {log.error_message}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* سياق التنفيذ (متقدم) */}
      {execution.context && Object.keys(execution.context).length > 0 && (
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <h3 className="text-sm font-medium text-foreground/70 mb-2 flex items-center gap-2">
            <Database className="w-4 h-4 text-muted-foreground/50" />
            سياق التنفيذ
          </h3>
          <pre className="text-xs font-mono text-muted-foreground/60 overflow-auto max-h-32 p-2 rounded-lg bg-black/20">
            {JSON.stringify(execution.context, null, 2)}
          </pre>
        </div>
      )}

      {/* خطأ عام إن وجد */}
      {execution.error_message && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-500/80 text-sm">
          <span className="font-bold">❌ خطأ عام:</span> {execution.error_message}
        </div>
      )}
    </div>
  );
}