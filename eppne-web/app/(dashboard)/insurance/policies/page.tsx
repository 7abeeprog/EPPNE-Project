// app/(dashboard)/insurance/policies/page.tsx
'use client';

import { useState } from 'react';
import { usePolicies } from '@/hooks/insurance/usePolicies';
import PolicyCard from '@/components/insurance/PolicyCard';
import SubscribeModal from '@/components/insurance/SubscribeModal';
import { Loader2, Plus, Search } from 'lucide-react';
import Link from 'next/link';

export default function PoliciesPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [subscribePolicyId, setSubscribePolicyId] = useState<number | null>(null);
  const { data: policies, isLoading } = usePolicies({ is_active: true });

  const filtered = policies?.filter(p =>
    p.name.includes(searchTerm) || p.description?.includes(searchTerm)
  );

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
        <h1 className="text-2xl font-bold text-foreground/90">📋 بوالص التأمين</h1>
        <Link
          href="/insurance/policies/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          بوليصة جديدة
        </Link>
      </div>

      <div className="flex items-center gap-2 bg-white/5 rounded-xl px-3 py-2 border border-white/5">
        <Search className="w-4 h-4 text-muted-foreground/50" />
        <input
          type="text"
          placeholder="ابحث عن بوليصة..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="bg-transparent border-0 outline-none text-sm w-full text-foreground/80 placeholder:text-muted-foreground/40"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filtered?.map((policy) => (
          <PolicyCard
            key={policy.id}
            policy={policy}
            onSubscribe={() => setSubscribePolicyId(policy.id)}
          />
        ))}
      </div>

      {subscribePolicyId && (
        <SubscribeModal
          isOpen={!!subscribePolicyId}
          onClose={() => setSubscribePolicyId(null)}
          policyId={subscribePolicyId}
        />
      )}
    </div>
  );
}