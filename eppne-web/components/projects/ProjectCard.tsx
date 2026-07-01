// components/projects/ProjectCard.tsx
'use client';

import Link from 'next/link';
import Image from 'next/image';
import { cn } from '@/lib/utils';
import { Building2, MapPin, TrendingUp, Users } from 'lucide-react';
import type { Project } from '@/types/projects';

interface ProjectCardProps {
  project: Project;
  className?: string;
}

const statusColors: Record<string, string> = {
  DRAFT: 'border-gray-500/30 text-gray-400',
  FUNDRAISING: 'border-emerald-500/30 text-emerald-400',
  UNDER_CONSTRUCTION: 'border-blue-500/30 text-blue-400',
  OPERATIONAL: 'border-green-500/30 text-green-400',
  COMPLETED: 'border-purple-500/30 text-purple-400',
  CANCELLED: 'border-red-500/30 text-red-400',
};

const statusLabels: Record<string, string> = {
  DRAFT: 'مسودة',
  FUNDRAISING: 'جمع تمويل',
  UNDER_CONSTRUCTION: 'قيد الإنشاء',
  OPERATIONAL: 'تشغيلي',
  COMPLETED: 'مكتمل',
  CANCELLED: 'ملغي',
};

export default function ProjectCard({ project, className }: ProjectCardProps) {
  const fundingPercentage = project.funding_goal_mrusdt > 0
    ? (project.current_funding_mrusdt / project.funding_goal_mrusdt) * 100
    : 0;

  return (
    <Link
      href={`/projects/${project.id}`}
      className={cn(
        "group block p-5 rounded-2xl transition-all duration-300",
        "bg-card/30 backdrop-blur-xl border border-white/10",
        "hover:bg-card/50 hover:border-primary/30 hover:shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.2)]",
        className
      )}
    >
      {/* صورة الغلاف */}
      <div className="relative w-full h-40 rounded-xl overflow-hidden mb-4 bg-white/5">
        {project.cover_image_url ? (
          <Image
            src={project.cover_image_url}
            alt={project.title}
            fill
            className="object-cover group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl">
            <Building2 className="w-12 h-12 text-muted-foreground/20" />
          </div>
        )}
        {/* حالة المشروع */}
        <span className={cn(
          "absolute top-2 right-2 px-2.5 py-1 rounded-full text-xs font-medium border backdrop-blur-sm",
          statusColors[project.status] || 'border-white/10 text-muted-foreground'
        )}>
          {statusLabels[project.status] || project.status}
        </span>
      </div>

      {/* المحتوى */}
      <div className="space-y-2">
        <h3 className="font-semibold text-foreground/90 text-lg line-clamp-1 group-hover:text-primary transition-colors">
          {project.title}
        </h3>
        <p className="text-sm text-muted-foreground/60 line-clamp-2">
          {project.description}
        </p>

        {/* الموقع */}
        {project.country && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground/50">
            <MapPin className="w-3 h-3" />
            {project.country}
          </div>
        )}

        {/* شريط التمويل */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground/60">
              {project.current_funding_mrusdt.toFixed(2)} / {project.funding_goal_mrusdt.toFixed(2)} MR_USDT
            </span>
            <span className="text-primary font-medium">{fundingPercentage.toFixed(0)}%</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-primary to-secondary transition-all duration-1000"
              style={{ width: `${Math.min(fundingPercentage, 100)}%` }}
            />
          </div>
        </div>

        {/* مؤشرات سريعة */}
        <div className="flex items-center gap-4 pt-2 border-t border-white/5 text-xs text-muted-foreground/50">
          <span className="flex items-center gap-1">
            <Users className="w-3 h-3" />
            {project.current_funding_mrusdt > 0 ? 'ممول' : 'بدون تمويل'}
          </span>
          <span className="flex items-center gap-1">
            <TrendingUp className="w-3 h-3" />
            {project.project_type.replace(/_/g, ' ')}
          </span>
        </div>
      </div>
    </Link>
  );
}