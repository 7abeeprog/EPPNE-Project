// app/(dashboard)/ai-agents/create/page.tsx
'use client';

import { ArrowLeft, Brain } from 'lucide-react';
import { useRouter } from 'next/navigation';
import AgentForm from '@/components/ai-agents/AgentForm';

export default function CreateAgentPage() {
  const router = useRouter();

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <button
        onClick={() => router.push('/ai-agents')}
        className="flex items-center gap-2 text-sm text-muted-foreground/60 hover:text-foreground/80 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        العودة إلى الوكلاء
      </button>

      <div className="rounded-3xl bg-card/20 backdrop-blur-2xl border border-white/10 p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-xl bg-primary/20 text-primary">
            <Brain className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground/90">🧠 إنشاء وكيل جديد</h1>
            <p className="text-xs text-muted-foreground/50">أضف وكيل ذكاء اصطناعي سيادي لأتمتة المهام</p>
          </div>
        </div>

        <AgentForm />
      </div>
    </div>
  );
}