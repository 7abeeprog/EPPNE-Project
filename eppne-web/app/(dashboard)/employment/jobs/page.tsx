// app/(dashboard)/employment/jobs/page.tsx
'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getOpenJobs } from '@/services/employment';
import Link from 'next/link';
import { Search, MapPin, DollarSign, Users, Loader2, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';
import StatusBadge from '@/components/employment/StatusBadge';

export default function JobsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['open-jobs', filterType],
    queryFn: () => getOpenJobs({ 
      ...(filterType && { employment_type: filterType }),
      limit: 50 
    }).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  const filtered = data?.filter(job =>
    job.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    job.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">💼 الوظائف</h1>
          <p className="text-sm text-muted-foreground/70">استعرض وتقدم للوظائف المتاحة</p>
        </div>
        <Link
          href="/employment/jobs/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          نشر وظيفة
        </Link>
      </div>

      {/* الفلاتر */}
      <div className="flex flex-wrap items-center gap-3 p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <div className="flex items-center gap-2 flex-1 min-w-[200px] bg-white/5 rounded-xl px-3 py-2 border border-white/5">
          <Search className="w-4 h-4 text-muted-foreground/50" />
          <input
            type="text"
            placeholder="ابحث عن وظيفة..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent border-0 outline-none text-sm w-full text-foreground/80 placeholder:text-muted-foreground/40"
          />
        </div>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-foreground/80 outline-none focus:border-primary/30"
        >
          <option value="">كل الأنواع</option>
          <option value="FULL_TIME">دوام كامل</option>
          <option value="PART_TIME">دوام جزئي</option>
          <option value="CONTRACT">عقد</option>
        </select>
      </div>

      {/* القائمة */}
      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : filtered?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <div className="text-4xl mb-4">📭</div>
          <p className="text-lg">لا توجد وظائف متاحة حالياً</p>
          <p className="text-sm">كن أول من ينشر وظيفة</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered?.map((job) => (
            <Link
              key={job.id}
              href={`/employment/jobs/${job.id}`}
              className="p-5 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/30 hover:shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.2)] transition-all duration-300"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-foreground/90">{job.title}</h3>
                  <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground/50">
                    <span className="flex items-center gap-1">
                      <Users className="w-3 h-3" />
                      صاحب العمل #{job.employer_id}
                    </span>
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3 h-3" />
                      {job.location || 'عن بعد'}
                    </span>
                  </div>
                </div>
                {job.is_active ? (
                  <StatusBadge status="ACTIVE" className="text-xs" />
                ) : (
                  <StatusBadge status="SUSPENDED" className="text-xs" />
                )}
              </div>

              <div className="mt-3 flex items-center gap-4 text-sm">
                <span className="text-primary font-medium">
                  {job.salary_min && job.salary_max 
                    ? `${job.salary_min} - ${job.salary_max} ${job.currency}`
                    : 'غير محدد'}
                </span>
                <span className="text-muted-foreground/50">{job.employment_type.replace('_', ' ')}</span>
                {job.required_skills.length > 0 && (
                  <span className="text-xs text-muted-foreground/40">
                    🛠️ {job.required_skills.length} مهارة
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}