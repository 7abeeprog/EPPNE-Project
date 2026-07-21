// app/(dashboard)/academy/instructor/grading/page.tsx
"use client";

import { useState, useCallback } from "react";
import { useQueryClient, useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { motion, Variants } from "framer-motion";

import { useTasks, useGradeSubmissionMutation } from "@/hooks/academy-queries";
import { AcademyService } from "@/services/academy.service";
import { AcademyTask, TaskSubmission } from "@/types/academy";
import { handleError } from "@/lib/error-handler";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  CheckCircle,
  FileText,
  UserCircle,
  Loader2,
  Award,
  GraduationCap,
  AlertCircle,
} from "lucide-react";
import { toast } from "sonner";

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const cardVariants: Variants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 300, damping: 24 },
  },
};

export default function InstructorGradingCenter() {
  const queryClient = useQueryClient();
  const params = useParams();
  const courseId = Number(params.courseId) || 1;

  const [selectedTaskId, setSelectedTaskId] = useState<number | "">("");
  const [gradingData, setGradingData] = useState<{
    [key: number]: { grade: string; feedback: string };
  }>({});

  const {
    data: tasks,
    isLoading: isTasksLoading,
    error: tasksError,
  } = useTasks(courseId, 0, 100);

  // ✅ الحل الجذري للخطأ
  const {
    data: submissions,
    isLoading: isSubmissionsLoading,
    error: submissionsError,
  } = useQuery<TaskSubmission[]>({
    queryKey: ["academy", "instructor", "submissions", selectedTaskId],
    queryFn: async () => {
      const result = await AcademyService.getTaskSubmissions(
        Number(selectedTaskId),
        0,
        50
      );
      // التعامل مع كلا الاحتمالين
      if (Array.isArray(result)) return result;
      if (result && typeof result === 'object' && 'data' in result) {
        return (result as any).data || [];
      }
      return [];
    },
    enabled: !!selectedTaskId,
    staleTime: 2 * 60 * 1000,
  });

  const gradeSubmissionMutation = useGradeSubmissionMutation();

  if (tasksError) {
    const error = handleError(tasksError, "جلب تكليفات المدرب");
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
        <div className="p-6 bg-destructive/10 rounded-full mb-6 border border-destructive/20">
          <AlertCircle className="h-16 w-16 text-destructive" />
        </div>
        <h2 className="text-3xl font-bold mb-2">فشل في تحميل التكليفات</h2>
        <p className="text-muted-foreground text-lg mb-8 max-w-md">{error.message}</p>
        <Button onClick={() => window.location.reload()} size="lg" className="rounded-xl h-14 px-8">
          إعادة المحاولة
        </Button>
      </div>
    );
  }

  const handleGradeSubmit = useCallback(
    (submissionId: number) => {
      const data = gradingData[submissionId];
      if (!data || !data.grade) {
        toast.error("يرجى إدخال الدرجة المستحقة للاعتماد.");
        return;
      }

      const selectedTask = tasks?.find((t: AcademyTask) => t.id === Number(selectedTaskId));
      const maxScore = selectedTask?.max_score || 100;
      const gradeNum = Number(data.grade);

      if (gradeNum < 0 || gradeNum > maxScore) {
        toast.error(`الدرجة يجب أن تكون بين 0 و ${maxScore}.`);
        return;
      }

      gradeSubmissionMutation.mutate(
        {
          submissionId,
          payload: {
            grade: gradeNum,
            instructor_feedback: data.feedback || "تم التقييم",
            status: "GRADED",
          },
        },
        {
          onSuccess: () => {
            toast.success("تم صك واعتماد الدرجة في السجل الأكاديمي للطلاب بنجاح! 🏅");
            queryClient.invalidateQueries({
              queryKey: ["academy", "instructor", "submissions", selectedTaskId],
            });
            setGradingData((prev) => {
              const newData = { ...prev };
              delete newData[submissionId];
              return newData;
            });
          },
          onError: (error) => {
            const err = handleError(error, "تقييم التسليم");
            toast.error(err.message);
          },
        }
      );
    },
    [gradingData, selectedTaskId, tasks, gradeSubmissionMutation, queryClient]
  );

  const updateGradingData = useCallback(
    (submissionId: number, field: "grade" | "feedback", value: string) => {
      setGradingData((prev) => ({
        ...prev,
        [submissionId]: {
          ...prev[submissionId],
          [field]: value,
        },
      }));
    },
    []
  );

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative"
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(var(--primary-rgb),0.04),_transparent_75%)] pointer-events-none -z-10" />

      <motion.div
        variants={cardVariants}
        className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-white/10 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 w-full"
      >
        <div className="absolute top-0 right-0 w-72 h-72 bg-primary/10 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse duration-1000" />
        <div className="flex-1">
          <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-primary flex items-center gap-4 drop-shadow-sm">
            <div className="p-3 bg-primary/10 rounded-2xl border border-primary/20 shadow-inner">
              <Award className="h-10 w-10 text-primary" />
            </div>
            غرفة التقييم والاعتماد السيادي
          </h1>
          <p className="text-muted-foreground mt-4 text-lg md:text-xl font-medium max-w-2xl">
            راجع ملفات الطلاب المرفوعة، صغ ملاحظاتك الفنية، واعتمد الدرجات النهائية على البلوكشين الداخلي.
          </p>
        </div>
      </motion.div>

      <motion.div variants={cardVariants}>
        <Card className="w-full border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
          <CardContent className="p-8">
            <Label className="text-xl font-bold flex items-center gap-2 mb-4 text-foreground">
              <GraduationCap className="h-6 w-6 text-primary" />
              اختر التكليف لاستعراض الحلول المعلقة:
            </Label>
            {isTasksLoading ? (
              <Skeleton className="h-16 w-full rounded-2xl bg-background/50 border border-white/5" />
            ) : (
              <select
                className="w-full h-16 px-5 text-xl bg-background/50 backdrop-blur-md border border-white/10 rounded-2xl focus:border-primary focus:ring-1 focus:ring-primary/50 outline-none transition-all cursor-pointer shadow-inner"
                value={selectedTaskId}
                onChange={(e) => setSelectedTaskId(Number(e.target.value))}
              >
                <option value="" disabled>-- قائمة التكليفات النشطة --</option>
                {tasks?.map((t: AcademyTask) => (
                  <option key={t.id} value={t.id}>
                    {t.title} (الدرجة القصوى: {t.max_score} نقطة)
                  </option>
                ))}
              </select>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {selectedTaskId && !isSubmissionsLoading && (!submissions || submissions.length === 0) && (
        <motion.div variants={cardVariants}>
          <div className="text-center py-24 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-primary/20">
            <CheckCircle className="mx-auto h-20 w-20 text-emerald-500/30 mb-4 animate-bounce" />
            <h2 className="text-3xl font-black text-foreground">لا توجد تسليمات معلقة!</h2>
            <p className="text-muted-foreground mt-2 text-lg">
              لقد قمت بتقييم وتطهير كافة ملفات الطلاب لهذا التكليف بنجاح.
            </p>
          </div>
        </motion.div>
      )}

      {submissionsError && selectedTaskId && (
        <motion.div variants={cardVariants}>
          <div className="p-6 bg-destructive/10 rounded-[2rem] border border-destructive/20 text-center">
            <p className="text-destructive font-bold">
              {handleError(submissionsError, "جلب تسليمات الطلاب").message}
            </p>
            <Button variant="outline" className="mt-4" onClick={() => window.location.reload()}>
              إعادة المحاولة
            </Button>
          </div>
        </motion.div>
      )}

      <motion.div variants={cardVariants} className="space-y-6">
        {isSubmissionsLoading ? (
          [1, 2].map((i) => (
            <Skeleton key={i} className="h-48 w-full rounded-[2rem] bg-card/30 border border-white/5" />
          ))
        ) : (
          submissions?.map((sub: TaskSubmission) => (
            <Card
              key={sub.id}
              className="border-white/10 bg-card/40 backdrop-blur-md rounded-[2rem] hover:border-primary/40 hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] transition-all overflow-hidden flex flex-col md:flex-row group"
            >
              <div className="p-8 md:w-1/3 bg-background/30 backdrop-blur-sm border-l border-white/5 flex flex-col justify-center relative">
                <div className="absolute top-0 right-0 w-1.5 h-full bg-primary/40 group-hover:bg-primary transition-colors" />
                <div className="flex items-center gap-4 mb-6">
                  <div className="p-2 bg-card/60 rounded-xl border border-white/10">
                    <UserCircle className="h-10 w-10 text-muted-foreground/80 group-hover:text-primary transition-colors" />
                  </div>
                  <div>
                    <h3 className="font-black text-lg text-foreground">
                      المجند / الطالب #{sub.user_id}
                    </h3>
                    <p className="text-xs font-bold text-muted-foreground mt-1">
                      {new Date(sub.submitted_at).toLocaleString("ar-EG")}
                    </p>
                  </div>
                </div>
                {sub.file_url && (
                  <Button
                    variant="outline"
                    size="lg"
                    className="w-full h-12 rounded-xl border-primary/20 hover:bg-primary/10 shadow-sm font-bold text-md"
                    onClick={() => window.open(sub.file_url, "_blank")}
                  >
                    <FileText className="ml-2 h-5 w-5 text-primary" />
                    عرض ملف الحل السيادي
                  </Button>
                )}
                {sub.student_notes && (
                  <div className="mt-4 p-4 bg-background/50 rounded-xl border border-white/5 text-sm font-medium shadow-inner">
                    <span className="font-bold text-primary block mb-1">ملاحظة الطالب المرفقة:</span>
                    {sub.student_notes}
                  </div>
                )}
              </div>

              <CardContent className="p-8 flex-1 flex flex-col md:flex-row gap-6 items-end relative z-10">
                <div className="flex-1 space-y-4 w-full">
                  <div className="flex flex-col gap-2">
                    <Label className="font-bold text-md text-muted-foreground">ملاحظات التقييم والتوجيه</Label>
                    <textarea
                      rows={3}
                      className="w-full p-4 bg-background/40 border border-white/10 rounded-xl outline-none focus:border-primary focus:ring-1 focus:ring-primary/50 text-md font-medium transition-colors shadow-inner resize-none"
                      placeholder="اكتب توجيهاتك المعرفية..."
                      value={gradingData[sub.id]?.feedback || ""}
                      onChange={(e) => updateGradingData(sub.id, "feedback", e.target.value)}
                    />
                  </div>
                </div>

                <div className="w-full md:w-56 space-y-4 shrink-0">
                  <div className="flex flex-col gap-2">
                    <Label className="font-bold text-md text-muted-foreground text-center md:text-right">
                      الدرجة المستحقة
                    </Label>
                    <Input
                      type="number"
                      className="h-14 text-center text-2xl font-black bg-background/40 border-white/10 rounded-xl focus:border-primary shadow-inner font-mono"
                      placeholder={`0 - ${tasks?.find((t: AcademyTask) => t.id === Number(selectedTaskId))?.max_score || 100}`}
                      value={gradingData[sub.id]?.grade || ""}
                      onChange={(e) => updateGradingData(sub.id, "grade", e.target.value)}
                      min={0}
                      max={tasks?.find((t: AcademyTask) => t.id === Number(selectedTaskId))?.max_score || 100}
                    />
                  </div>
                  <Button
                    onClick={() => handleGradeSubmit(sub.id)}
                    disabled={
                      gradeSubmissionMutation.isPending &&
                      gradeSubmissionMutation.variables?.submissionId === sub.id
                    }
                    className="w-full h-14 bg-emerald-600 hover:bg-emerald-500 font-black text-md shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:scale-105 transition-all rounded-xl"
                  >
                    {gradeSubmissionMutation.isPending &&
                      gradeSubmissionMutation.variables?.submissionId === sub.id ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <>اعتماد التقييم <CheckCircle className="mr-2 h-5 w-5" /></>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </motion.div>
    </motion.div>
  );
}