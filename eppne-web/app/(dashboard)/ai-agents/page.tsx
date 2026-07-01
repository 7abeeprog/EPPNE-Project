// app/(dashboard)/ai-agents/page.tsx
'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { getAgents } from '@/services/ai-agents';
import AgentCard from '@/components/ai-agents/AgentCard';
import { Plus, Search, Loader2, Brain } from 'lucide-react';
import { cn } from '@/lib/utils';
import { AGENT_ROLE_LABELS, AGENT_STATUS_CONFIG, type AgentRole, type AgentStatus } from '@/types/ai-agents';

const statusOptions: { value: AgentStatus | ''; label: string }[] = [
  { value: '', label: 'كل الحالات' },
  { value: 'ACTIVE', label: 'نشط' },
  { value: 'IDLE', label: 'خامل' },
  { value: 'LEARNING', label: 'قيد التعلم' },
  { value: 'SUSPENDED', label: 'موقف' },
];

export default function AIAgentsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRole, setFilterRole] = useState<AgentRole | ''>('');
  const [filterStatus, setFilterStatus] = useState<AgentStatus | ''>('');

  const { data, isLoading } = useQuery({
    queryKey: ['agents', filterRole, filterStatus],
    queryFn: () =>
      getAgents({
        ...(filterRole && { role: filterRole }),
        ...(filterStatus && { status: filterStatus }),
        limit: 50,
      }).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });

  const filtered = data?.filter(
    (a) =>
      a.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.role.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 space-y-6">
      {/* الهيدر */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90 flex items-center gap-2">
            <Brain className="w-7 h-7 text-primary" />
            الوكلاء الرقميون
          </h1>
          <p className="text-sm text-muted-foreground/70">إدارة وكلاء الذكاء الاصطناعي السياديين</p>
        </div>
        <Link
          href="/ai-agents/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          وكيل جديد
        </Link>
      </div>

      {/* الفلاتر */}
      <div className="flex flex-wrap items-center gap-3 p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <div className="flex items-center gap-2 flex-1 min-w-[200px] bg-white/5 rounded-xl px-3 py-2 border border-white/5">
          <Search className="w-4 h-4 text-muted-foreground/50" />
          <input
            type="text"
            placeholder="ابحث عن وكيل..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent border-0 outline-none text-sm w-full text-foreground/80 placeholder:text-muted-foreground/40"
          />
        </div>

        <select
          value={filterRole}
          onChange={(e) => setFilterRole(e.target.value as AgentRole | '')}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-foreground/80 outline-none focus:border-primary/30"
        >
          <option value="">كل الأدوار</option>
          {Object.entries(AGENT_ROLE_LABELS).map(([key, value]) => (
            <option key={key} value={key}>
              {value.icon} {value.label}
            </option>
          ))}
        </select>

        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value as AgentStatus | '')}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-foreground/80 outline-none focus:border-primary/30"
        >
          {statusOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* القائمة */}
      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : filtered?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <Brain className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد وكلاء رقميون</p>
          <p className="text-sm">أنشئ وكيلك الذكي الأول لأتمتة المهام السيادية</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered?.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      )}
    </div>
  );
}