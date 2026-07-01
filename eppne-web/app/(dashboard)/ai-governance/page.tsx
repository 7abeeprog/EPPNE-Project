// app/(dashboard)/ai-governance/page.tsx
'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getMyAgents } from '@/services/ai-agents';
import UsageDashboard from '@/components/ai-governance/UsageDashboard';
import QuotaManager from '@/components/ai-governance/QuotaManager';
import AuditLogViewer from '@/components/ai-governance/AuditLogViewer';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Loader2, Bot, Gauge, Shield } from 'lucide-react';

export default function AIGovernancePage() {
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(null);

  const { data: agents, isLoading } = useQuery({
    queryKey: ['my-agents'],
    queryFn: () => getMyAgents().then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!agents || agents.length === 0) {
    return (
      <div className="p-6 text-center text-muted-foreground/60">
        <Bot className="w-12 h-12 mx-auto mb-4 opacity-30" />
        <p className="text-lg">لا توجد وكلاء ذكاء اصطناعي</p>
        <p className="text-sm">أنشئ وكيلاً أولاً للبدء في إدارة حوكمته</p>
      </div>
    );
  }

  const selectedAgent = agents.find(a => a.id === selectedAgentId) || agents[0];
  const currentAgentId = selectedAgentId || agents[0].id;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">⚖️ حوكمة الذكاء الاصطناعي</h1>
          <p className="text-sm text-muted-foreground/70">الدستور الرقمي للوكلاء السياديين</p>
        </div>
      </div>

      {/* اختيار الوكيل */}
      <div className="flex flex-wrap gap-2">
        {agents.map((agent) => (
          <button
            key={agent.id}
            onClick={() => setSelectedAgentId(agent.id)}
            className={cn(
              "px-4 py-2 rounded-xl border transition-all duration-200 text-sm",
              currentAgentId === agent.id
                ? "border-primary/50 bg-primary/20 text-primary"
                : "border-white/10 bg-white/5 text-muted-foreground/70 hover:bg-white/10"
            )}
          >
            🤖 {agent.name}
          </button>
        ))}
      </div>

      {/* تبويبات الحوكمة */}
      <Tabs defaultValue="dashboard" className="space-y-4">
        <TabsList className="bg-card/20 backdrop-blur-xl border border-white/10 p-1 rounded-2xl">
          <TabsTrigger value="dashboard" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary rounded-xl px-4 py-2 text-sm">
            <Gauge className="w-4 h-4 mr-1.5" />
            الاستهلاك
          </TabsTrigger>
          <TabsTrigger value="quotas" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary rounded-xl px-4 py-2 text-sm">
            <Bot className="w-4 h-4 mr-1.5" />
            الحصص والحدود
          </TabsTrigger>
          <TabsTrigger value="audit" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary rounded-xl px-4 py-2 text-sm">
            <Shield className="w-4 h-4 mr-1.5" />
            سجل التدقيق
          </TabsTrigger>
        </TabsList>

        <TabsContent value="dashboard">
          <UsageDashboard agentId={currentAgentId} agentName={selectedAgent.name} />
        </TabsContent>

        <TabsContent value="quotas">
          <QuotaManager agentId={currentAgentId} />
        </TabsContent>

        <TabsContent value="audit">
          <AuditLogViewer agentId={currentAgentId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}