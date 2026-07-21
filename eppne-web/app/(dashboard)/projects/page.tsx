// app/(dashboard)/projects/page.tsx
'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { ProjectsService, ProjectResponse } from '@/services/projects'; // ✅ استيراد الخدمة والنوع
import ProjectCard from '@/components/projects/ProjectCard';
import { Plus, Search, Filter, Loader2, Building2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ProjectType, ProjectStatus } from '@/types/projects';

const typeLabels: Record<ProjectType, string> = {
  INDUSTRIAL: 'صناعي',
  AGRICULTURAL: 'زراعي',
  REAL_ESTATE: 'عقاري',
  EDUCATIONAL: 'تعليمي',
  HEALTHCARE: 'صحي',
  ENERGY: 'طاقة',
  TECHNOLOGY: 'تقني',
  SOCIAL: 'اجتماعي',
  OTHER: 'أخرى',
};

const statusOptions: { value: ProjectStatus | ''; label: string }[] = [
  { value: '', label: 'كل الحالات' },
  { value: 'DRAFT', label: 'مسودة' },
  { value: 'FUNDRAISING', label: 'جمع تمويل' },
  { value: 'UNDER_CONSTRUCTION', label: 'قيد الإنشاء' },
  { value: 'OPERATIONAL', label: 'تشغيلي' },
  { value: 'COMPLETED', label: 'مكتمل' },
  { value: 'CANCELLED', label: 'ملغي' },
];

export default function ProjectsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<ProjectType | ''>('');
  const [filterStatus, setFilterStatus] = useState<ProjectStatus | ''>('');

  // ✅ استدعاء الخدمة مباشرة دون .then غير الصحيح
  const { data, isLoading } = useQuery({
    queryKey: ['projects', filterType, filterStatus],
    queryFn: () =>
      ProjectsService.listProjects({
        ...(filterType && { project_type: filterType }),
        ...(filterStatus && { status: filterStatus }),
        limit: 50,
      }),
    staleTime: 2 * 60 * 1000,
  });

  // ✅ التصفية باستخدام النوع ProjectResponse والحماية الاختيارية
  const filtered = data?.filter(
    (p: ProjectResponse) =>
      (p.title?.toLowerCase() || '').includes(searchTerm.toLowerCase()) ||
      (p.description?.toLowerCase() || '').includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 space-y-6">
      {/* الهيدر */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">🏗️ المشاريع السيادية</h1>
          <p className="text-sm text-muted-foreground/70">
            استكشف المشاريع الاستثمارية وساهم في تمويلها
          </p>
        </div>
        <Link
          href="/projects/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          مشروع جديد
        </Link>
      </div>

      {/* الفلاتر */}
      <div className="flex flex-wrap items-center gap-3 p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <div className="flex items-center gap-2 flex-1 min-w-[200px] bg-white/5 rounded-xl px-3 py-2 border border-white/5">
          <Search className="w-4 h-4 text-muted-foreground/50" />
          <input
            type="text"
            placeholder="ابحث عن مشروع..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent border-0 outline-none text-sm w-full text-foreground/80 placeholder:text-muted-foreground/40"
          />
        </div>

        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value as ProjectType | '')}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-foreground/80 outline-none focus:border-primary/30"
        >
          <option value="">كل الأنواع</option>
          {Object.entries(typeLabels).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>

        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value as ProjectStatus | '')}
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
          <Building2 className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد مشاريع</p>
          <p className="text-sm">كن أول من يطلق مشروعاً سيادياً على المنصة</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered?.map((project: ProjectResponse) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}
    </div>
  );
}