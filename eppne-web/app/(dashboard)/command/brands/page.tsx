// app/(dashboard)/command/brands/page.tsx
'use client';

import { useState } from 'react';
import { useBrands } from '@/hooks/command/useBrands';
import BrandCard from '@/components/command/BrandCard';
import { Loader2, Building2, Search, Filter, Plus } from 'lucide-react';
import Link from 'next/link';

export default function BrandsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [activeFilter, setActiveFilter] = useState<'all' | 'active' | 'inactive'>('all');

  const { data: brands, isLoading } = useBrands();

  const filtered = brands?.filter((b) => {
    const matchesSearch = b.name.includes(searchTerm);
    const matchesActive = activeFilter === 'all' ||
      (activeFilter === 'active' && b.is_active) ||
      (activeFilter === 'inactive' && !b.is_active);
    return matchesSearch && matchesActive;
  });

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
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">🏢 البراندات السيادية</h1>
          <p className="text-sm text-muted-foreground/70">إدارة جميع الكيانات السيادية على المنصة</p>
        </div>
        <Link
          href="/command/brands/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          براند جديد
        </Link>
      </div>

      <div className="flex flex-wrap items-center gap-3 p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <div className="flex items-center gap-2 flex-1 min-w-[200px] bg-white/5 rounded-xl px-3 py-2 border border-white/5">
          <Search className="w-4 h-4 text-muted-foreground/50" />
          <input
            type="text"
            placeholder="ابحث عن براند..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent border-0 outline-none text-sm w-full text-foreground/80 placeholder:text-muted-foreground/40"
          />
        </div>
        <div className="flex gap-1 bg-white/5 rounded-xl p-1">
          <button
            onClick={() => setActiveFilter('all')}
            className={cn(
              "px-3 py-1.5 rounded-lg text-xs transition-all",
              activeFilter === 'all' ? "bg-primary/20 text-primary" : "text-muted-foreground/50 hover:text-foreground/80"
            )}
          >
            الكل
          </button>
          <button
            onClick={() => setActiveFilter('active')}
            className={cn(
              "px-3 py-1.5 rounded-lg text-xs transition-all",
              activeFilter === 'active' ? "bg-emerald-500/20 text-emerald-500" : "text-muted-foreground/50 hover:text-foreground/80"
            )}
          >
            نشط
          </button>
          <button
            onClick={() => setActiveFilter('inactive')}
            className={cn(
              "px-3 py-1.5 rounded-lg text-xs transition-all",
              activeFilter === 'inactive' ? "bg-red-500/20 text-red-500" : "text-muted-foreground/50 hover:text-foreground/80"
            )}
          >
            غير نشط
          </button>
        </div>
      </div>

      {filtered?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <Building2 className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد براندات</p>
          <p className="text-sm">أنشئ برانداً سيادياً جديداً</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered?.map((brand) => (
            <BrandCard key={brand.id} brand={brand} />
          ))}
        </div>
      )}
    </div>
  );
}