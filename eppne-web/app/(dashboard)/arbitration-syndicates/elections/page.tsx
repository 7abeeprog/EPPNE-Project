// app/(dashboard)/arbitration-syndicates/elections/page.tsx
'use client';

import { useElections } from '@/hooks/arbitration-syndicates/useElections';
import ElectionCard from '@/components/arbitration-syndicates/ElectionCard';
import { Loader2, Vote, Plus } from 'lucide-react';
import Link from 'next/link';

export default function ElectionsPage() {
  const { data: elections, isLoading } = useElections();

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
        <h1 className="text-2xl font-bold text-foreground/90">🗳️ الانتخابات النقابية</h1>
        <Link
          href="/arbitration-syndicates/elections/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          انتخاب جديد
        </Link>
      </div>

      {elections?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <Vote className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد انتخابات</p>
          <p className="text-sm">نظم أول انتخابات نقابية</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {elections?.map((election) => (
            <ElectionCard key={election.id} election={election} />
          ))}
        </div>
      )}
    </div>
  );
}