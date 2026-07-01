// components/projects/AdvancedMilestones.tsx
'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getProject, completeMilestone, releaseMilestoneFunds } from '@/services/projects';
import { formatDistanceToNow } from 'date-fns/ar';
import { 
  CheckCircle, Circle, Calendar, Loader2, 
  DollarSign, ChevronDown, ChevronUp, 
  Check, X, Clock, FileCheck
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface AdvancedMilestonesProps {
  projectId: number;
}

export default function AdvancedMilestones({ projectId }: AdvancedMilestonesProps) {
  const queryClient = useQueryClient();
  const [expandedMilestone, setExpandedMilestone] = useState<number | null>(null);

  const { data: project, isLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => getProject(projectId).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  const completeMutation = useMutation({
    mutationFn: ({ milestoneId, data }: { milestoneId: number; data: { actual_date: string; completion_notes?: string } }) =>
      completeMilestone(milestoneId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project-analytics', projectId] });
    },
  });

  const releaseMutation = useMutation({
    mutationFn: (milestoneId: number) => releaseMilestoneFunds(milestoneId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
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
        <p className="text-xs mt-1">أضف معالم لتتبع تقدم المشروع وإطلاق الأموال</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {milestones.map((milestone) => {
        const isCompleted = milestone.is_completed;
        const isExpanded = expandedMilestone === milestone.id;
        const canComplete = !isCompleted && project?.status === 'FUNDRAISING';
        const canRelease = isCompleted && milestone.funds_to_release > 0;

        return (
          <div
            key={milestone.id}
            className={cn(
              "rounded-2xl border transition-all duration-300 bg-card/20 backdrop-blur-sm",
              isCompleted ? "border-emerald-500/30" : "border-white/10",
              isExpanded && "border-primary/30 shadow-[0_0_40px_-15px_rgba(var(--primary-rgb),0.15)]"
            )}
          >
            {/* رأس المعلم */}
            <div 
              className="flex items-center gap-4 p-4 cursor-pointer"
              onClick={() => setExpandedMilestone(isExpanded ? null : milestone.id)}
            >
              {/* أيقونة الحالة */}
              <div className={cn(
                "flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all",
                isCompleted 
                  ? "border-emerald-500 bg-emerald-500/20 text-emerald-500" 
                  : "border-white/20 bg-white/5 text-muted-foreground/50"
              )}>
                {isCompleted ? <CheckCircle className="w-5 h-5" /> : <Circle className="w-5 h-5" />}
              </div>

              {/* المحتوى */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3">
                  <h4 className="font-medium text-foreground/80 truncate">
                    {milestone.title}
                  </h4>
                  {isCompleted && (
                    <span className="text-xs text-emerald-500/70 flex items-center gap-1">
                      <Check className="w-3 h-3" />
                      مكتمل
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-4 mt-0.5 text-xs text-muted-foreground/50">
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {new Date(milestone.target_date).toLocaleDateString('ar-EG')}
                  </span>
                  {milestone.funds_to_release > 0 && (
                    <span className="flex items-center gap-1 text-primary/70">
                      <DollarSign className="w-3 h-3" />
                      {milestone.funds_to_release.toFixed(2)} MR_USDT
                    </span>
                  )}
                  {isCompleted && milestone.actual_date && (
                    <span className="flex items-center gap-1 text-emerald-500/50">
                      <Clock className="w-3 h-3" />
                      {formatDistanceToNow(new Date(milestone.actual_date), { addSuffix: true })}
                    </span>
                  )}
                </div>
              </div>

              {/* زر التوسيع */}
              <button className="p-1 rounded-lg hover:bg-white/10 transition-colors">
                {isExpanded ? <ChevronUp className="w-4 h-4 text-muted-foreground/50" /> : <ChevronDown className="w-4 h-4 text-muted-foreground/50" />}
              </button>
            </div>

            {/* المحتوى الموسع */}
            {isExpanded && (
              <div className="px-4 pb-4 pt-0 border-t border-white/5 space-y-3">
                {/* أزرار الإجراء */}
                <div className="flex flex-wrap gap-2 pt-3">
                  {canComplete && (
                    <button
                      onClick={() => {
                        const actualDate = new Date().toISOString();
                        completeMutation.mutate({
                          milestoneId: milestone.id,
                          data: { 
                            actual_date: actualDate,
                            completion_notes: 'تم إكمال المعلم بنجاح'
                          }
                        });
                      }}
                      disabled={completeMutation.isPending}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-500/20 text-emerald-500 border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors text-sm disabled:opacity-50"
                    >
                      {completeMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                      إكمال المعلم
                    </button>
                  )}
                  
                  {canRelease && (
                    <button
                      onClick={() => releaseMutation.mutate(milestone.id)}
                      disabled={releaseMutation.isPending}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors text-sm disabled:opacity-50"
                    >
                      {releaseMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <DollarSign className="w-4 h-4" />}
                      إطلاق الأموال ({milestone.funds_to_release.toFixed(2)} MR_USDT)
                    </button>
                  )}
                </div>

                {/* ملاحظات الإكمال */}
                {milestone.is_completed && milestone.completion_notes && (
                  <div className="p-3 rounded-xl bg-white/5 border border-white/5 text-sm text-muted-foreground/60">
                    📝 {milestone.completion_notes}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}