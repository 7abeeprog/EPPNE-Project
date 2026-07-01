// app/(dashboard)/ai/approvals/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getPendingApprovals, resolveApproval } from '@/services/ai-agents';
import { useAIAgentStore } from '@/store/aiAgentStore';
import { useApprovalWebSocket } from '@/hooks/ai-agents/useApprovalWebSocket';
import ApprovalResolver from '@/components/ai-agents/ApprovalResolver';
import { formatDistanceToNow } from 'date-fns/ar';
import { 
  Loader2, CheckCircle, XCircle, Clock, 
  AlertTriangle, Wallet, FileSignature, 
  Power, Code, User, Calendar 
} from 'lucide-react';
import { cn } from '@/lib/utils';

const actionIcons = {
  TRANSFER_FUNDS: { icon: Wallet, label: 'تحويل أموال', color: 'text-amber-500' },
  SIGN_CONTRACT: { icon: FileSignature, label: 'توقيع عقد', color: 'text-blue-500' },
  SHUTDOWN_FACTORY: { icon: Power, label: 'إيقاف تشغيل', color: 'text-red-500' },
  DEPLOY_CODE: { icon: Code, label: 'نشر كود', color: 'text-purple-500' },
};

export default function ApprovalsPage() {
  const queryClient = useQueryClient();
  const { pendingApprovals, setPendingApprovals, pendingApprovalsCount } = useAIAgentStore();
  const [selectedApproval, setSelectedApproval] = useState<number | null>(null);
  
  // 🔥 تفعيل WebSocket للتحديثات الفورية
  const { isConnected } = useApprovalWebSocket();

  // جلب الطلبات المعلقة
  const { data, isLoading } = useQuery({
    queryKey: ['pending-approvals'],
    queryFn: () => getPendingApprovals().then(res => res.data),
    refetchInterval: 30000, // تحديث دوري احتياطي
    staleTime: 5000,
  });

  // تحديث المخزن عند جلب البيانات
  useEffect(() => {
    if (data) {
      setPendingApprovals(data);
    }
  }, [data, setPendingApprovals]);

  // حل الطلب (Mutation)
  const resolveMutation = useMutation({
    mutationFn: ({ approvalId, data }: { approvalId: number; data: any }) =>
      resolveApproval(approvalId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['pending-approvals'] });
      // حذف من المخزن (سيتم عبر WebSocket أيضاً)
    },
  });

  const handleResolve = (approvalId: number, status: 'APPROVED' | 'REJECTED', feedback?: string) => {
    resolveMutation.mutate({
      approvalId,
      data: { status, human_feedback: feedback || '' }
    });
    setSelectedApproval(null);
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* الهيدر */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90 flex items-center gap-3">
            🛡️ لوحة الموافقات البشرية
            <span className="text-sm font-normal text-muted-foreground/60 flex items-center gap-1.5">
              <span className={cn(
                "w-2 h-2 rounded-full",
                isConnected ? "bg-emerald-500 animate-pulse" : "bg-red-500"
              )} />
              {isConnected ? 'اتصال مباشر' : 'غير متصل'}
            </span>
          </h1>
          <p className="text-sm text-muted-foreground/70">
            طلبات تحتاج إلى تدخل بشري ({pendingApprovalsCount} معلق)
          </p>
        </div>
      </div>

      {/* قائمة الطلبات */}
      {pendingApprovals.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60 rounded-3xl bg-card/20 backdrop-blur-xl border border-white/10">
          <CheckCircle className="w-12 h-12 mx-auto mb-4 text-emerald-500/30" />
          <p className="text-lg">لا توجد طلبات معلقة</p>
          <p className="text-sm">جميع العمليات في انتظار قرارك ستظهر هنا</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {pendingApprovals.map((approval) => {
            const action = actionIcons[approval.action_type] || { icon: AlertTriangle, label: approval.action_type, color: 'text-gray-500' };
            const Icon = action.icon;

            return (
              <div
                key={approval.id}
                className={cn(
                  "p-5 rounded-2xl bg-card/30 backdrop-blur-xl border transition-all duration-300",
                  "border-white/10 hover:border-primary/30 hover:shadow-[0_0_40px_-15px_rgba(var(--primary-rgb),0.15)]",
                  approval.action_type === 'TRANSFER_FUNDS' && "border-amber-500/20"
                )}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className={cn(
                      "p-2.5 rounded-xl bg-white/5",
                      action.color
                    )}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-foreground/90">
                          {action.label}
                        </h3>
                        <span className="text-xs text-amber-500/70 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground/50">
                        <span className="flex items-center gap-1">
                          <User className="w-3 h-3" />
                          الوكيل #{approval.agent_id}
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          الطلب: #{approval.id}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* زر الحل */}
                  <button
                    onClick={() => setSelectedApproval(approval.id)}
                    className="px-4 py-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors text-sm font-medium"
                  >
                    مراجعة
                  </button>
                </div>

                {/* عرض الـ Payload (ملخص) */}
                <div className="mt-3 p-3 rounded-xl bg-white/5 border border-white/5 text-xs font-mono text-muted-foreground/60 overflow-auto max-h-20">
                  {Object.entries(approval.proposed_payload)
                    .slice(0, 3)
                    .map(([key, value]) => (
                      <div key={key} className="flex gap-2">
                        <span className="text-foreground/50">{key}:</span>
                        <span>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
                      </div>
                    ))}
                  {Object.keys(approval.proposed_payload).length > 3 && (
                    <div className="text-muted-foreground/40">+ {Object.keys(approval.proposed_payload).length - 3} حقول أخرى</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* مودال حل الطلب */}
      {selectedApproval && (
        <ApprovalResolver
          approval={pendingApprovals.find(a => a.id === selectedApproval)!}
          onClose={() => setSelectedApproval(null)}
          onResolve={handleResolve}
          isResolving={resolveMutation.isPending}
        />
      )}
    </div>
  );
}