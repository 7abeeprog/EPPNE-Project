// app/(dashboard)/zamakana/scenarios/page.tsx
'use client';

import { useScenarios } from '@/hooks/zamakana/useScenarios';
import ScenarioCard from '@/components/zamakana/ScenarioCard';
import { Loader2, Brain, Plus } from 'lucide-react';
import Link from 'next/link';

export default function ScenariosPage() {
  const { data: scenarios, isLoading } = useScenarios();

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground/90">🔮 السيناريوهات المستقبلية</h1>
        <Link
          href="/zamakana/scenarios/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          سيناريو جديد
        </Link>
      </div>

      {scenarios?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <Brain className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد سيناريوهات</p>
          <p className="text-sm">استكشف المستقبل بتحليل الذكاء الاصطناعي</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {scenarios?.map((scenario) => (
            <ScenarioCard key={scenario.id} scenario={scenario} />
          ))}
        </div>
      )}
    </div>
  );
}