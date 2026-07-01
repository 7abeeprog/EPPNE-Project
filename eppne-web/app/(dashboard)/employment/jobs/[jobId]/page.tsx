// app/(dashboard)/employment/jobs/[jobId]/page.tsx
'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getJob, applyToJob, getJobApplications, reviewApplication } from '@/services/employment';
import { useEmploymentStore } from '@/store/employmentStore';
import { ArrowLeft, Loader2, CheckCircle, XCircle, Clock, User, FileText, MapPin, DollarSign } from 'lucide-react';
import { cn } from '@/lib/utils';
import StatusBadge from '@/components/employment/StatusBadge';
import { useState } from 'react';

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const jobId = parseInt(params.jobId as string);
  const [showApplyForm, setShowApplyForm] = useState(false);
  const [coverLetter, setCoverLetter] = useState('');
  const [resumeUrl, setResumeUrl] = useState('');

  const { data: job, isLoading } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => getJob(jobId).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  const { data: applications, isLoading: appsLoading } = useQuery({
    queryKey: ['job-applications', jobId],
    queryFn: () => getJobApplications(jobId).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  const applyMutation = useMutation({
    mutationFn: () => applyToJob({ job_id: jobId, cover_letter: coverLetter, resume_url: resumeUrl }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job-applications', jobId] });
      setShowApplyForm(false);
    },
  });

  const reviewMutation = useMutation({
    mutationFn: ({ appId, approve }: { appId: number; approve: boolean }) =>
      reviewApplication(appId, approve),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job-applications', jobId] });
    },
  });

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!job) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted-foreground/60">
        <p className="text-lg">الوظيفة غير موجودة</p>
        <button onClick={() => router.back()} className="mt-4 text-primary hover:underline">
          العودة
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <button
        onClick={() => router.back()}
        className="flex items-center gap-2 text-sm text-muted-foreground/60 hover:text-foreground/80 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        العودة
      </button>

      {/* تفاصيل الوظيفة */}
      <div className="p-6 rounded-3xl bg-card/20 backdrop-blur-2xl border border-white/10">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground/90">{job.title}</h1>
            <div className="flex items-center gap-3 mt-2 text-sm text-muted-foreground/60">
              <span className="flex items-center gap-1">
                <User className="w-4 h-4" />
                صاحب العمل #{job.employer_id}
              </span>
              <span className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                {job.location || 'عن بعد'}
              </span>
              <span className="flex items-center gap-1">
                <DollarSign className="w-4 h-4" />
                {job.salary_min && job.salary_max 
                  ? `${job.salary_min} - ${job.salary_max} ${job.currency}`
                  : 'غير محدد'}
              </span>
            </div>
          </div>
          <StatusBadge status={job.is_active ? 'ACTIVE' : 'SUSPENDED'} />
        </div>

        <p className="mt-4 text-foreground/70 leading-relaxed whitespace-pre-wrap">
          {job.description || 'لا يوجد وصف'}
        </p>

        {job.required_skills.length > 0 && (
          <div className="mt-4">
            <p className="text-sm font-medium text-foreground/70">المهارات المطلوبة</p>
            <div className="flex flex-wrap gap-2 mt-1.5">
              {job.required_skills.map((skill) => (
                <span key={skill} className="px-3 py-1 rounded-full bg-primary/10 text-primary text-sm border border-primary/20">
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}

        <button
          onClick={() => setShowApplyForm(true)}
          className="mt-6 px-6 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          تقديم طلب
        </button>
      </div>

      {/* طلبات التوظيف (لصاحب العمل) */}
      {!appsLoading && applications && applications.length > 0 && (
        <div className="p-6 rounded-3xl bg-card/20 backdrop-blur-2xl border border-white/10">
          <h3 className="text-lg font-semibold text-foreground/90 mb-4">📋 طلبات التوظيف ({applications.length})</h3>
          <div className="space-y-3">
            {applications.map((app) => (
              <div key={app.id} className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/5">
                <div>
                  <p className="text-sm font-medium text-foreground/80">المتقدم #{app.applicant_id}</p>
                  <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground/50">
                    <StatusBadge status={app.status} />
                    {app.ai_match_score && (
                      <span>توافق AI: {app.ai_match_score}%</span>
                    )}
                  </div>
                </div>
                {app.status === 'PENDING' && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => reviewMutation.mutate({ appId: app.id, approve: true })}
                      className="p-2 rounded-lg bg-emerald-500/20 text-emerald-500 hover:bg-emerald-500/30 transition-colors"
                    >
                      <CheckCircle className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => reviewMutation.mutate({ appId: app.id, approve: false })}
                      className="p-2 rounded-lg bg-red-500/20 text-red-500 hover:bg-red-500/30 transition-colors"
                    >
                      <XCircle className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}