// app/(dashboard)/projects/[id]/page.tsx
'use client';

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { getProject, getProjectAnalytics } from '@/services/projects';
import { useProjectStore } from '@/store/projectStore';
import ProjectDetails from '@/components/projects/ProjectDetails';
import ProjectAnalytics from '@/components/projects/ProjectAnalytics';
import AdvancedMilestones from '@/components/projects/AdvancedMilestones';
import ProjectAnalysisDashboard from '@/components/projects/ProjectAnalysisDashboard';
import ContributionModal from '@/components/projects/ContributionModal';
import ProjectUpdates from '@/components/projects/ProjectUpdates';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Loader2, ArrowLeft } from 'lucide-react';

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = parseInt(params.id as string);
  const { setSelectedProject, selectedProject } = useProjectStore();

  // جلب بيانات المشروع
  const { data: project, isLoading: isLoadingProject } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => getProject(projectId).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  // جلب التحليلات
  const { data: analytics, isLoading: isLoadingAnalytics } = useQuery({
    queryKey: ['project-analytics', projectId],
    queryFn: () => getProjectAnalytics(projectId).then(res => res.data),
    refetchInterval: 30000, // تحديث كل 30 ثانية
    staleTime: 10000,
  });

  // تخزين المشروع في Zustand
  useEffect(() => {
    if (project) {
      setSelectedProject(project);
    }
    return () => {
      // تنظيف عند مغادرة الصفحة
      // useProjectStore.getState().clearSelectedProject();
    };
  }, [project, setSelectedProject]);

  if (isLoadingProject) {
    return (
      <div className="flex justify-center items-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center h-screen text-muted-foreground/60">
        <p className="text-lg">المشروع غير موجود</p>
        <button
          onClick={() => router.push('/projects')}
          className="mt-4 text-primary hover:underline flex items-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          العودة إلى المشاريع
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* زر العودة */}
      <button
        onClick={() => router.push('/projects')}
        className="flex items-center gap-2 text-sm text-muted-foreground/60 hover:text-foreground/80 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        العودة إلى المشاريع
      </button>

      {/* تفاصيل المشروع (الهيدر) */}
      <ProjectDetails project={project} analytics={analytics} />

      {/* التحليلات السريعة (3-4 بطاقات في صف) */}
      {analytics && <ProjectAnalytics analytics={analytics} />}

      {/* التبويبات */}
      <Tabs defaultValue="milestones" className="space-y-4">
        <TabsList className="bg-card/20 backdrop-blur-xl border border-white/10 p-1 rounded-2xl">
          <TabsTrigger
            value="milestones"
            className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary rounded-xl px-4 py-2 text-sm text-muted-foreground/70 transition-all"
          >
            🎯 المعالم
          </TabsTrigger>
          <TabsTrigger
            value="analysis"
            className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary rounded-xl px-4 py-2 text-sm text-muted-foreground/70 transition-all"
          >
            📊 التحليل
          </TabsTrigger>
          <TabsTrigger
            value="updates"
            className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary rounded-xl px-4 py-2 text-sm text-muted-foreground/70 transition-all"
          >
            📰 التحديثات
          </TabsTrigger>
          <TabsTrigger
            value="contributions"
            className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary rounded-xl px-4 py-2 text-sm text-muted-foreground/70 transition-all"
          >
            💰 المساهمات
          </TabsTrigger>
        </TabsList>

        <TabsContent value="milestones">
          <AdvancedMilestones projectId={projectId} />
        </TabsContent>

        <TabsContent value="analysis">
          <ProjectAnalysisDashboard projectId={projectId} />
        </TabsContent>

        <TabsContent value="updates">
          <ProjectUpdates projectId={projectId} />
        </TabsContent>

        <TabsContent value="contributions">
          <div className="p-6 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 text-center text-muted-foreground/60">
            <p className="text-sm">قائمة المساهمين ستظهر هنا</p>
            <p className="text-xs mt-1">(قيد التطوير)</p>
          </div>
        </TabsContent>
      </Tabs>

      {/* زر المساهمة (ثابت في الأسفل) */}
      <ContributionModal projectId={projectId} />
    </div>
  );
}