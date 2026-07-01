// app/(dashboard)/invitations/campaigns/page.tsx
'use client';

import { useState } from 'react';
import { useCampaigns } from '@/hooks/invitations/useCampaigns';
import CampaignCard from '@/components/invitations/CampaignCard';
import CampaignStatusBadge from '@/components/invitations/CampaignStatusBadge';
import { Loader2, Megaphone, Search, Filter, Plus } from 'lucide-react';
import Link from 'next/link';
import type { CampaignStatus, CampaignType } from '@/types/invitations';

const statusOptions: { value: CampaignStatus | ''; label: string }[] = [
  { value: '', label: 'كل الحالات' },
  { value: 'DRAFT', label: 'مسودة' },
  { value: 'ACTIVE', label: 'نشطة' },
  { value: 'PAUSED', label: 'موقفة' },
  { value: 'COMPLETED', label: 'مكتملة' },
  { value: 'CANCELLED', label: 'ملغية' },
];

export default function CampaignsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<CampaignStatus | ''>('');

  const { data: campaigns, isLoading } = useCampaigns({ ...(statusFilter && { status: statusFilter }) });

  const filtered = campaigns?.filter(c =>
    c.name.includes(searchTerm) || c.description?.includes(searchTerm)
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
        <h1 className="text-2xl font-bold text-foreground/90">📢 الحملات التسويقية</h1>
        <Link
          href="/invitations/campaigns/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          حملة جديدة
        </Link>
      </div>

      <div className="flex flex-wrap items-center gap-3 p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <div className="flex items-center gap-2 flex-1 min-w-[200px] bg-white/5 rounded-xl px-3 py-2 border border-white/5">
          <Search className="w-4 h-4 text-muted-foreground/50" />
          <input
            type="text"
            placeholder="ابحث عن حملة..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent border-0 outline-none text-sm w-full text-foreground/80 placeholder:text-muted-foreground/40"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as CampaignStatus | '')}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-foreground/80 outline-none focus:border-primary/30"
        >
          {statusOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {filtered?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <Megaphone className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد حملات تسويقية</p>
          <p className="text-sm">أنشئ حملتك الأولى للوصول إلى عملاء جدد</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered?.map((campaign) => (
            <CampaignCard key={campaign.id} campaign={campaign} />
          ))}
        </div>
      )}
    </div>
  );
}