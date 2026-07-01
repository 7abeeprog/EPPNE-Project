// app/(dashboard)/academy/admin/tasks/page.tsx
"use client";

import { useState, useMemo, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

// ✅ استبدال الهوكات غير الموجودة بالهوكات الجديدة
import {
  useCourses,
  useCohorts,
  useTasks,
  useCreateTask,
} from "@/hooks/academy-queries";
import { Course, Cohort, AcademyTask } from "@/types/academy";
import { handleError } from "@/lib/error-handler";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Target,
  Plus,
  BookOpen,
  Clock,
  Loader2,
  Users,
  ShieldCheck,
  AlertCircle,
} from "lucide-react";
import { motion, Variants } from "framer-motion";

// ✅ تعريف الحركات باستخدام Variants
const cardVariants: Variants = {
  hidden: { opacity: 0, y: 30, scale: 0.95 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      type: "spring",
      stiffness: 300,
      damping: 24,
    },
  },
};

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

export default function TasksDashboard() {
  const queryClient = useQueryClient();
  const [selectedCourseId, setSelectedCourseId] = useState<number | "">("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [taskData, setTaskData] = useState({
    title: "",
    description: "",
    cohort_id: "",
    deadline: "",
    max_score: 100,
  });

  // ✅ 1. جلب الكورسات (مع Pagination)
  const {
    data: coursesData,
    isLoading: isCoursesLoading,
    error: coursesError,
  } = useCourses(0, 100);

  const courses = coursesData?.data || [];

  // ✅ 2. حساب الكورس المحدد والـ org_entity_id (useMemo)
  const selectedCourse = useMemo(
    () => courses.find((c: Course) => c.id === Number(selectedCourseId)),
    [courses, selectedCourseId]
  );
  const orgEntityId = selectedCourse?.org_entity_id;

  // ✅ 3. جلب الدفعات (مع Pagination)
  const {
    data: cohortsData,
    isLoading: isCohortsLoading,
    error: cohortsError,
  } = useCohorts(orgEntityId || 0, 0, 50, !!orgEntityId);

  const cohorts = cohortsData?.data || [];

  // ✅ 4. جلب التكليفات (مع Pagination)
  const {
    data: tasksData,
    isLoading: isTasksLoading,
    error: tasksError,
  } = useTasks(selectedCourseId as number, 0, 50, !!selectedCourseId);

  const tasks = tasksData?.data || [];

  // ✅ 5. محرك إنشاء التكليف (Mutation)
  const createTaskMutation = useCreateTask();

  // ✅ 6. معالجة الأخطاء
  if (coursesError) {
    const error = handleError(coursesError, "جلب الكورسات");
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
        <div className="p-6 bg-destructive/10 rounded-full mb-6 border border-destructive/20">
          <AlertCircle className="h-16 w-16 text-destructive" />
        </div>
        <h2 className="text-3xl font-bold mb-2">فشل في تحميل الكورسات</h2>
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

  // ✅ 7. دالة حفظ التكليف
  const handleSaveTask = useCallback(() => {
    if (!selectedCourseId || !taskData.title.trim() || !taskData.description.trim()) {
      toast.error("العنوان والوصف حقول سيادية إجبارية.");
      return;
    }

    createTaskMutation.mutate(
      {
        course_id: Number(selectedCourseId),
        cohort_id: taskData.cohort_id ? Number(taskData.cohort_id) : undefined,
        title: taskData.title.trim(),
        description: taskData.description.trim(),
        deadline: taskData.deadline ? new Date(taskData.deadline).toISOString() : undefined,
        max_score: Number(taskData.max_score) || 100,
      },
      {
        onSuccess: () => {
          toast.success("تم تشفير وإطلاق التكليف السيادي بنجاح! 🎯");
          queryClient.invalidateQueries({
            queryKey: ["academy", "tasks", selectedCourseId],
          });
          setIsModalOpen(false);
          setTaskData({
            title: "",
            description: "",
            cohort_id: "",
            deadline: "",
            max_score: 100,
          });
        },
        onError: (error) => {
          const err = handleError(error, "إنشاء التكليف");
          toast.error(err.message);
        },
      }
    );
  }, [selectedCourseId, taskData, createTaskMutation, queryClient]);

  return (
    <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative animate-in fade-in duration-700">
      {/* خلفية نيون زجاجية */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(var(--primary-rgb),0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* رأس الصفحة */}
      <div className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 w-full">
        <div className="absolute top-0 right-0 w-72 h-72 bg-primary/20 blur-[120px] rounded-full pointer-events-none -z-10" />
        <div className="flex-1">
          <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-primary flex items-center gap-4 drop-shadow-sm">
            <div className="p-3 bg-primary/10 rounded-2xl border border-primary/20 shadow-inner">
              <Target className="h-10 w-10 text-primary" />
            </div>
            هندسة التكليفات والمهام
          </h1>
          <p className="text-muted-foreground mt-4 text-lg md:text-xl font-medium max-w-2xl">
            أدر المهام الأكاديمية، اربطها بالكورسات السيادية، وقم بتقييدها بدفعات محددة بدقة عسكرية.
          </p>
        </div>
      </div>

      {/* فلتر الكورس */}
      <Card className="w-full border-primary/20 bg-card/60 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
        <CardContent className="p-8 flex flex-col md:flex-row items-end gap-6">
          <div className="flex-1 w-full">
            <Label className="text-xl font-bold flex items-center gap-2 mb-4 text-foreground">
              <BookOpen className="h-6 w-6 text-primary" />
              حدد الكورس المستهدف للعمليات:
            </Label>
            {isCoursesLoading ? (
              <Skeleton className="h-16 w-full rounded-2xl bg-background/50 border border-primary/10" />
            ) : (
              <select
                className="w-full h-16 px-5 text-xl font-bold bg-background/50 backdrop-blur-md border border-primary/20 rounded-2xl focus:border-primary focus:ring-1 focus:ring-primary/50 outline-none transition-all cursor-pointer shadow-inner"
                value={selectedCourseId}
                onChange={(e) => setSelectedCourseId(Number(e.target.value))}
              >
                <option value="" disabled>
                  -- اختر الكورس السيادي --
                </option>
                {courses.map((c: Course) => (
                  <option key={c.id} value={c.id}>
                    {c.title}
                  </option>
                ))}
              </select>
            )}
          </div>
          {selectedCourseId && (
            <Button
              onClick={() => setIsModalOpen(true)}
              size="lg"
              className="h-16 px-8 text-xl font-bold shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:scale-105 transition-transform rounded-2xl w-full md:w-auto"
            >
              <Plus className="ml-2 h-6 w-6" />
              إطلاق تكليف جديد
            </Button>
          )}
        </CardContent>
      </Card>

      {/* شبكة عرض التكليفات مع الحركة الفيزيائية */}
      {selectedCourseId && (
        <div className="w-full">
          {isTasksLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3].map((i) => (
                <Skeleton
                  key={i}
                  className="h-64 rounded-[2rem] bg-card/40 border border-white/5"
                />
              ))}
            </div>
          ) : tasksError ? (
            <div className="p-8 bg-destructive/10 rounded-[2rem] border border-destructive/20 text-center">
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
            <motion.div
              initial="hidden"
              animate="show"
              variants={cardVariants}
              className="text-center py-20 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-primary/30"
            >
              <Target className="mx-auto h-20 w-20 text-primary/20 mb-4 animate-pulse" />
              <h2 className="text-2xl font-bold text-foreground">خزانة المهام فارغة</h2>
              <p className="text-muted-foreground mt-2 text-lg">
                لم يتم إطلاق أي تكليفات لهذا الكورس حتى الآن.
              </p>
            </motion.div>
          ) : (
            <motion.div
              variants={containerVariants}
              initial="hidden"
              animate="show"
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
            >
              {tasks.map((task: AcademyTask) => (
                <motion.div key={task.id} variants={cardVariants}>
                  <Card className="h-full border-white/10 bg-card/40 backdrop-blur-md rounded-[2rem] hover:border-primary/50 hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] transition-all group overflow-hidden relative">
                    <div className="absolute top-0 right-0 w-2 h-full bg-primary/50 group-hover:bg-primary transition-colors" />
                    <CardContent className="p-8 flex flex-col h-full">
                      <h3 className="text-2xl font-black text-foreground group-hover:text-primary transition-colors pr-3 mb-3">
                        {task.title}
                      </h3>
                      <p className="text-muted-foreground line-clamp-3 mb-6 flex-grow font-medium">
                        {task.description}
                      </p>

                      <div className="space-y-3 mt-auto pt-4 border-t border-border/50">
                        {task.cohort_id ? (
                          <div className="flex items-center text-sm font-bold bg-primary/10 text-primary px-3 py-2 rounded-xl border border-primary/20 w-fit">
                            <Users className="h-4 w-4 ml-2" />
                            مقيد بدفعة #{task.cohort_id}
                          </div>
                        ) : (
                          <div className="flex items-center text-sm font-bold bg-emerald-500/10 text-emerald-500 px-3 py-2 rounded-xl border border-emerald-500/20 w-fit">
                            <ShieldCheck className="h-4 w-4 ml-2" />
                            عام لجميع الطلاب
                          </div>
                        )}

                        <div className="grid grid-cols-2 gap-3 mt-2">
                          <div className="bg-background/40 p-3 rounded-xl border border-white/5 shadow-sm">
                            <span className="text-xs font-bold text-muted-foreground block mb-1 flex items-center gap-1">
                              <Clock className="h-3 w-3 text-rose-500" />
                              التسليم
                            </span>
                            <span className="text-sm font-black">
                              {task.deadline
                                ? new Date(task.deadline).toLocaleDateString("ar-EG")
                                : "مفتوح"}
                            </span>
                          </div>
                          <div className="bg-background/40 p-3 rounded-xl border border-white/5 shadow-sm">
                            <span className="text-xs font-bold text-muted-foreground block mb-1 flex items-center gap-1">
                              <Target className="h-3 w-3 text-emerald-500" />
                              الدرجة
                            </span>
                            <span className="text-sm font-black text-emerald-500">
                              {task.max_score} نقطة
                            </span>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </motion.div>
          )}
        </div>
      )}

      {/* نافذة إطلاق التكليف (Modal) */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-md p-4 animate-in fade-in duration-300">
          <div className="bg-card/90 backdrop-blur-3xl border border-primary/20 shadow-[0_0_50px_-10px_rgba(var(--primary-rgb),0.3)] rounded-[2.5rem] p-8 md:p-10 max-w-lg w-full animate-in zoom-in-95 duration-300">
            <h2 className="text-3xl font-black mb-8 flex items-center gap-3 border-b border-border/50 pb-6 text-foreground">
              <div className="p-2 bg-primary/10 rounded-xl border border-primary/20">
                <Target className="h-8 w-8 text-primary" />
              </div>
              إطلاق تكليف سيادي
            </h2>
            <div className="space-y-5">
              <div>
                <Label className="font-bold text-lg">عنوان التكليف</Label>
                <Input
                  className="h-14 rounded-xl mt-2 bg-background/50 border-white/10 focus:border-primary shadow-inner text-lg"
                  placeholder="مثال: بناء عقد ذكي لامركزي"
                  value={taskData.title}
                  onChange={(e) =>
                    setTaskData({ ...taskData, title: e.target.value })
                  }
                />
              </div>
              <div>
                <Label className="font-bold text-lg">الوصف الفني للمهمة</Label>
                <textarea
                  className="w-full p-4 mt-2 bg-background/50 border border-white/10 rounded-xl outline-none focus:border-primary shadow-inner text-lg resize-none"
                  rows={4}
                  placeholder="اشرح المتطلبات بدقة..."
                  value={taskData.description}
                  onChange={(e) =>
                    setTaskData({ ...taskData, description: e.target.value })
                  }
                />
              </div>

              <div className="p-4 bg-primary/5 rounded-2xl border border-primary/10 space-y-4">
                <div>
                  <Label className="font-bold text-lg">
                    تقييد بدفعة معينة (اختياري)
                  </Label>
                  {isCohortsLoading ? (
                    <Skeleton className="h-14 w-full mt-2 rounded-xl" />
                  ) : cohortsError ? (
                    <p className="text-destructive text-sm mt-2">
                      {handleError(cohortsError, "جلب الدفعات").message}
                    </p>
                  ) : (
                    <select
                      className="w-full h-14 px-4 mt-2 bg-background/80 border border-white/10 rounded-xl outline-none focus:border-primary shadow-inner text-lg cursor-pointer"
                      value={taskData.cohort_id}
                      onChange={(e) =>
                        setTaskData({ ...taskData, cohort_id: e.target.value })
                      }
                    >
                      <option value="" className="font-bold text-emerald-500">
                        مفتوح لجميع الملتحقين بالكورس
                      </option>
                      {cohorts.map((c: Cohort) => (
                        <option key={c.id} value={c.id}>
                          دفعة: {c.name}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="font-bold text-lg">الدرجة القصوى</Label>
                    <Input
                      type="number"
                      className="h-14 rounded-xl mt-2 bg-background/80 border-white/10 focus:border-primary shadow-inner font-mono text-lg"
                      value={taskData.max_score}
                      onChange={(e) =>
                        setTaskData({
                          ...taskData,
                          max_score: Number(e.target.value),
                        })
                      }
                      min={1}
                      max={1000}
                    />
                  </div>
                  <div>
                    <Label className="font-bold text-lg">الموعد النهائي</Label>
                    <Input
                      type="date"
                      className="h-14 rounded-xl mt-2 bg-background/80 border-white/10 focus:border-primary shadow-inner text-lg"
                      value={taskData.deadline}
                      onChange={(e) =>
                        setTaskData({ ...taskData, deadline: e.target.value })
                      }
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-4 mt-8 pt-6 border-t border-border/50">
                <Button
                  variant="ghost"
                  onClick={() => setIsModalOpen(false)}
                  className="rounded-xl h-14 px-8 text-lg font-bold hover:bg-destructive/10 hover:text-destructive transition-colors"
                >
                  إلغاء الأمر
                </Button>
                <Button
                  onClick={handleSaveTask}
                  disabled={createTaskMutation.isPending}
                  className="rounded-xl h-14 px-10 text-lg font-bold shadow-[0_0_20px_rgba(var(--primary-rgb),0.4)] hover:scale-105 transition-transform"
                >
                  {createTaskMutation.isPending ? (
                    <Loader2 className="w-6 h-6 animate-spin mr-2" />
                  ) : null}
                  {createTaskMutation.isPending
                    ? "جاري التشفير..."
                    : "اعتماد وإطلاق"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}