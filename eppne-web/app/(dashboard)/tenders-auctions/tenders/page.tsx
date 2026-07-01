// app/(dashboard)/tenders-auctions/tenders/page.tsx
'use client';

import { useState } from 'react';
import { useTenders } from '@/hooks/tenders-auctions/useTenders';
import TenderCard from '@/components/tenders-auctions/TenderCard';
import { Loader2, Search, Filter } from 'lucide-react';
import Link from 'next/link';
import type { TenderStatus } from '@/types/tenders-auctions';

const statusOptions: { value: TenderStatus | ''; label: string }[] = [
  { value: '', label: 'كل الحالات' },
  { value: 'DRAFT', label: 'مسودة' },
  { value: 'OPEN', label: 'مفتوحة' },
  { value: 'EVALUATING', label: 'قيد التقييم' },
  { value: 'AWARDED', label: 'تم الترسية' },
  { value: 'CANCELLED', label: 'ملغاة' },
];

export default function TendersPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<TenderStatus | ''>('');

  const { data: tenders, isLoading } = useTenders({ ...(statusFilter && { status: statusFilter }) });

  const filtered = tenders?.filter(t =>
    t.title.includes(searchTerm) || t.description.includes(searchTerm)
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
        <h1 className="text-2xl font-bold text-foreground/90">📋 المناقصات</h1>
        <Link
          href="/tenders-auctions/tenders/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          مناقصة جديدة
        </Link>
      </div>

      <div className="flex flex-wrap items-center gap-3 p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <div className="flex items-center gap-2 flex-1 min-w-[200px] bg-white/5 rounded-xl px-3 py-2 border border-white/5">
          <Search className="w-4 h-4 text-muted-foreground/50" />
          <input
            type="text"
            placeholder="ابحث عن مناقصة..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent border-0 outline-none text-sm w-full text-foreground/80 placeholder:text-muted-foreground/40"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as TenderStatus | '')}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-foreground/80 outline-none focus:border-primary/30"
        >
          {statusOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filtered?.map((tender) => (
          <Link key={tender.id} href={`/tenders-auctions/tenders/${tender.id}`}>
            <TenderCard tender={tender} />
          </Link>
        ))}
      </div>
    </div>
  );
}