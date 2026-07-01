// app/(dashboard)/social/pages/page.tsx
'use client';

import { useState } from 'react';
import { usePages } from '@/hooks/social/usePages';
import PageCard from '@/components/social/PageCard';
import CreatePageModal from '@/components/social/CreatePageModal';
import { Loader2, Plus } from 'lucide-react';

export default function PagesPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const { data: pages, isLoading } = usePages();

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
        <h1 className="text-2xl font-bold text-foreground/90">📄 الصفحات</h1>
        <button
          onClick={() => setCreateOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          صفحة جديدة
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {pages?.map((page) => (
          <PageCard key={page.id} page={page} />
        ))}
      </div>

      <CreatePageModal isOpen={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}