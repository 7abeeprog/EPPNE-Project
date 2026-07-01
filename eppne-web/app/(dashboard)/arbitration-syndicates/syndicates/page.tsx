// app/(dashboard)/arbitration-syndicates/syndicates/page.tsx
'use client';

import { useSyndicates, useJoinSyndicate } from '@/hooks/arbitration-syndicates/useSyndicates';
import SyndicateCard from '@/components/arbitration-syndicates/SyndicateCard';
import { Loader2, Building2, Plus } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

export default function SyndicatesPage() {
  const { data: syndicates, isLoading } = useSyndicates();
  const joinSyndicate = useJoinSyndicate();
  const [joiningId, setJoiningId] = useState<number | null>(null);

  const handleJoin = (syndicateId: number) => {
    setJoiningId(syndicateId);
    joinSyndicate.mutate(
      { syndicateId },
      {
        onSuccess: () => setJoiningId(null),
      }
    );
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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground/90">🏛️ النقابات</h1>
        <Link
          href="/arbitration-syndicates/syndicates/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          نقابة جديدة
        </Link>
      </div>

      {syndicates?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <Building2 className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد نقابات</p>
          <p className="text-sm">أنشئ أول نقابة سيادية</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {syndicates?.map((syndicate) => (
            <SyndicateCard
              key={syndicate.id}
              syndicate={syndicate}
              onJoin={() => handleJoin(syndicate.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}