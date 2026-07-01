// app/(dashboard)/insurance/claims/page.tsx
'use client';

import { useState } from 'react';
import { useMyClaims } from '@/hooks/insurance/useClaims';
import ClaimCard from '@/components/insurance/ClaimCard';
import SubmitClaimModal from '@/components/insurance/SubmitClaimModal';
import { Loader2, Plus, AlertTriangle } from 'lucide-react';

export default function ClaimsPage() {
  const [submitModalOpen, setSubmitModalOpen] = useState(false);
  const { data: claims, isLoading } = useMyClaims();

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
        <h1 className="text-2xl font-bold text-foreground/90">📄 مطالباتي</h1>
        <button
          onClick={() => setSubmitModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          مطالبة جديدة
        </button>
      </div>

      {claims?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <AlertTriangle className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد مطالبات</p>
          <p className="text-sm">قدم مطالبة جديدة عند الحاجة</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {claims?.map((claim) => (
            <ClaimCard key={claim.id} claim={claim} />
          ))}
        </div>
      )}

      <SubmitClaimModal isOpen={submitModalOpen} onClose={() => setSubmitModalOpen(false)} />
    </div>
  );
}