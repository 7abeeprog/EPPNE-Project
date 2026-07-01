// app/(dashboard)/logistics/warehouses/page.tsx
'use client';

import { useState } from 'react';
import { useWarehouses } from '@/hooks/logistics/useWarehouses';
import WarehouseCard from '@/components/logistics/WarehouseCard';
import { Loader2, Building2, Search, Filter, Plus } from 'lucide-react';
import Link from 'next/link';

export default function WarehousesPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const { data: warehouses, isLoading } = useWarehouses();

  const filtered = warehouses?.filter(w =>
    w.name.includes(searchTerm) || w.location.includes(searchTerm)
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
        <h1 className="text-2xl font-bold text-foreground/90">🏗️ المخازن</h1>
        <Link
          href="/logistics/warehouses/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          مخزن جديد
        </Link>
      </div>

      <div className="flex flex-wrap items-center gap-3 p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <div className="flex items-center gap-2 flex-1 min-w-[200px] bg-white/5 rounded-xl px-3 py-2 border border-white/5">
          <Search className="w-4 h-4 text-muted-foreground/50" />
          <input
            type="text"
            placeholder="ابحث عن مخزن..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent border-0 outline-none text-sm w-full text-foreground/80 placeholder:text-muted-foreground/40"
          />
        </div>
      </div>

      {filtered?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <Building2 className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد مخازن</p>
          <p className="text-sm">أنشئ مخزنك الأول</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered?.map((warehouse) => (
            <WarehouseCard key={warehouse.id} warehouse={warehouse} />
          ))}
        </div>
      )}
    </div>
  );
}