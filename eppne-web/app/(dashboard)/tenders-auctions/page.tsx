// app/(dashboard)/tenders-auctions/page.tsx
'use client';

import { useTenders } from '@/hooks/tenders-auctions/useTenders';
import { useAuctions } from '@/hooks/tenders-auctions/useAuctions';
import { useMyBids } from '@/hooks/tenders-auctions/useBids';
import { Loader2, FileText, Gavel, DollarSign, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

export default function TendersAuctionsDashboard() {
  const { data: tenders, isLoading: tLoading } = useTenders({ status: 'OPEN' });
  const { data: auctions, isLoading: aLoading } = useAuctions({ status: 'LIVE' });
  const { data: myBids, isLoading: bLoading } = useMyBids();

  const isLoading = tLoading || aLoading || bLoading;

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const stats = [
    { label: 'مناقصات مفتوحة', value: tenders?.length || 0, icon: FileText, color: 'text-emerald-500' },
    { label: 'مزادات حية', value: auctions?.length || 0, icon: Gavel, color: 'text-amber-500' },
    { label: 'عطاءاتي', value: myBids?.length || 0, icon: DollarSign, color: 'text-blue-500' },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">📄 المناقصات والمزايدات</h1>
          <p className="text-sm text-muted-foreground/70">إدارة المناقصات والمزادات السيادية</p>
        </div>
        <Link
          href="/tenders-auctions/tenders/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <FileText className="w-4 h-4" />
          مناقصة جديدة
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {stats.map((stat, idx) => (
          <div key={idx} className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
            <div className="flex items-center gap-2">
              <stat.icon className={cn("w-4 h-4", stat.color)} />
              <span className="text-xs text-muted-foreground/50">{stat.label}</span>
            </div>
            <p className="mt-2 text-lg font-bold text-foreground/90">{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link
          href="/tenders-auctions/tenders"
          className="p-6 rounded-2xl bg-gradient-to-br from-emerald-500/10 to-teal-500/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <FileText className="w-8 h-8 mx-auto text-emerald-500" />
          <h3 className="mt-2 font-medium">استعراض المناقصات</h3>
          <p className="text-sm text-muted-foreground/50">تصفح وشارك في المناقصات المفتوحة</p>
        </Link>
        <Link
          href="/tenders-auctions/auctions"
          className="p-6 rounded-2xl bg-gradient-to-br from-amber-500/10 to-orange-500/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <Gavel className="w-8 h-8 mx-auto text-amber-500" />
          <h3 className="mt-2 font-medium">المزادات الحية</h3>
          <p className="text-sm text-muted-foreground/50">شارك في المزادات الفورية</p>
        </Link>
      </div>
    </div>
  );
}