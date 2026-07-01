// app/(dashboard)/employment/page.tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { getOpenJobs, getMyApplications, getMyContract, getMyPayrolls } from '@/services/employment';
import { Loader2, Briefcase, FileCheck, Users, DollarSign } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

export default function EmploymentDashboard() {
  const { data: jobs, isLoading: jobsLoading } = useQuery({
    queryKey: ['open-jobs'],
    queryFn: () => getOpenJobs({ limit: 10 }).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  const { data: applications } = useQuery({
    queryKey: ['my-applications'],
    queryFn: () => getMyApplications({ limit: 10 }).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  const { data: contract } = useQuery({
    queryKey: ['my-contract'],
    queryFn: () => getMyContract().then(res => res.data).catch(() => null),
    staleTime: 2 * 60 * 1000,
  });

  const { data: payrolls } = useQuery({
    queryKey: ['my-payrolls'],
    queryFn: () => getMyPayrolls({ limit: 6 }).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  if (jobsLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const stats = [
    { label: 'الوظائف النشطة', value: jobs?.length || 0, icon: Briefcase, color: 'text-blue-500' },
    { label: 'طلباتي', value: applications?.length || 0, icon: FileCheck, color: 'text-emerald-500' },
    { label: 'العقد النشط', value: contract ? 'نشط' : 'لا يوجد', icon: Users, color: contract ? 'text-primary' : 'text-muted-foreground' },
    { label: 'آخر راتب', value: payrolls?.[0]?.net_salary ? `${payrolls[0].net_salary} MR_USDT` : '—', icon: DollarSign, color: 'text-amber-500' },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">🧑‍💼 إدارة الموارد البشرية</h1>
          <p className="text-sm text-muted-foreground/70">إدارة الوظائف، الموظفين، والرواتب</p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/employment/jobs/create"
            className="px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
          >
            نشر وظيفة
          </Link>
          <Link
            href="/employment/attendance"
            className="px-4 py-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors"
          >
            تسجيل حضور
          </Link>
        </div>
      </div>

      {/* الإحصائيات */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map((stat, idx) => (
          <div key={idx} className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
            <div className="flex items-center gap-2">
              <stat.icon className={cn("w-4 h-4", stat.color)} />
              <span className="text-xs text-muted-foreground/50">{stat.label}</span>
            </div>
            <p className="mt-2 text-lg font-bold text-foreground/90">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* الوظائف النشطة */}
      <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <h3 className="text-sm font-medium text-foreground/70 mb-3">📋 أحدث الوظائف</h3>
        {jobs?.slice(0, 5).map((job) => (
          <Link
            key={job.id}
            href={`/employment/jobs/${job.id}`}
            className="flex items-center justify-between p-3 rounded-xl hover:bg-white/10 transition-colors border-b border-white/5 last:border-0"
          >
            <div>
              <p className="text-sm font-medium text-foreground/80">{job.title}</p>
              <p className="text-xs text-muted-foreground/50">{job.employment_type} • {job.location || 'عن بعد'}</p>
            </div>
            <span className="text-xs text-primary/80">
              {job.salary_min && job.salary_max ? `${job.salary_min} - ${job.salary_max} ${job.currency}` : 'غير محدد'}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}