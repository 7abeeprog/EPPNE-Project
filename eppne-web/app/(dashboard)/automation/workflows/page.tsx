// app/(dashboard)/automation/workflows/page.tsx
'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { AutomationService } from '@/services/automation.service'; // ✅ تغيير الاستيراد
import { Play, Trash2, Edit, Plus, Power, PowerOff, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import ConfirmationModal from '@/components/ui/ConfirmationModal';
import type { components } from '@/src/lib/api-types';

type Workflow = components['schemas']['WorkflowResponse'];

export default function WorkflowsListPage() {
  const queryClient = useQueryClient();
  const [deleteTarget, setDeleteTarget] = useState<Workflow | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['workflows'],
    queryFn: () => AutomationService.listWorkflows({ limit: 50 }), // ✅ استخدام AutomationService
    staleTime: 2 * 60 * 1000,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => AutomationService.deleteWorkflow(id, true), // ✅ استخدام AutomationService
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workflows'] }),
  });

  const triggerMutation = useMutation({
    mutationFn: (id: number) => AutomationService.triggerWorkflowManual(id, {}), // ✅ استخدام AutomationService
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workflows'] }),
  });

  const toggleActive = (workflow: Workflow) => {
    // يمكن إضافة نقطة نهاية لتحديث is_active
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">⚙️ سير العمل الآلي</h1>
          <p className="text-sm text-muted-foreground/70">إدارة وتشغيل مهام الأتمتة المتقدمة</p>
        </div>
        <Link
          href="/automation/workflows/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          سير عمل جديد
        </Link>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : data?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <div className="text-4xl mb-4">🤖</div>
          <p className="text-lg">لا توجد سير عمل</p>
          <p className="text-sm">أنشئ سير العمل الأول لأتمتة مهامك</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {data?.map((wf) => (
            <div
              key={wf.id}
              className={cn(
                "flex items-center gap-4 p-4 rounded-2xl bg-card/30 backdrop-blur-xl border transition-all duration-300",
                wf.is_active ? "border-white/10 hover:border-primary/30" : "border-white/5 opacity-60 hover:opacity-100"
              )}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3">
                  <h3 className="font-semibold text-foreground/90 truncate">{wf.name}</h3>
                  <span className={cn(
                    "text-xs px-2 py-0.5 rounded-full border",
                    wf.is_active ? "border-emerald-500/30 text-emerald-500" : "border-gray-500/30 text-gray-500"
                  )}>
                    {wf.is_active ? 'نشط' : 'موقف'}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-muted-foreground/60">
                    {wf.trigger_type}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground/60 truncate mt-0.5">
                  {wf.description || 'بدون وصف'} • {wf.nodes?.length || 0} عقدة • webhook: {wf.webhook_path || '—'}
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {wf.trigger_type === 'MANUAL' && (
                  <button
                    onClick={() => triggerMutation.mutate(wf.id)}
                    disabled={triggerMutation.isPending}
                    className="p-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors disabled:opacity-50"
                    title="تشغيل يدوي"
                  >
                    <Play className="w-4 h-4" />
                  </button>
                )}
                <Link
                  href={`/automation/workflows/${wf.id}`}
                  className="p-2 rounded-xl bg-white/5 hover:bg-white/10 transition-colors"
                >
                  <Edit className="w-4 h-4 text-muted-foreground/60" />
                </Link>
                <button
                  onClick={() => setDeleteTarget(wf)}
                  className="p-2 rounded-xl hover:bg-red-500/10 transition-colors"
                >
                  <Trash2 className="w-4 h-4 text-red-500/50 hover:text-red-500" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <ConfirmationModal
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (deleteTarget) {
            deleteMutation.mutate(deleteTarget.id);
            setDeleteTarget(null);
          }
        }}
        title="حذف سير العمل"
        message={`هل أنت متأكد من حذف سير العمل "${deleteTarget?.name}"؟ سيؤدي هذا إلى إيقاف تشغيله وحذف جميع سجلات التنفيذ.`}
        confirmText="حذف نهائي"
        type="danger"
        entityName={deleteTarget?.name}
        primaryColor="#ef4444"
        requiresTyping={true}
      />
    </div>
  );
}