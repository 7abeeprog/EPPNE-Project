// app/(dashboard)/tourism-sports/programs/page.tsx
'use client';

import { usePrograms } from '@/hooks/tourism-sports/usePrograms';
import ProgramCard from '@/components/tourism-sports/ProgramCard';
import { Loader2, Plus } from 'lucide-react';
import Link from 'next/link';

export default function ProgramsPage() {
  const { data: programs, isLoading } = usePrograms();

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
        <h1 className="text-2xl font-bold text-foreground/90">📅 البرامج السياحية</h1>
        <Link
          href="/tourism-sports/programs/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          برنامج جديد
        </Link>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {programs?.map((prog) => (
          <ProgramCard key={prog.id} program={prog} />
        ))}
      </div>
    </div>
  );
}