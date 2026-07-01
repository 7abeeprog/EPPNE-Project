// app/(dashboard)/academy/my-learning/page.tsx
"use client";

import { useState, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";

// ✅ استبدال apiClient بالهوكات الجديدة
import {
  useMyEnrollments,
  useStudentTasks,
  useSubmitTaskMutation,
} from "@/hooks/academy-queries";
import { Enrollment, AcademyTask } from "@/types/academy";
import { handleError } from "@/lib/error-handler";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  UploadCloud,
  CheckCircle,
  Clock,
  ArrowLeft,
  BookOpen,
  Target,
  Loader2,
  Sparkles,
  AlertCircle,
} from "lucide-react";
import { toast } from "sonner";

export default function MyLearningDashboard() {
  const router = useRouter();
  const queryClient = useQueryClient();

  // ✅ حالة الواجهة
  const [activeTab, setActiveTab] = useState<"courses" | "tasks">("courses");
  const [selectedTask, setSelectedTask] = useState<AcademyTask | null>(null);
  const [submissionData, setSubmissionData] = useState({
    fileUrl: "",
    notes: "",
  });

  // ✅ 1. جلب اشتراكات الطالب (مع Infinite Query)
  const {
    data: enrollmentsData,
    isLoading: isEnrollmentsLoading,
    error: enrollmentsError,
  } = useMyEnrollments(0, 50);

  // ✅ التصحيح: استخراج البيانات من InfiniteData باستخدام pages.flatMap
  const enrollments = useMemo(
    () => enrollmentsData?.pages.flatMap((page) => page.data) || [],
    [enrollmentsData]
  );

  // ✅ 2. جلب تكليفات الطالب (مع Pagination عادية)
  const {
    data: tasksData,
    isLoading: isTasksLoading,
    error: tasksError,
  } = useStudentTasks(0, 50);

  // ✅ تصحيح: tasksData يعيد PaginatedResponse مباشرة
  const tasks = tasksData?.data || [];

  // ✅ 3. محرك رفع التكليف (Mutation)
  const submitTaskMutation = useSubmitTaskMutation();

  // ✅ 4. معالجة الأخطاء
  if (enrollmentsError) {
    const error = handleError(enrollmentsError, "جلب اشتراكاتك");
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
        <div className="p-6 bg-destructive/10 rounded-full mb-6 border border-destructive/20">
          <AlertCircle className="h-16 w-16 text-destructive" />
        </div>
        <h2 className="text-3xl font-bold mb-2">فشل في تحميل البيانات</h2>
        <p className="text-muted-foreground text-lg mb-8 max-w-md">{error.message}</p>
        <Button
          onClick={() => window.location.reload()}
          size="lg"
          className="rounded-xl h-14 px-8"
        >
          إعادة المحاولة
        </Button>
      </div>
    );
  }

  // ✅ 5. دالة رفع التكليف (useCallback)
  const handleSubmitTask = useCallback(() => {
    if (!selectedTask || !submissionData.fileUrl.trim()) {
      toast.error("يرجى إرفاق رابط ملف الحل السيادي.");
      return;
    }

    submitTaskMutation.mutate(
      {
        taskId: selectedTask.id,
        payload: {
          file_url: submissionData.fileUrl.trim(),
          student_notes: submissionData.notes.trim() || undefined,
        },
      },
      {
        onSuccess: () => {
          toast.success("تم تشفير وتسليم التكليف السيادي بنجاح! 🛡️");
          queryClient.invalidateQueries({
            queryKey: ["academy", "student", "tasks"],
          });
          setSelectedTask(null);
          setSubmissionData({ fileUrl: "", notes: "" });
        },
        onError: (error) => {
          const err = handleError(error, "رفع التكليف");
          toast.error(err.message);
        },
      }
    );
  }, [selectedTask, submissionData, submitTaskMutation, queryClient]);

  // ✅ 6. حساب حالة التحميل المشتركة
  const isLoading = isEnrollmentsLoading || isTasksLoading;

  return (
    <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* خلفية نيون زجاجية */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(var(--primary-rgb),0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* هيدر اللوحة */}
      <div className="relative overflow-hidden flex flex-col md:flex-row justify-between items-start md:items-end gap-6 bg-card/40 backdrop-blur-2xl border border-white/10 p-8 md:p-10 rounded-[2rem] shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)]">
        <div className="absolute top-0 right-0 w-72 h-72 bg-primary/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse duration-1000" />

        <div className="relative z-10 flex gap-5 items-center">
          <div className="p-4 bg-primary/10 rounded-2xl border border-primary/20 shadow-inner hidden sm:block">
            <BookOpen className="h-10 w-10 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl md:text-5xl font-black mb-2 bg-clip-text text-transparent bg-gradient-to-r from-foreground to-primary drop-shadow-sm">
              مقرراتي ومهامي
            </h1>
            <p className="text-muted-foreground text-lg md:text-xl font-medium">
              استكمل رحلتك الأكاديمية وارفع تكليفاتك للتقييم السيادي.
            </p>
          </div>
        </div>

        <div className="flex gap-2 bg-background/50 backdrop-blur-md p-1.5 rounded-2xl border border-white/10 shadow-inner w-full md:w-auto relative z-10">
          <Button
            variant={activeTab === "courses" ? "default" : "ghost"}
            onClick={() => setActiveTab("courses")}
            className={`rounded-xl flex-1 md:flex-none font-bold text-md h-12 px-6 transition-all ${
              activeTab === "courses"
                ? "shadow-[0_0_15px_rgba(var(--primary-rgb),0.4)]"
                : "hover:bg-primary/10 text-muted-foreground hover:text-foreground"
            }`}
          >
            <BookOpen className="mr-2 h-4 w-4" /> المقررات
          </Button>
          <Button
            variant={activeTab === "tasks" ? "default" : "ghost"}
            onClick={() => setActiveTab("tasks")}
            className={`rounded-xl flex-1 md:flex-none font-bold text-md h-12 px-6 transition-all ${
              activeTab === "tasks"
                ? "shadow-[0_0_15px_rgba(var(--primary-rgb),0.4)]"
                : "hover:bg-primary/10 text-muted-foreground hover:text-foreground"
            }`}
          >
            <Target className="mr-2 h-4 w-4" /> التكليفات
          </Button>
        </div>
      </div>

      {/* تبويب المقررات */}
      {activeTab === "courses" && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          {isEnrollmentsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3].map((i) => (
                <Skeleton
                  key={i}
                  className="h-64 rounded-[2rem] bg-card/40 border border-white/5"
                />
              ))}
            </div>
          ) : enrollments.length === 0 ? (
            <div className="text-center py-24 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-primary/20">
              <Sparkles className="mx-auto h-16 w-16 text-primary/30 mb-4 animate-pulse" />
              <h2 className="text-2xl font-black text-foreground">
                لم تلتحق بأي مقررات بعد
              </h2>
              <p className="text-muted-foreground mt-2 text-lg">
                اذهب إلى الكتالوج الأكاديمي لاكتشاف المسارات السيادية.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {enrollments.map((enrollment: Enrollment) => (
                <Card
                  key={enrollment.id}
                  className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] overflow-hidden hover:border-primary/50 hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] transition-all group relative"
                >
                  <div className="absolute top-0 right-0 w-full h-1 bg-gradient-to-r from-emerald-500 to-primary opacity-50 group-hover:opacity-100 transition-opacity" />
                  <CardContent className="p-8 flex flex-col h-full">
                    <div className="p-3 bg-primary/10 rounded-xl border border-primary/20 w-fit mb-4 group-hover:scale-110 transition-transform">
                      <BookOpen className="h-6 w-6 text-primary" />
                    </div>

                    <h3 className="text-2xl font-black mb-6 text-foreground group-hover:text-primary transition-colors">
                      {enrollment.course?.title ||
                        `مسار أكاديمي #${enrollment.course_id}`}
                    </h3>

                    {/* شريط التقدم الزجاجي */}
                    <div className="mt-auto mb-6 bg-background/50 p-4 rounded-2xl border border-white/5 shadow-inner">
                      <div className="flex justify-between text-sm mb-3 font-black">
                        <span className="text-muted-foreground">نسبة الإنجاز</span>
                        <span className="text-emerald-500 drop-shadow-sm">
                          {Math.round(enrollment.progress_percentage || 0)}%
                        </span>
                      </div>
                      <div className="w-full bg-card/80 rounded-full h-2.5 overflow-hidden shadow-inner border border-white/5">
                        <div
                          className="bg-gradient-to-r from-emerald-400 to-emerald-600 h-full rounded-full relative"
                          style={{
                            width: `${Math.min(
                              enrollment.progress_percentage || 0,
                              100
                            )}%`,
                          }}
                        >
                          <div className="absolute inset-0 bg-white/20 animate-[shimmer_2s_infinite]" />
                        </div>
                      </div>
                    </div>

                    <Button
                      onClick={() =>
                        router.push(`/academy/classroom/${enrollment.course_id}`)
                      }
                      className="w-full h-12 bg-primary font-black text-md rounded-xl shadow-[0_0_15px_rgba(var(--primary-rgb),0.3)] hover:scale-105 transition-transform"
                    >
                      {enrollment.is_completed || enrollment.progress_percentage === 100
                        ? "مراجعة المحتوى"
                        : "استكمال التعلم"}{" "}
                      <ArrowLeft className="ml-2 h-5 w-5" />
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* تبويب المهام والتكليفات */}
      {activeTab === "tasks" && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          {isTasksLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[1, 2].map((i) => (
                <Skeleton
                  key={i}
                  className="h-64 rounded-[2rem] bg-card/40 border border-white/5"
                />
              ))}
            </div>
          ) : tasksError ? (
            <div className="p-6 bg-destructive/10 rounded-[2rem] border border-destructive/20 text-center">
              <p className="text-destructive font-bold">
                {handleError(tasksError, "جلب التكليفات").message}
              </p>
              <Button
                variant="outline"
                className="mt-4"
                onClick={() => window.location.reload()}
              >
                إعادة المحاولة
              </Button>
            </div>
          ) : tasks.length === 0 ? (
            <div className="text-center py-24 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-emerald-500/20">
              <CheckCircle className="mx-auto h-16 w-16 text-emerald-500/30 mb-4 animate-bounce" />
              <h2 className="text-2xl font-black text-foreground">
                لا توجد تكليفات معلقة
              </h2>
              <p className="text-muted-foreground mt-2 text-lg">
                لقد أنجزت كافة المهام المطلوبة منك بنجاح.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {tasks.map((task: AcademyTask) => (
                <Card
                  key={task.id}
                  className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-primary/40 hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] transition-all flex flex-col group overflow-hidden"
                >
                  <CardContent className="p-8 flex flex-col h-full relative z-10">
                    <h3 className="text-2xl font-black mb-3 text-foreground group-hover:text-primary transition-colors">
                      {task.title}
                    </h3>
                    <p className="text-muted-foreground text-md font-medium mb-6 flex-1 bg-background/30 p-4 rounded-xl border border-white/5 shadow-inner">
                      {task.description}
                    </p>

                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-t border-border/50 pt-6 mt-auto gap-4">
                      <div className="flex flex-col">
                        <span className="text-xs font-bold text-muted-foreground mb-1">
                          الموعد النهائي
                        </span>
                        <span className="text-sm font-black flex items-center text-rose-500 bg-rose-500/10 px-3 py-1 rounded-lg border border-rose-500/20">
                          <Clock className="mr-1.5 h-4 w-4" />
                          {task.deadline
                            ? new Date(task.deadline).toLocaleDateString("ar-EG")
                            : "مفتوح"}
                        </span>
                      </div>
                      <Button
                        onClick={() => setSelectedTask(task)}
                        variant="outline"
                        className="rounded-xl border-primary/40 text-primary hover:bg-primary hover:text-white font-bold h-12 px-6 w-full sm:w-auto shadow-sm transition-all"
                      >
                        رفع الحل السيادي
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* نافذة رفع الحل الزجاجية */}
      {selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-md p-4 animate-in fade-in duration-300">
          <div className="bg-card/90 backdrop-blur-3xl border border-white/10 shadow-[0_0_50px_-10px_rgba(var(--primary-rgb),0.3)] rounded-[2.5rem] p-8 md:p-10 max-w-lg w-full animate-in zoom-in-95 duration-300">
            <div className="mb-8 border-b border-border/50 pb-6">
              <h2 className="text-3xl font-black flex items-center gap-3 text-foreground mb-2">
                <div className="p-2 bg-primary/10 rounded-xl border border-primary/20">
                  <UploadCloud className="h-8 w-8 text-primary" />
                </div>
                تسليم التكليف
              </h2>
              <p className="text-muted-foreground font-medium text-lg">
                {selectedTask.title}
              </p>
              <p className="text-sm text-muted-foreground/70 mt-1">
                الدرجة القصوى: {selectedTask.max_score} نقطة
              </p>
            </div>

            <div className="space-y-6">
              <div>
                <Label className="font-bold text-lg text-foreground">
                  رابط ملف الحل المرفوع (MinIO / Drive)
                </Label>
                <div className="flex items-center gap-3 mt-2">
                  <Input
                    placeholder="https://..."
                    value={submissionData.fileUrl}
                    onChange={(e) =>
                      setSubmissionData({
                        ...submissionData,
                        fileUrl: e.target.value,
                      })
                    }
                    className="bg-background/50 border-white/10 rounded-xl h-14 text-lg focus:border-primary shadow-inner"
                  />
                  <Button
                    size="icon"
                    variant="outline"
                    className="h-14 w-14 rounded-xl shrink-0 border-white/10 bg-background/50 hover:bg-primary/10 hover:border-primary/30 hover:text-primary transition-colors"
                    onClick={() => {
                      toast.info("سيتم إضافة رفع الملفات مباشرة في التحديث القادم");
                    }}
                  >
                    <UploadCloud className="h-6 w-6" />
                  </Button>
                </div>
              </div>
              <div>
                <Label className="font-bold text-lg text-foreground">
                  ملاحظات للمدرب (اختياري)
                </Label>
                <textarea
                  rows={4}
                  className="w-full p-4 mt-2 bg-background/50 border border-white/10 rounded-xl outline-none focus:border-primary focus:ring-1 focus:ring-primary/50 transition-all shadow-inner text-lg resize-none"
                  placeholder="أي تفاصيل تود إضافتها مع التسليم..."
                  value={submissionData.notes}
                  onChange={(e) =>
                    setSubmissionData({
                      ...submissionData,
                      notes: e.target.value,
                    })
                  }
                />
              </div>
              <div className="flex justify-end gap-4 mt-8 pt-6 border-t border-border/50">
                <Button
                  variant="ghost"
                  onClick={() => {
                    setSelectedTask(null);
                    setSubmissionData({ fileUrl: "", notes: "" });
                  }}
                  className="rounded-xl h-14 px-8 text-lg font-bold"
                >
                  إلغاء الأمر
                </Button>
                <Button
                  onClick={handleSubmitTask}
                  disabled={
                    submitTaskMutation.isPending || !submissionData.fileUrl.trim()
                  }
                  className="rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white h-14 px-8 text-lg font-bold shadow-[0_0_20px_rgba(16,185,129,0.4)] hover:scale-105 transition-transform"
                >
                  {submitTaskMutation.isPending ? (
                    <Loader2 className="mr-2 h-6 w-6 animate-spin" />
                  ) : (
                    <CheckCircle className="mr-2 h-6 w-6" />
                  )}
                  {submitTaskMutation.isPending
                    ? "جاري التشفير..."
                    : "اعتماد وتسليم"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}