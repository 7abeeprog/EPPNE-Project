// app/(dashboard)/zamakana/page.tsx
'use client';

import { useNodes } from '@/hooks/zamakana/useNodes';
import { useCampaigns } from '@/hooks/zamakana/useCampaigns';
import { useScenarios } from '@/hooks/zamakana/useScenarios';
import { useKnowledgeGraph } from '@/hooks/zamakana/useKnowledgeGraph';
import { Loader2, Network, Clock, Brain, Globe } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

export default function ZamakanaDashboard() {
  const { data: nodes, isLoading: nLoading } = useNodes({ limit: 100 });
  const { data: campaigns, isLoading: cLoading } = useCampaigns();
  const { data: scenarios, isLoading: sLoading } = useScenarios();
  const { data: graph, isLoading: gLoading } = useKnowledgeGraph({ limit: 100 });

  const isLoading = nLoading || cLoading || sLoading || gLoading;

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const stats = [
    { label: 'عقد معرفية', value: nodes?.length || 0, icon: Network, color: 'text-blue-500' },
    { label: 'حملات كوكبية', value: campaigns?.length || 0, icon: Globe, color: 'text-emerald-500' },
    { label: 'سيناريوهات', value: scenarios?.length || 0, icon: Brain, color: 'text-purple-500' },
    { label: 'صلات معرفية', value: graph?.edges?.length || 0, icon: Network, color: 'text-amber-500' },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">🧠 الزمكان</h1>
          <p className="text-sm text-muted-foreground/70">محرك المعرفة والتأثير عبر الزمن</p>
        </div>
        <Link
          href="/zamakana/nodes/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Network className="w-4 h-4" />
          عقدة جديدة
        </Link>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map((stat, idx) => (
          <div key={idx} className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
            <div className="flex items-center gap-2">
              <stat.icon className={cn("w-4 h-4", stat.color)} />
              <span className="text-xs text-muted-foreground/50">{stat.label}</span>
            </div>
            <p className="mt-2 text-lg font-bold text-foreground/90">{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          href="/zamakana/nodes"
          className="p-6 rounded-2xl bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <Network className="w-8 h-8 mx-auto text-blue-500" />
          <h3 className="mt-2 font-medium">عقد المعرفة</h3>
          <p className="text-sm text-muted-foreground/50">استكشاف الحقب والابتكارات</p>
        </Link>
        <Link
          href="/zamakana/campaigns"
          className="p-6 rounded-2xl bg-gradient-to-br from-emerald-500/10 to-teal-500/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <Globe className="w-8 h-8 mx-auto text-emerald-500" />
          <h3 className="mt-2 font-medium">حملات كوكبية</h3>
          <p className="text-sm text-muted-foreground/50">تجميع ساعات تطوعية عالمية</p>
        </Link>
        <Link
          href="/zamakana/scenarios"
          className="p-6 rounded-2xl bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <Brain className="w-8 h-8 mx-auto text-purple-500" />
          <h3 className="mt-2 font-medium">سيناريوهات مستقبلية</h3>
          <p className="text-sm text-muted-foreground/50">محاكاة المستقبل بالذكاء الاصطناعي</p>
        </Link>
      </div>
    </div>
  );
}