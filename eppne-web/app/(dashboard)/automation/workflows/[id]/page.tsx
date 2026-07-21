// app/(dashboard)/automation/workflows/[id]/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getWorkflow, updateWorkflow, toggleWorkflowActive } from '@/services/automation.service';
import WorkflowBuilder from '@/components/automation/WorkflowBuilder';
import TriggerSettings from '@/components/automation/TriggerSettings';
import ExecutionsPage from '@/components/automation/ExecutionsPage'; // المود الجديد
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Loader2, Save, Power, PowerOff, ArrowLeft } from 'lucide-react';
import { cn } from '@/lib/utils';
import ExecutionsPage from './executions/page';

export default function WorkflowEditorPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const workflowId = params.id === 'create' ? null : parseInt(params.id as string);
  const isNew = !workflowId;

  // ===== جلب البيانات =====
  const { data, isLoading } = useQuery({
    queryKey: ['workflow', workflowId],
    queryFn: () => (workflowId ? getWorkflow(workflowId).then(res => res.data) : null),
    enabled: !!workflowId,
    staleTime: 2 * 60 * 1000,
  });

  // ===== حالة المحرر =====
  const [workflowName, setWorkflowName] = useState('');
  const [workflowDescription, setWorkflowDescription] = useState('');
  const [triggerType, setTriggerType] = useState<'MANUAL' | 'WEBHOOK' | 'SCHEDULE' | 'EVENT'>('MANUAL');
  const [triggerConfig, setTriggerConfig] = useState<Record<string, any>>({});
  const [isActive, setIsActive] = useState(true);
  const [webhookPath, setWebhookPath] = useState<string | null>(null);

  // تحديث الحالة عند تحميل البيانات
  useEffect(() => {
    if (data) {
      setWorkflowName(data.name);
      setWorkflowDescription(data.description || '');
      setTriggerType(data.trigger_type);
      setTriggerConfig(data.trigger_config || {});
      setIsActive(data.is_active);
      setWebhookPath(data.webhook_path || null);
    }
  }, [data]);

  // ===== حفظ التغييرات =====
  const updateMutation = useMutation({
    mutationFn: (payload: any) => {
      if (isNew) {
        return Promise.reject('Use WorkflowBuilder save');
      }
      return updateWorkflow(workflowId!, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      queryClient.invalidateQueries({ queryKey: ['workflow', workflowId] });
    },
  });

  // ===== تغيير الحالة (نشط/موقف) =====
  const toggleMutation = useMutation({
    mutationFn: () => toggleWorkflowActive(workflowId!, !isActive),
    onSuccess: () => {
      setIsActive(!isActive);
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      queryClient.invalidateQueries({ queryKey: ['workflow', workflowId] });
    },
  });

  // ===== معالج تغيير المشغل =====
  const handleTriggerChange = (type: string, config: Record<string, any>) => {
    setTriggerType(type as any);
    setTriggerConfig(config);
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  // إذا كان جديداً، نمرر مباشرة إلى WorkflowBuilder مع بيانات افتراضية
  if (isNew) {
    return (
      <div className="h-screen">
        <WorkflowBuilder
          initialWorkflow={undefined}
          isNew={true}
        />
      </div>
    );
  }

  // ===== العرض للكيانات الموجودة =====
  return (
    <div className="flex flex-col h-screen bg-background">
      {/* الهيدر */}
      <div className="flex items-center justify-between p-4 border-b border-white/10 bg-card/30 backdrop-blur-xl shrink-0">
        <div className="flex items-center gap-4 flex-1">
          <button
            onClick={() => router.push('/automation/workflows')}
            className="p-2 rounded-xl hover:bg-white/10 transition-colors"
          >
            <ArrowLeft className="w-4 h-4 text-muted-foreground/60" />
          </button>
          <input
            type="text"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            className="bg-transparent border-0 text-xl font-bold text-foreground/90 outline-none placeholder:text-muted-foreground/40 w-64"
          />
          <span className="text-xs px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-muted-foreground/50">
            ID: {workflowId}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {/* زر التفعيل */}
          <button
            onClick={() => toggleMutation.mutate()}
            disabled={toggleMutation.isPending}
            className={cn(
              "flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-300",
              isActive
                ? "bg-emerald-500/20 text-emerald-500 border border-emerald-500/30 hover:bg-emerald-500/30"
                : "bg-gray-500/20 text-gray-500 border border-gray-500/30 hover:bg-gray-500/30"
            )}
          >
            {toggleMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : isActive ? <Power className="w-4 h-4" /> : <PowerOff className="w-4 h-4" />}
            {isActive ? 'نشط' : 'موقف'}
          </button>
          <button
            onClick={() => {
              updateMutation.mutate({
                name: workflowName,
                description: workflowDescription,
                trigger_type: triggerType,
                trigger_config: triggerConfig,
                is_active: isActive,
              });
            }}
            disabled={updateMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
          >
            {updateMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            حفظ
          </button>
        </div>
      </div>

      {/* المحتوى الرئيسي مع تبويبات */}
      <div className="flex-1 overflow-hidden">
        <Tabs defaultValue="design" className="h-full flex flex-col">
          <div className="px-4 pt-3 border-b border-white/10 bg-card/10 backdrop-blur-sm shrink-0">
            <TabsList className="bg-transparent gap-6">
              <TabsTrigger value="design" className="data-[state=active]:text-primary data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none pb-2 text-muted-foreground/60">
                🎨 تصميم سير العمل
              </TabsTrigger>
              <TabsTrigger value="settings" className="data-[state=active]:text-primary data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none pb-2 text-muted-foreground/60">
                ⚙️ إعدادات المشغل
              </TabsTrigger>
              {/* ===== المود الجديد: تبويب سجل التنفيذات ===== */}
              <TabsTrigger value="executions" className="data-[state=active]:text-primary data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none pb-2 text-muted-foreground/60">
                📋 سجل التنفيذات
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="design" className="flex-1 overflow-hidden m-0 p-0">
            <WorkflowBuilder
              initialWorkflow={data || undefined}
              isNew={false}
            />
          </TabsContent>

          <TabsContent value="settings" className="flex-1 overflow-y-auto m-0 p-6">
            <div className="max-w-3xl mx-auto space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-foreground/90">⚙️ إعدادات المشغل</h3>
                <p className="text-sm text-muted-foreground/60">حدد كيف سيتم تشغيل سير العمل هذا</p>
              </div>

              <TriggerSettings
                triggerType={triggerType}
                triggerConfig={triggerConfig}
                webhookPath={webhookPath}
                onChange={handleTriggerChange}
              />

              <div className="p-4 rounded-2xl bg-amber-500/5 border border-amber-500/20">
                <p className="text-xs text-amber-500/70 flex items-center gap-2">
                  💡 تذكر حفظ سير العمل بعد تغيير الإعدادات.
                </p>
              </div>
            </div>
          </TabsContent>

          {/* ===== المود الجديد: محتوى تبويب سجل التنفيذات ===== */}
          <TabsContent value="executions" className="flex-1 overflow-hidden m-0 p-0">
            <ExecutionsPage workflowId={workflowId} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}