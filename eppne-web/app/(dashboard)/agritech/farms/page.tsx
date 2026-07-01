// app/(dashboard)/agritech/farms/page.tsx
'use client';

import { useState } from 'react';
import { useFarms, useDeleteFarm } from '@/hooks/agritech/useFarms';
import FarmCard from '@/components/agritech/FarmCard';
import { Loader2, Plus, Search, Filter } from 'lucide-react';
import Link from 'next/link';
import type { FarmType } from '@/types/agritech';

const farmTypeLabels: Record<FarmType, string> = {
  TRADITIONAL_SOIL: 'تربة تقليدية',
  HYDROPONICS: 'زراعة مائية',
  AEROPONICS: 'زراعة هوائية',
  VERTICAL_FARM: 'مزرعة عمودية',
  AQUAPONICS: 'أكوابونيك',
  LIVESTOCK_FARM: 'ثروة حيوانية',
  POULTRY_FARM: 'دواجن',
  FISH_FARM: 'استزراع سمكي',
  VERMICULTURE_FARM: 'ديدان عضوية',
  ALGAE_FARM: 'طحالب',
};

export default function FarmsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<FarmType | ''>('');

  const { data: farms, isLoading } = useFarms({ ...(filterType && { farm_type: filterType }) });
  const deleteFarm = useDeleteFarm();

  const filtered = farms?.filter((f) =>
    f.name.toLowerCase().includes(searchTerm.toLowerCase())
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
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">🌾 المزارع</h1>
          <p className="text-sm text-muted-foreground/70">إدارة المزارع الذكية</p>
        </div>
        <Link
          href="/agritech/farms/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          مزرعة جديدة
        </Link>
      </div>

      <div className="flex flex-wrap items-center gap-3 p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <div className="flex items-center gap-2 flex-1 min-w-[200px] bg-white/5 rounded-xl px-3 py-2 border border-white/5">
          <Search className="w-4 h-4 text-muted-foreground/50" />
          <input
            type="text"
            placeholder="ابحث عن مزرعة..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent border-0 outline-none text-sm w-full text-foreground/80 placeholder:text-muted-foreground/40"
          />
        </div>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value as FarmType | '')}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-foreground/80 outline-none focus:border-primary/30"
        >
          <option value="">كل الأنواع</option>
          {Object.entries(farmTypeLabels).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered?.map((farm) => (
          <FarmCard key={farm.id} farm={farm} />
        ))}
      </div>
    </div>
  );
}