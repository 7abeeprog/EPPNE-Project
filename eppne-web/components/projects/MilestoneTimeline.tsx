// components/projects/MilestoneTimeline.tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { getProject } from '@/services/projects';
import { CheckCircle, Circle, Calendar, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns/ar';

interface MilestoneTimelineProps {
  projectId: number;
}

export default function MilestoneTimeline({ projectId }: MilestoneTimelineProps) {
  const { data: project, isLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => getProject(projectId).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-32">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  const milestones = project?.milestones || [];

  if (milestones.length === 0) {
    return (
      <div className="p-8 text-center text-muted-foreground/60 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <Calendar className="w-8 h-8 mx-auto mb-2 opacity-30" />
        <p>لا توجد معالم محددة لهذا المشروع</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {milestones.map((milestone, index) => {
        const isCompleted = milestone.is_completed;
        const isLast = index === milestones.length - 1;

        return (
          <div key={milestone.id} className="relative flex gap-4">
            {/* الخط العمودي */}
            {!isLast && (
              <div className={cn(
                "absolute top-8 left-4 w-0.5 h-full -translate-x-1/2",
                isCompleted ? "bg-primary/50" : "bg-white/10"
              )} />
            )}

            {/* الدائرة */}
            <div className="relative z-10 flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-card/40 backdrop-blur-xl border border-white/10">
              {isCompleted ? (
                <CheckCircle className="w-5 h-5 text-emerald-500" />
              ) : (
                <Circle className="w-5 h-5 text-muted-foreground/30" />
              )}
            </div>

            {/* المحتوى */}
            <div className={cn(
              "flex-1 p-4 rounded-2xl bg-card/20 backdrop-blur-sm border transition-all duration-300",
              isCompleted
                ? "border-emerald-500/20 hover:border-emerald-500/40"
                : "border-white/5 hover:border-white/10"
            )}>
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="font-medium text-foreground/80">{milestone.title}</h4>
                  <p className="text-xs text-muted-foreground/50 flex items-center gap-1 mt-1">
                    <Calendar className="w-3 h-3" />
                    {new Date(milestone.target_date).toLocaleDateString('ar-EG')}
                  </p>
                </div>
                <div className="text-right">
                  {isCompleted && milestone.actual_date && (
                    <span className="text-xs text-emerald-500/70">
                      ✓ تم الإنجاز {formatDistanceToNow(new Date(milestone.actual_date), { addSuffix: true })}
                    </span>
                  )}
                  {milestone.funds_to_release > 0 && (
                    <p className="text-xs text-primary/70 mt-1">
                      💰 {milestone.funds_to_release.toFixed(2)} MR_USDT
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}