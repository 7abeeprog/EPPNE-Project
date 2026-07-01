// app/(dashboard)/zamakana/nodes/page.tsx
'use client';

import { useState } from 'react';
import { useNodes } from '@/hooks/zamakana/useNodes';
import NodeCard from '@/components/zamakana/NodeCard';
import { Loader2, Network, Search, Filter } from 'lucide-react';
import Link from 'next/link';
import type { ZamakanaNodeType } from '@/types/zamakana';

const typeOptions: { value: ZamakanaNodeType | ''; label: string }[] = [
  { value: '', label: 'كل الأنواع' },
  { value: 'ERA', label: 'حقبة' },
  { value: 'INNOVATION', label: 'ابتكار' },
  { value: 'PERSON', label: 'شخصية' },
  { value: 'EVENT', label: 'حدث' },
];

export default function NodesPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<ZamakanaNodeType | ''>('');

  const { data: nodes, isLoading } = useNodes({ ...(filterType && { node_type: filterType }) });

  const filtered = nodes?.filter(n =>
    n.title.includes(searchTerm) || n.description.includes(searchTerm)
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
        <h1 className="text-2xl font-bold text-foreground/90">📚 عقد المعرفة</h1>
        <Link
          href="/zamakana/nodes/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Network className="w-4 h-4" />
          عقدة جديدة
        </Link>
      </div>

      <div className="flex flex-wrap items-center gap-3 p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <div className="flex items-center gap-2 flex-1 min-w-[200px] bg-white/5 rounded-xl px-3 py-2 border border-white/5">
          <Search className="w-4 h-4 text-muted-foreground/50" />
          <input
            type="text"
            placeholder="ابحث عن عقدة..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent border-0 outline-none text-sm w-full text-foreground/80 placeholder:text-muted-foreground/40"
          />
        </div>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value as ZamakanaNodeType | '')}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-foreground/80 outline-none focus:border-primary/30"
        >
          {typeOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {filtered?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <Network className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد عقد معرفية</p>
          <p className="text-sm">ابدأ ببناء شبكة المعرفة السيادية</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered?.map((node) => (
            <NodeCard key={node.id} node={node} />
          ))}
        </div>
      )}
    </div>
  );
}