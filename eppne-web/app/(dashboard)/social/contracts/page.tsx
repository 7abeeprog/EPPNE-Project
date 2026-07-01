// app/(dashboard)/social/contracts/page.tsx
'use client';

import { useState } from 'react';
import { useContracts } from '@/hooks/social/useContracts';
import ContractCard from '@/components/social/ContractCard';
import { Loader2, Plus, FileText } from 'lucide-react';
import Link from 'next/link';

export default function ContractsPage() {
  const { data: contracts, isLoading } = useContracts();

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
        <h1 className="text-2xl font-bold text-foreground/90">📄 العقود الاجتماعية الذكية</h1>
        <Link
          href="/social/contracts/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          عقد جديد
        </Link>
      </div>

      {contracts?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <FileText className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد عقود</p>
          <p className="text-sm">أنشئ عقداً جديداً للتوثيق الرقمي</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {contracts?.map((contract) => (
            <ContractCard key={contract.id} contract={contract} />
          ))}
        </div>
      )}
    </div>
  );
}