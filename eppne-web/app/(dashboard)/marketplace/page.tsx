// app/(dashboard)/marketplace/page.tsx
'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getServices } from '@/services/marketplace';
import ServiceCard from '@/components/marketplace/ServiceCard';
import { Search, Filter, Loader2, ShoppingBag } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ServiceType } from '@/types/marketplace';

const serviceTypeLabels: Record<ServiceType, string> = {
  RIDE_HAILING: '🚗 نقل ركاب',
  DELIVERY: '📦 توصيل',
  E_COMMERCE: '🛍️ تجارة إلكترونية',
  TOURISM_BOOKING: '✈️ سياحة',
  EDUCATION_PLATFORM: '📚 تعليم',
  JOB_MARKETPLACE: '💼 توظيف',
  SOCIAL_NETWORK: '🌐 تواصل اجتماعي',
  HEALTHCARE_PORTAL: '🏥 صحة',
  REAL_ESTATE: '🏠 عقارات',
  EVENT_MANAGEMENT: '🎪 فعاليات',
  CUSTOM: '⚙️ مخصص',
};

const typeOptions: { value: ServiceType | ''; label: string }[] = [
  { value: '', label: 'جميع الأنواع' },
  ...Object.entries(serviceTypeLabels).map(([key, label]) => ({
    value: key as ServiceType,
    label,
  })),
];

export default function MarketplacePage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<ServiceType | ''>('');
  const [filterFeatured, setFilterFeatured] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['marketplace-services', filterType, filterFeatured],
    queryFn: () =>
      getServices({
        ...(filterType && { service_type: filterType }),
        ...(filterFeatured && { featured: true }),
        limit: 50,
      }).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  const filtered = data?.filter(
    (s) =>
      s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 space-y-6">
      {/* الهيدر */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">🛒 متجر الخدمات</h1>
          <p className="text-sm text-muted-foreground/70">
            استكشف التطبيقات الجاهزة وانشرها بنقرة واحدة
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground/50">
          <ShoppingBag className="w-4 h-4" />
          <span>{data?.length || 0} خدمة متاحة</span>
        </div>
      </div>

      {/* الفلاتر */}
      <div className="flex flex-wrap items-center gap-3 p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <div className="flex items-center gap-2 flex-1 min-w-[200px] bg-white/5 rounded-xl px-3 py-2 border border-white/5">
          <Search className="w-4 h-4 text-muted-foreground/50" />
          <input
            type="text"
            placeholder="ابحث عن خدمة..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent border-0 outline-none text-sm w-full text-foreground/80 placeholder:text-muted-foreground/40"
          />
        </div>

        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value as ServiceType | '')}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-foreground/80 outline-none focus:border-primary/30"
        >
          {typeOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        <label className="flex items-center gap-2 text-sm text-muted-foreground/60 cursor-pointer">
          <input
            type="checkbox"
            checked={filterFeatured}
            onChange={(e) => setFilterFeatured(e.target.checked)}
            className="w-4 h-4 rounded border-white/20 bg-white/5"
          />
          ⭐ مميزة فقط
        </label>
      </div>

      {/* القائمة */}
      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : filtered?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <div className="text-4xl mb-4">📭</div>
          <p className="text-lg">لا توجد خدمات</p>
          <p className="text-sm">حاول تعديل الفلاتر أو البحث بكلمات مختلفة</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered?.map((service) => (
            <ServiceCard key={service.id} service={service} />
          ))}
        </div>
      )}
    </div>
  );
}