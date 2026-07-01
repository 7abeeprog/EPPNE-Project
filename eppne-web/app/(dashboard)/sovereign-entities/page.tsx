// app/(dashboard)/sovereign-entities/page.tsx
'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Plus, Search, Filter } from 'lucide-react';
import Link from 'next/link';
import { getMyEntities } from '@/services/sovereign-entities';
import EntityCard from '@/components/sovereign-entities/EntityCard';
import { cn } from '@/lib/utils';
import type { SovereignEntityType, KYBStatus } from '@/types/sovereign-entities';

const entityTypeLabels: Record<SovereignEntityType, string> = {
  STATE_GOVERNMENT: 'دولة/حكومة',
  MINISTRY_AUTHORITY: 'وزارة/هيئة',
  INTERNATIONAL_ORGANIZATION: 'منظمة دولية',
  MULTINATIONAL_CORP: 'شركة متعددة الجنسيات',
  ENTERPRISE: 'شركة',
  NGO_CIVIL_SOCIETY: 'منظمة مجتمع مدني',
  ACADEMIC_INSTITUTION: 'مؤسسة أكاديمية',
  DIVISION: 'قطاع/إدارة',
  TEAM: 'فريق عمل',
};

export default function SovereignEntitiesPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<SovereignEntityType | ''>('');
  const [filterKYB, setFilterKYB] = useState<KYBStatus | ''>('');

  const { data, isLoading } = useQuery({
    queryKey: ['entities', 'me', filterType, filterKYB],
    queryFn: () => getMyEntities({ 
      ...(filterType && { entity_type: filterType }),
      ...(filterKYB && { kyb_status: filterKYB })
    }).then(res => res.data),
    staleTime: 5 * 60 * 1000,
  });

  const filtered = data?.filter(entity => 
    entity.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    entity.legal_name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 space-y-6">
      {/* الهيدر */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">🏛️ الكيانات السيادية</h1>
          <p className="text-sm text-muted-foreground/70">إدارة الكيانات التي تمثلها أو تديرها</p>
        </div>
        <Link
          href="/sovereign-entities/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          كيان جديد
        </Link>
      </div>

      {/* الفلاتر */}
      <div className="flex flex-wrap items-center gap-3 p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <div className="flex items-center gap-2 flex-1 min-w-[200px] bg-white/5 rounded-xl px-3 py-2 border border-white/5">
          <Search className="w-4 h-4 text-muted-foreground/50" />
          <input
            type="text"
            placeholder="ابحث باسم الكيان..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent border-0 outline-none text-sm w-full text-foreground/80 placeholder:text-muted-foreground/40"
          />
        </div>

        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value as SovereignEntityType | '')}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-foreground/80 outline-none focus:border-primary/30"
        >
          <option value="">كل الأنواع</option>
          {Object.entries(entityTypeLabels).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>

        <select
          value={filterKYB}
          onChange={(e) => setFilterKYB(e.target.value as KYBStatus | '')}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-foreground/80 outline-none focus:border-primary/30"
        >
          <option value="">كل حالات التحقق</option>
          <option value="PENDING">قيد الانتظار</option>
          <option value="UNDER_REVIEW">قيد المراجعة</option>
          <option value="VERIFIED">موثق</option>
          <option value="REJECTED">مرفوض</option>
          <option value="SUSPENDED">معلق</option>
        </select>
      </div>

      {/* القائمة */}
      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <div className="w-8 h-8 border-4 border-primary/30 border-t-primary rounded-full animate-spin" />
        </div>
      ) : filtered?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <Building2 className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد كيانات</p>
          <p className="text-sm">ابدأ بإنشاء كيانك السيادي الأول</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered?.map((entity) => (
            <EntityCard key={entity.id} entity={entity} />
          ))}
        </div>
      )}
    </div>
  );
}