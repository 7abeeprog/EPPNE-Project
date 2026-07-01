// app/(dashboard)/automation/workflows/[id]/executions/page.tsx
'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { getWorkflowExecutions } from '@/services/automation';
import ExecutionStatusBadge from '@/components/automation/ExecutionStatusBadge';
import { formatDistanceToNow } from 'date-fns/ar';
import { Loader2, Search, RefreshCw, Eye } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function ExecutionsPage() {
  const params = useParams();
  const router = useRouter();
  const workflowId = parseInt(params.id as string);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['executions', workflowId, statusFilter],
    queryFn: () => getWorkflowExecutions(workflowId, { 
      limit: 50, 
      ...(statusFilter && { status: statusFilter })
    }).then(res => res.data),
    refetchInterval: 10000, // تحديث كل 10 ثوانٍ لإظهار التنفيذات الجديدة
    staleTime: 5000,
  });

  // فلترة البحث
  const filtered = data?.filter(exec => 
    exec.id.toString().includes(searchTerm) ||
    exec.triggered_by.includes(searchTerm)
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">📋 سجل التنفيذات</h1>
          <p className="text-sm text-muted-foreground/70">جميع عمليات تشغيل سير العمل</p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isRefetching}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors text-sm"
        >
          <RefreshCw className={cn("w-4 h-4", isRefetching && "animate-spin")} />
          تحديث
        </button>
      </div>

      {/* أدوات التصفية والبحث */}
      <div className="flex flex-wrap items-center gap-3 p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <div className="flex items-center gap-2 flex-1 min-w-[200px] bg-white/5 rounded-xl px-3 py-2 border border-white/5">
          <Search className="w-4 h-4 text-muted-foreground/50" />
          <input
            type="text"
            placeholder="ابحث برقم التنفيذ أو المحفز..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent border-0 outline-none text-sm w-full text-foreground/80 placeholder:text-muted-foreground/40"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-foreground/80 outline-none focus:border-primary/30"
        >
          <option value="">كل الحالات</option>
          <option value="PENDING">قيد الانتظار</option>
          <option value="RUNNING">قيد التشغيل</option>
          <option value="SUCCESS">تم بنجاح</option>
          <option value="FAILED">فشل</option>
          <option value="RETRY">إعادة محاولة</option>
          <option value="CANCELLED">ملغي</option>
        </select>
      </div>

      {/* الجدول */}
      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : filtered?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <div className="text-4xl mb-4">📭</div>
          <p className="text-lg">لا توجد تنفيذات</p>
          <p className="text-sm">سيظهر هنا سجل جميع عمليات تشغيل سير العمل</p>
        </div>
      ) : (
        <div className="rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-white/5 border-b border-white/10">
                <tr>
                  <th className="text-right px-4 py-3 text-muted-foreground/60 font-medium">#</th>
                  <th className="text-right px-4 py-3 text-muted-foreground/60 font-medium">المحفز</th>
                  <th className="text-right px-4 py-3 text-muted-foreground/60 font-medium">الحالة</th>
                  <th className="text-right px-4 py-3 text-muted-foreground/60 font-medium">المدة</th>
                  <th className="text-right px-4 py-3 text-muted-foreground/60 font-medium">التاريخ</th>
                  <th className="text-right px-4 py-3 text-muted-foreground/60 font-medium">الإجراء</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filtered?.map((exec) => {
                  const duration = exec.finished_at 
                    ? formatDistanceToNow(new Date(exec.finished_at), { addSuffix: true })
                    : exec.status === 'RUNNING' 
                      ? 'جارٍ التنفيذ...' 
                      : '—';
                  
                  return (
                    <tr key={exec.id} className="hover:bg-white/5 transition-colors">
                      <td className="px-4 py-3 font-mono text-foreground/80">#{exec.id}</td>
                      <td className="px-4 py-3 text-foreground/70 truncate max-w-[150px]">
                        {exec.triggered_by}
                        {exec.trigger_payload && Object.keys(exec.trigger_payload).length > 0 && (
                          <span className="text-[10px] text-muted-foreground/40 ml-1">
                            ({Object.keys(exec.trigger_payload).length} حقول)
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <ExecutionStatusBadge status={exec.status} />
                      </td>
                      <td className="px-4 py-3 text-foreground/60 text-xs font-mono">
                        {duration}
                      </td>
                      <td className="px-4 py-3 text-foreground/50 text-xs">
                        {new Date(exec.created_at).toLocaleString('ar-EG')}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => router.push(`/automation/executions/${exec.id}`)}
                          className="p-1.5 rounded-lg hover:bg-white/10 transition-colors text-muted-foreground/50 hover:text-foreground/80"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}