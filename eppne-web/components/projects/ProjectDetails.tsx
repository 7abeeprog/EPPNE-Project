// components/projects/ProjectDetails.tsx
'use client';

import Image from 'next/image';
import { MapPin, Calendar, Building2, Globe, Users, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Project, ProjectAnalytics } from '@/types/projects';

interface ProjectDetailsProps {
  project: Project;
  analytics?: ProjectAnalytics;
}

const statusColors: Record<string, string> = {
  DRAFT: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  FUNDRAISING: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  UNDER_CONSTRUCTION: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  OPERATIONAL: 'bg-green-500/20 text-green-400 border-green-500/30',
  COMPLETED: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  CANCELLED: 'bg-red-500/20 text-red-400 border-red-500/30',
};

const statusLabels: Record<string, string> = {
  DRAFT: 'مسودة',
  FUNDRAISING: 'جمع تمويل',
  UNDER_CONSTRUCTION: 'قيد الإنشاء',
  OPERATIONAL: 'تشغيلي',
  COMPLETED: 'مكتمل',
  CANCELLED: 'ملغي',
};

const typeLabels: Record<string, string> = {
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

export default function ProjectDetails({ project, analytics }: ProjectDetailsProps) {
  const fundingPercentage = project.funding_goal_mrusdt > 0
    ? (project.current_funding_mrusdt / project.funding_goal_mrusdt) * 100
    : 0;

  return (
    <div className="relative overflow-hidden rounded-3xl bg-card/20 backdrop-blur-2xl border border-white/10">
      {/* صورة الغلاف */}
      <div className="relative w-full h-64 md:h-80">
        {project.cover_image_url ? (
          <Image
            src={project.cover_image_url}
            alt={project.title}
            fill
            className="object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary/5 to-secondary/5">
            <Building2 className="w-20 h-20 text-muted-foreground/20" />
          </div>
        )}
        {/* تدرج شفاف فوق الصورة */}
        <div className="absolute inset-0 bg-gradient-to-t from-background via-background/20 to-transparent" />
      </div>

      {/* المحتوى فوق الصورة */}
      <div className="relative -mt-16 px-6 pb-6">
        <div className="flex flex-col md:flex-row items-start md:items-end gap-4">
          {/* الشعار/أيقونة */}
          <div className="w-20 h-20 rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10 flex items-center justify-center text-3xl shadow-lg">
            {project.cover_image_url ? (
              <Image
                src={project.cover_image_url}
                alt={project.title}
                width={80}
                height={80}
                className="rounded-2xl object-cover"
              />
            ) : (
              <Building2 className="w-10 h-10 text-primary/60" />
            )}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl md:text-3xl font-bold text-foreground/90 truncate">
                {project.title}
              </h1>
              <span className={cn(
                "text-xs px-3 py-1 rounded-full border font-medium",
                statusColors[project.status] || 'bg-white/5 text-muted-foreground border-white/10'
              )}>
                {statusLabels[project.status] || project.status}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-4 mt-1 text-sm text-muted-foreground/60">
              <span className="flex items-center gap-1">
                <Building2 className="w-4 h-4" />
                {typeLabels[project.project_type] || project.project_type}
              </span>
              {project.country && (
                <span className="flex items-center gap-1">
                  <MapPin className="w-4 h-4" />
                  {project.country}
                </span>
              )}
              <span className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                {new Date(project.created_at).toLocaleDateString('ar-EG')}
              </span>
            </div>
          </div>

          {/* أزرار الإجراء */}
          <div className="flex items-center gap-3 self-end">
            <button className="px-4 py-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors text-sm font-medium">
              متابعة
            </button>
            <button className="px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 text-sm">
              تبرع الآن
            </button>
          </div>
        </div>

        {/* وصف المشروع */}
        <p className="mt-4 text-foreground/70 leading-relaxed max-w-3xl">
          {project.description}
        </p>

        {/* شريط التمويل */}
        <div className="mt-4 space-y-1">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-4">
              <span className="text-foreground/80 font-medium">
                {project.current_funding_mrusdt.toFixed(2)} <span className="text-muted-foreground/50 text-xs">MR_USDT</span>
              </span>
              <span className="text-muted-foreground/50">من</span>
              <span className="text-foreground/80 font-medium">
                {project.funding_goal_mrusdt.toFixed(2)} <span className="text-muted-foreground/50 text-xs">MR_USDT</span>
              </span>
            </div>
            <span className="text-primary font-bold">{fundingPercentage.toFixed(0)}%</span>
          </div>
          <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-primary to-secondary transition-all duration-1000"
              style={{ width: `${Math.min(fundingPercentage, 100)}%` }}
            />
          </div>
        </div>

        {/* إحصائيات سريعة */}
        {analytics && (
          <div className="flex flex-wrap gap-6 mt-4 pt-4 border-t border-white/5 text-sm">
            <div className="flex items-center gap-2 text-muted-foreground/60">
              <Users className="w-4 h-4" />
              <span>{analytics.total_contributors} مساهم</span>
            </div>
            <div className="flex items-center gap-2 text-muted-foreground/60">
              <TrendingUp className="w-4 h-4" />
              <span>{analytics.milestones_completed}/{analytics.milestones_total} معالم</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}