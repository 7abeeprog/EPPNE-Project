// app/(dashboard)/tenders-auctions/auctions/page.tsx
'use client';

import { useState } from 'react';
import { useAuctions } from '@/hooks/tenders-auctions/useAuctions';
import AuctionCard from '@/components/tenders-auctions/AuctionCard';
import { Loader2, Search, Filter } from 'lucide-react';
import Link from 'next/link';
import type { AuctionStatus } from '@/types/tenders-auctions';

const statusOptions: { value: AuctionStatus | ''; label: string }[] = [
  { value: '', label: 'كل الحالات' },
  { value: 'SCHEDULED', label: 'مجدول' },
  { value: 'LIVE', label: 'حي' },
  { value: 'CLOSED_WITH_WINNER', label: 'منتهي بفائز' },
  { value: 'CLOSED_NO_WINNER', label: 'منتهي بدون فائز' },
  { value: 'CANCELLED', label: 'ملغي' },
];

export default function AuctionsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<AuctionStatus | ''>('');

  const { data: auctions, isLoading } = useAuctions({ ...(statusFilter && { status: statusFilter }) });

  const filtered = auctions?.filter(a =>
    a.title.includes(searchTerm) || a.description?.includes(searchTerm)
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
        <h1 className="text-2xl font-bold text-foreground/90">🔨 المزادات</h1>
        <Link
          href="/tenders-auctions/auctions/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          مزاد جديد
        </Link>
      </div>

      <div className="flex flex-wrap items-center gap-3 p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <div className="flex items-center gap-2 flex-1 min-w-[200px] bg-white/5 rounded-xl px-3 py-2 border border-white/5">
          <Search className="w-4 h-4 text-muted-foreground/50" />
          <input
            type="text"
            placeholder="ابحث عن مزاد..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent border-0 outline-none text-sm w-full text-foreground/80 placeholder:text-muted-foreground/40"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as AuctionStatus | '')}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-foreground/80 outline-none focus:border-primary/30"
        >
          {statusOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filtered?.map((auction) => (
          <Link key={auction.id} href={`/tenders-auctions/auctions/${auction.id}`}>
            <AuctionCard auction={auction} />
          </Link>
        ))}
      </div>
    </div>
  );
}