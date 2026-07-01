// app/(dashboard)/academy/[id]/learn/page.tsx
"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState, useMemo, useCallback } from "react";
import Link from "next/link";
import { motion, AnimatePresence, Variants } from "framer-motion";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import {
  useCourse,
  useCurriculum,
  useMyEnrollments,
  useProgressMutation,
} from "@/hooks/academy-queries";
import { AcademyService } from "@/services/academy.service";
import { KnowledgeNode, Enrollment, Quiz, QuizQuestion } from "@/types/academy";
import { handleError } from "@/lib/error-handler";

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  Play,
  FileText,
  HelpCircle,
  CheckCircle,
  Video,
  Podcast,
  Loader2,
  Lock,
} from "lucide-react";

// ✅ تعريفات صارمة للأنواع المحلية لتجنب Implicit Any
interface CourseUnit {
  id: number;
  title: string;
}

interface PaginatedEnrollments {
  data: Enrollment[];
}

// ✅ تعريف صارم لحركات الواجهة
const contentVariants: Variants = {
  hidden: { opacity: 0, scale: 0.98, y: 15 },
  visible: { 
    opacity: 1, 
    scale: 1, 
    y: 0,
    transition: { type: "spring", stiffness: 300, damping: 25 }
  },
  exit: { opacity: 0, scale: 0.98, y: -15 },
};

// ==========================================
// 🟢 الصفحة الرئيسية (غرفة التعلم)
// ==========================================
export default function LearnPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const courseId = Number(params.id);

  // ✅ 1. جلب البيانات المعمارية
  const { data: course, isLoading: isCourseLoading, error: courseError } = useCourse(courseId);
  const { data: curriculum, isLoading: isCurriculumLoading, error: curriculumError } = useCurriculum(courseId);

  // ✅ 2. جلب الاشتراكات (بدون معاملات ليتوافق مع InfiniteQuery)
  const { data: enrollmentsData, isLoading: isEnrollmentsLoading } = useMyEnrollments();

  const [selectedNode, setSelectedNode] = useState<KnowledgeNode | null>(null);
  const [completedNodes, setCompletedNodes] = useState<number[]>([]);

  const isLoading = isCourseLoading || isCurriculumLoading || isEnrollmentsLoading;

  const units = useMemo(() => (curriculum?.units as CourseUnit[]) || [], [curriculum]);
  const nodes = useMemo(() => (curriculum?.nodes as KnowledgeNode[]) || [], [curriculum]);

  // ✅ 3. استخراج الاشتراكات بأنواع صارمة (Strict Types)
  const enrollments = useMemo(() => {
    if (!enrollmentsData) return [];
    if ('pages' in enrollmentsData) {
      return enrollmentsData.pages.flatMap((page: PaginatedEnrollments) => page.data || []);
    }
    return (enrollmentsData as any).data || [];
  }, [enrollmentsData]);

  const enrollment = useMemo(() => {
    return enrollments.find((e: Enrollment) => e.course_id === courseId) || null;
  }, [enrollments, courseId]);

  const currentProgress = enrollment?.progress_percentage || 0;

  // ✅ 4. معالجة الأخطاء
  if (courseError) {
    const error = handleError(courseError, "جلب تفاصيل الكورس");
    return (
      <div className="flex flex-col items-center justify-center min-h-screen p-6 text-center animate-in zoom-in-95 duration-500">
        <div className="p-6 bg-destructive/10 rounded-full mb-6 border border-destructive/20 shadow-[0_0_30px_rgba(var(--destructive-rgb),0.2)]">
          <FileText className="h-16 w-16 text-destructive animate-pulse" />
        </div>
        <h2 className="text-3xl font-black mb-2">فشل تقني سيادي</h2>
        <p className="text-muted-foreground text-lg mb-8 max-w-md">{error.message}</p>
        <Button onClick={() => router.push("/academy")} size="lg" className="rounded-xl h-14 px-8 font-bold">
          العودة إلى المعسكر الأكاديمي
        </Button>
      </div>
    );
  }

  // ✅ 5. التأكد من التسجيل وحماية المسار
  useEffect(() => {
    if (!isLoading && !enrollment) {
      toast.error("الوصول مقيد: أنت غير مدرج في السجل الخاص بهذا المسار.");
      router.push(`/academy/courses/${courseId}`);
    }
  }, [isLoading, enrollment, courseId, router]);

  // ✅ 6. تهيئة العرض الأولي
  useEffect(() => {
    if (!isLoading && nodes.length > 0 && !selectedNode) {
      setSelectedNode(nodes[0]);
    }
  }, [isLoading, nodes, selectedNode]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-screen w-full text-primary animate-in fade-in duration-500">
        <Loader2 className="w-16 h-16 animate-spin mb-4 drop-shadow-[0_0_15px_rgba(var(--primary-rgb),0.5)]" />
        <p className="text-xl font-bold tracking-widest">جاري تأمين الزمكان لغرفة التعلم...</p>
      </div>
    );
  }

  if (!enrollment) return null;

  return (
    <div className="h-[calc(100vh-64px)] flex flex-col bg-background relative overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(var(--primary-rgb),0.05),_transparent_80%)] pointer-events-none" />

      {/* الشريط العلوي */}
      <header className="h-16 border-b border-white/5 bg-card/40 backdrop-blur-xl px-6 flex items-center justify-between z-10 shadow-sm">
        <div className="flex items-center gap-4">
          <Link href={`/academy/courses/${courseId}`}>
            <Button variant="ghost" size="icon" className="hover:bg-primary/10 rounded-xl transition-all">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <h1 className="text-xl font-black text-foreground drop-shadow-sm line-clamp-1">
            {course?.title}
          </h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="w-32 md:w-48 bg-background/50 h-3 rounded-full overflow-hidden border border-white/10 shadow-inner hidden sm:block">
            <div
              className="bg-emerald-500 h-full transition-all duration-1000 shadow-[0_0_10px_rgba(16,185,129,0.5)] relative"
              style={{ width: `${Math.min(currentProgress, 100)}%` }}
            >
              <div className="absolute inset-0 bg-white/20 animate-[shimmer_2s_infinite]" />
            </div>
          </div>
          <span className="text-sm font-black text-emerald-500">{Math.round(currentProgress)}%</span>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden z-10">
        {/* الترسانة الجانبية (Curriculum Sidebar) */}
        <aside className="w-80 lg:w-96 border-l border-white/5 bg-card/20 backdrop-blur-3xl overflow-y-auto shadow-[10px_0_30px_rgba(0,0,0,0.2)]">
          <div className="p-4">
            <Accordion type="multiple" className="w-full space-y-3" defaultValue={units.map((u) => u.id.toString())}>
              {units.map((unit, uIdx) => (
                <AccordionItem
                  key={unit.id}
                  value={unit.id.toString()}
                  className="border border-white/5 bg-background/30 rounded-2xl px-3 overflow-hidden data-[state=open]:bg-background/50 transition-colors shadow-sm"
                >
                  <AccordionTrigger className="hover:no-underline font-black text-primary/90 text-sm py-4">
                    الوحدة {uIdx + 1}: {unit.title}
                  </AccordionTrigger>
                  <AccordionContent className="pb-4">
                    <div className="space-y-2 pr-3 border-r-2 border-primary/20">
                      {nodes.filter((n) => n.unit_id === unit.id).map((node) => {
                        const isCompleted = completedNodes.includes(node.id) || currentProgress === 100;
                        const isActive = selectedNode?.id === node.id;
                        return (
                          <button
                            key={node.id}
                            onClick={() => setSelectedNode(node)}
                            className={`w-full text-right p-3 rounded-xl flex items-center gap-3 transition-all duration-300 group
                              ${isActive 
                                ? "bg-primary/20 border border-primary/40 shadow-[0_0_15px_rgba(var(--primary-rgb),0.2)]" 
                                : "hover:bg-white/5 border border-transparent text-foreground/80"}
                              ${isCompleted && !isActive ? "opacity-60" : ""}
                            `}
                          >
                            <span className={isActive ? "text-primary" : "text-muted-foreground group-hover:text-primary/70"}>
                              {getNodeIcon(node.content_type, isCompleted)}
                            </span>
                            <span className={`flex-1 text-sm truncate ${isActive ? "font-black text-primary" : "font-semibold"}`}>
                              {node.title}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        </aside>

        {/* مساحة العرض المركزية */}
        <main className="flex-1 overflow-y-auto p-6 md:p-10 bg-black/10 relative">
          {selectedNode ? (
            <NodeContent
              key={selectedNode.id}
              node={selectedNode}
              courseId={courseId}
              enrollment={enrollment}
              onComplete={() => {
                const newCompleted = [...new Set([...completedNodes, selectedNode.id])];
                setCompletedNodes(newCompleted);
              }}
              isCompleted={completedNodes.includes(selectedNode.id) || currentProgress === 100}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground/50 animate-pulse">
              <Lock className="w-24 h-24 mb-6 opacity-20" />
              <p className="text-2xl font-bold tracking-wider">يرجى تحديد وحدة من الترسانة الجانبية للبدء</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

// ==========================================
// 🟢 وظائف الدعم
// ==========================================
function getNodeIcon(type: string, isCompleted: boolean) {
  if (isCompleted) return <CheckCircle className="h-5 w-5 text-emerald-500 shrink-0" />;
  switch (type) {
    case "VIDEO": return <Play className="h-5 w-5 shrink-0" />;
    case "ARTICLE": return <FileText className="h-5 w-5 shrink-0" />;
    case "QUIZ": return <HelpCircle className="h-5 w-5 shrink-0" />;
    case "LIVE": return <Podcast className="h-5 w-5 shrink-0" />;
    default: return <FileText className="h-5 w-5 shrink-0" />;
  }
}

// ==========================================
// 🟢 مكون عرض محتوى الدرس التفاعلي
// ==========================================
function NodeContent({
  node,
  courseId,
  enrollment,
  onComplete,
  isCompleted,
}: {
  node: KnowledgeNode;
  courseId: number;
  enrollment: Enrollment;
  onComplete: () => void;
  isCompleted: boolean;
}) {
  const [quizAnswers, setQuizAnswers] = useState<Record<number, string>>({});
  const progressMutation = useProgressMutation();

  const { data: quizData, isLoading: isQuizLoading, error: quizError } = useQuery({
    queryKey: ["academy", "quiz", node.id],
    queryFn: () => AcademyService.getQuizByNode(node.id),
    enabled: node.content_type === "QUIZ",
    staleTime: 5 * 60 * 1000,
  });

  const submitQuizMutation = useMutation({
    mutationFn: (answers: Record<number, string>) => AcademyService.submitQuiz(node.id, answers),
    onSuccess: (result) => {
      if (result.passed) {
        const newProgress = Math.min((enrollment.progress_percentage || 0) + 10, 100);
        progressMutation.mutate(
          { courseId, payload: { progress_percentage: newProgress } },
          {
            onSuccess: () => {
              toast.success("تم اعتماد اجتيازك للاختبار بنجاح! 🏆");
              onComplete();
            },
          }
        );
      } else {
        toast.info("لم تحقق نسبة النجاح المطلوبة. راجع المعلومات وحاول مجدداً.");
      }
    },
    onError: (error) => {
      toast.error(handleError(error, "عملية تقديم الاختبار").message);
    },
  });

  const joinLiveMutation = useMutation({
    mutationFn: () => AcademyService.joinLiveSession(node.id),
    onSuccess: () => {
      window.open(node.content_url || "#", "_blank");
      const newProgress = Math.min((enrollment.progress_percentage || 0) + 5, 100);
      progressMutation.mutate(
        { courseId, payload: { progress_percentage: newProgress } },
        {
          onSuccess: () => {
            toast.success("تم تسجيل بيانات حضورك بالشبكة المركزية!");
            onComplete();
          },
        }
      );
    },
    onError: (error) => {
      toast.error(handleError(error, "الانضمام للبث المباشر").message);
    },
  });

  const handleCompleteNode = useCallback(() => {
    if (isCompleted) return;
    const newProgress = Math.min((enrollment.progress_percentage || 0) + 10, 100);
    progressMutation.mutate(
      { courseId, payload: { progress_percentage: newProgress } },
      {
        onSuccess: () => {
          toast.success("تم تأكيد إنجاز الوحدة المعرفية.");
          onComplete();
        },
        onError: (error) => {
          toast.error(handleError(error, "تحديث التقدم").message);
        },
      }
    );
  }, [isCompleted, enrollment, courseId, progressMutation, onComplete]);

  const handleQuizSubmit = () => {
    if (Object.keys(quizAnswers).length === 0) {
      toast.warning("يجب تزويد النظام بكافة الإجابات المطلوبة.");
      return;
    }
    submitQuizMutation.mutate(quizAnswers);
  };

  if (quizError && node.content_type === "QUIZ") {
    return (
      <div className="p-8 bg-destructive/10 rounded-[2rem] border border-destructive/20 text-center shadow-lg">
        <p className="text-destructive font-black text-xl mb-2">فشل في استرداد بيانات الاختبار</p>
        <p className="text-muted-foreground">{handleError(quizError, "جلب الاختبار").message}</p>
        <Button variant="outline" className="mt-6 font-bold" onClick={() => window.location.reload()}>
          إعادة إنشاء الاتصال
        </Button>
      </div>
    );
  }

  return (
    <AnimatePresence mode="wait">
      <motion.div 
        key={node.id} 
        variants={contentVariants}
        initial="hidden"
        animate="visible"
        exit="exit"
        className="w-full max-w-5xl mx-auto space-y-8 pb-20"
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-card/40 backdrop-blur-2xl p-6 rounded-[2rem] border border-white/5 shadow-xl">
          <div>
            <h2 className="text-3xl font-black text-foreground drop-shadow-md">
              {node.title}
            </h2>
            <div className="flex gap-3 mt-3">
              <Badge variant="outline" className="bg-background/50 border-primary/30 text-primary font-bold px-3 py-1">
                {node.content_type === "VIDEO" ? "محتوى مرئي" : node.content_type === "LIVE" ? "بث متزامن" : node.content_type === "QUIZ" ? "اختبار سيادي" : "مادة تعليمية"}
              </Badge>
            </div>
          </div>

          {node.content_type !== "QUIZ" && (
            <Button
              onClick={handleCompleteNode}
              disabled={isCompleted || progressMutation.isPending}
              size="lg"
              className={`rounded-xl h-14 px-8 text-lg font-bold shadow-lg transition-all duration-300 shrink-0
                ${isCompleted ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/30" : "bg-primary text-primary-foreground hover:bg-primary/90"}
              `}
            >
              {progressMutation.isPending ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : <CheckCircle className="mr-2 h-5 w-5" />}
              {isCompleted ? "إنجاز معتمد" : "تأكيد إكمال الدرس"}
            </Button>
          )}
        </div>

        {node.content_type === "VIDEO" && (
          <div className="space-y-6">
            <div className="relative aspect-video rounded-[2.5rem] overflow-hidden bg-black shadow-[0_20px_50px_rgba(0,0,0,0.5)] border border-white/10 group">
              {node.content_url ? (
                <video controls className="w-full h-full object-contain" src={node.content_url} />
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-white/40 group-hover:text-white/60 transition-colors">
                  <Video className="h-20 w-20 mb-4 opacity-50" />
                  <p className="text-xl font-black tracking-widest">تشفير الفيديو قيد التقدم...</p>
                </div>
              )}
            </div>
            {node.description && (
              <div className="prose dark:prose-invert max-w-none bg-card/30 backdrop-blur-xl p-8 rounded-[2rem] border border-white/5 shadow-inner">
                <p className="text-lg leading-relaxed text-muted-foreground font-medium">{node.description}</p>
              </div>
            )}
          </div>
        )}

        {node.content_type === "LIVE" && (
          <div className="text-center py-16 px-6 bg-card/40 backdrop-blur-2xl rounded-[3rem] border border-blue-500/20 shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/10 blur-[100px] rounded-full pointer-events-none" />
            <div className="relative inline-flex mb-8">
              <span className="absolute flex h-6 w-6 -top-1 -right-1">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-6 w-6 bg-red-500" />
              </span>
              <div className="p-6 bg-blue-500/10 rounded-full border border-blue-500/30">
                <Podcast className="h-20 w-20 text-blue-500" />
              </div>
            </div>
            <h2 className="text-4xl font-black mb-4 relative z-10 text-foreground">{node.title}</h2>
            <p className="text-muted-foreground text-xl max-w-2xl mx-auto mb-10 relative z-10 font-medium">
              {node.description || "بوابة الزمكان سيتم فتحها قريباً لهذه الجلسة التفاعلية."}
            </p>
            <Button
              size="lg"
              onClick={() => joinLiveMutation.mutate()}
              disabled={joinLiveMutation.isPending || isCompleted}
              className="rounded-2xl h-16 px-10 text-xl font-bold bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_30px_rgba(37,99,235,0.4)] transition-all relative z-10"
            >
              {joinLiveMutation.isPending ? <Loader2 className="mr-2 h-6 w-6 animate-spin" /> : <Play className="mr-2 h-6 w-6" />}
              {joinLiveMutation.isPending ? "جاري التوثيق الأمني..." : isCompleted ? "تم الحضور" : "الانضمام للبث المباشر"}
            </Button>
          </div>
        )}

        {node.content_type === "QUIZ" && (
          <div className="space-y-8">
            {isQuizLoading ? (
              <div className="p-16 text-center animate-pulse bg-card/20 rounded-[3rem] border border-white/5">
                <Loader2 className="w-16 h-16 mx-auto animate-spin text-primary drop-shadow-[0_0_15px_rgba(var(--primary-rgb),0.5)]" />
              </div>
            ) : submitQuizMutation.isSuccess ? (
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className={`p-12 rounded-[3rem] text-center border shadow-2xl backdrop-blur-2xl relative overflow-hidden ${
                  submitQuizMutation.data.passed ? "bg-emerald-500/10 border-emerald-500/30" : "bg-destructive/10 border-destructive/30"
                }`}
              >
                <div className={`text-8xl font-black mb-6 drop-shadow-lg ${submitQuizMutation.data.passed ? "text-emerald-500" : "text-destructive"}`}>
                  {submitQuizMutation.data.score}%
                </div>
                <h3 className="text-3xl font-black mb-4 text-foreground">
                  {submitQuizMutation.data.passed ? "تم اعتماد النتيجة سيادياً! 🏆" : "لم يتم الاجتياز. النظام يتطلب إعادة المحاولة."}
                </h3>
              </motion.div>
            ) : (
              <div className="bg-card/40 backdrop-blur-2xl border border-white/5 rounded-[3rem] p-8 md:p-12 shadow-2xl">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 pb-6 border-b border-white/10">
                  <h2 className="text-3xl font-black text-foreground">{quizData?.title || "اختبار سيادي تفاعلي"}</h2>
                  <Badge variant="outline" className="px-4 py-2 text-lg border-primary/30 text-primary bg-primary/10 rounded-xl mt-4 md:mt-0 font-bold">
                    نسبة الاجتياز: {quizData?.passing_score}%
                  </Badge>
                </div>

                <div className="space-y-8">
                  {quizData?.questions?.map((q: QuizQuestion, idx: number) => (
                    <div key={q.id} className="p-8 bg-background/40 rounded-3xl border border-white/5 shadow-inner">
                      <p className="font-bold text-xl mb-6 text-foreground leading-relaxed">{idx + 1}. {q.text}</p>
                      {q.type === "MCQ" && q.options && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {q.options.map((opt: string, optIdx: number) => (
                            <label key={optIdx} className="flex items-center gap-4 cursor-pointer p-5 rounded-2xl border border-white/5 hover:bg-white/5 hover:border-primary/50 transition-all bg-card/30">
                              <input
                                type="radio"
                                className="w-5 h-5 text-primary bg-background border-primary/50 focus:ring-primary"
                                name={`q-${q.id}`}
                                value={opt}
                                onChange={(e) => setQuizAnswers({ ...quizAnswers, [q.id]: e.target.value })}
                              />
                              <span className="text-lg font-bold">{opt}</span>
                            </label>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                <div className="mt-12 pt-8 border-t border-white/10 flex justify-end">
                  <Button
                    size="lg"
                    onClick={handleQuizSubmit}
                    disabled={submitQuizMutation.isPending}
                    className="h-16 px-12 text-xl font-black rounded-2xl shadow-[0_0_25px_rgba(var(--primary-rgb),0.3)] transition-all"
                  >
                    {submitQuizMutation.isPending ? <Loader2 className="mr-3 h-6 w-6 animate-spin" /> : <HelpCircle className="mr-3 h-6 w-6" />}
                    {submitQuizMutation.isPending ? "جاري المعالجة الأمنية..." : "تسليم وتشفير الإجابات"}
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}