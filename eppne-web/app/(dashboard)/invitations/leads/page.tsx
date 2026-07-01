// app/(dashboard)/invitations/leads/page.tsx
'use client';

import { useState } from 'react';
import { useLeads } from '@/hooks/invitations/useLeads';
import LeadCard from '@/components/invitations/LeadCard';
import LeadStatusBadge from '@/components/invitations/LeadStatusBadge';
import { Loader2, Users, Search, Filter, Plus } from 'lucide-react';
import Link from 'next/link';
import type { LeadStatus, LeadSource } from '@/types/invitations';

const statusOptions: { value: LeadStatus | ''; label: string }[] = [
  { value: '', label: 'كل الحالات' },
  { value: 'NEW', label: 'جديد' },
  { value: 'CONTACTED', label: 'تم التواصل' },
  { value: 'QUALIFIED', label: 'مؤهل' },
  { value: 'CONVERTED', label: 'محول' },
  { value: 'LOST', label: 'مفقود' },
];

export default function LeadsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<LeadStatus | ''>('');

  const { data: leads, isLoading } = useLeads({ ...(statusFilter && { status: statusFilter }) });

  const filtered = leads?.filter(l =>
    l.email?.includes(searchTerm) ||
    l.first_name?.includes(searchTerm) ||
    l.last_name?.includes(searchTerm) ||
    l.company?.includes(searchTerm)
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
        <h1 className="text-2xl font-bold text-foreground/90">👥 العملاء المحتملون</h1>
        <Link
          href="/invitations/leads/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          عميل جديد
        </Link>
      </div>

      <div className="flex flex-wrap items-center gap-3 p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <div className="flex items-center gap-2 flex-1 min-w-[200px] bg-white/5 rounded-xl px-3 py-2 border border-white/5">
          <Search className="w-4 h-4 text-muted-foreground/50" />
          <input
            type="text"
            placeholder="ابحث عن عميل..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent border-0 outline-none text-sm w-full text-foreground/80 placeholder:text-muted-foreground/40"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as LeadStatus | '')}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-foreground/80 outline-none focus:border-primary/30"
        >
          {statusOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {filtered?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <Users className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد عملاء محتملين</p>
          <p className="text-sm">أضف عميلاً جديداً أو استورد من منصات التواصل</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered?.map((lead) => (
            <LeadCard key={lead.id} lead={lead} onClick={() => window.location.href = `/invitations/leads/${lead.id}`} />
          ))}
        </div>
      )}
    </div>
  );
}