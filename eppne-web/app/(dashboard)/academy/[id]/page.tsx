// app/(dashboard)/academy/[id]/page.tsx
"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { motion, Variants } from "framer-motion";
import Image from "next/image";

// ✅ الهوكات والأنواع السيادية
import {
  useCourse,
  useMyEnrollments,
  useEnrollMutation,
} from "@/hooks/academy-queries";
import { Course, Enrollment } from "@/types/academy";
import { handleError } from "@/lib/error-handler";

// ✅ مكونات الواجهة (UI)
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CourseActionButton } from "@/components/academy/CourseActionButton";
import {
  BookOpen,
  Award,
  PlayCircle,
  Loader2,
  AlertCircle,
  Clock,
  Star,
  Shield,
  CheckCircle,
  Layers
} from "lucide-react";
import { toast } from "sonner";

// ✅ تعريف الحركات الصارمة (Strict Types) لمنع أخطاء الـ Index Signature
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

export default function CourseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const courseId = Number(params.id);

  // ✅ استخراج كود الإحالة من الرابط
  const affiliateCode = searchParams.get('ref') || searchParams.get('affiliate') || undefined;

  const [activeTab, setActiveTab] = useState("overview");

  // ✅ 1. جلب بيانات الكورس (مُخزنة مؤقتاً ومعزولة)
  const {
    data: course,
    isLoading: isCourseLoading,
    error: courseError,
  } = useCourse(courseId);

  // ✅ 2. جلب اشتراكات الطالب (مع ترقيم الصفحات)
  const {
    data: enrollmentsData,
    isLoading: isEnrollmentsLoading,
    error: enrollmentsError,
  } = useMyEnrollments(0, 100); // ✅ إضافة المعاملات لتقليل حجم البيانات

  // ✅ 3. استخراج البيانات بشكل آمن لمنع أخطاء InfiniteData و Implicit Any
  const enrollments = useMemo(() => {
    if (!enrollmentsData) return [];
    
    if ('pages' in enrollmentsData) {
      // تحديد النوع بشكل صريح كـ { data: Enrollment[] } لتجنب implicit any
      return enrollmentsData.pages.flatMap((page: { data: Enrollment[] }) => page.data || []);
    }
    
    return (enrollmentsData as any).data || [];
  }, [enrollmentsData]);

  // ✅ 4. التحقق من حالة الاشتراك
  const enrollment = useMemo(
    () => enrollments.find((e: Enrollment) => e.course_id === courseId),
    [enrollments, courseId]
  );
  
  const isEnrolled = !!enrollment;

  // ✅ 5. محرك التسجيل
  const enrollMutation = useEnrollMutation();

  const isLoading = isCourseLoading || isEnrollmentsLoading;

  // ✅ 6. معالجة الأخطاء المركزية
  if (courseError) {
    const error = handleError(courseError, "جلب تفاصيل المسار");
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center animate-in zoom-in-95 duration-500">
        <div className="p-6 bg-destructive/10 rounded-full mb-6 border border-destructive/20 shadow-[0_0_30px_rgba(var(--destructive-rgb),0.2)]">
          <AlertCircle className="h-16 w-16 text-destructive animate-pulse" />
        </div>
        <h2 className="text-3xl font-black mb-2 text-foreground">فشل أمني / تقني</h2>
        <p className="text-muted-foreground text-lg mb-8 max-w-md">{error.message}</p>
        <Button
          onClick={() => router.push("/academy")}
          size="lg"
          className="rounded-xl h-14 px-8 font-bold shadow-lg"
        >
          العودة إلى المعسكر الأكاديمي
        </Button>
      </div>
    );
  }

  // ✅ 7. حالة التحميل المهيكلة
  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto p-4 md:p-8 space-y-8 animate-in fade-in">
        <Skeleton className="h-[400px] w-full rounded-[2.5rem] bg-card/40 border border-white/5" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <Skeleton className="h-64 md:col-span-2 rounded-[2rem] bg-card/40 border border-white/5" />
          <Skeleton className="h-64 rounded-[2rem] bg-card/40 border border-white/5" />
        </div>
      </div>
    );
  }

  if (!course) return null;

  // ✅ 8. دالة التسجيل (مع تمرير كود الإحالة)
  const handleEnroll = () => {
    if (!course?.id) return;
    enrollMutation.mutate(
      {
        courseId: course.id,
        payload: {
          payment_method: course.is_free || course.price_mrusdt === 0 ? "FREE" : "WALLET",
          affiliate_code: affiliateCode, // ✅ تمرير كود الإحالة
        },
      },
      {
        onSuccess: () => {
          toast.success("تم إدراجك في السجل السيادي للمسار بنجاح! 🛡️");
          queryClient.invalidateQueries({ queryKey: ["academy", "my-enrollments"] });
          router.push(`/academy/classroom/${course.id}`);
        },
        onError: (error) => {
          const err = handleError(error, "عملية التسجيل");
          toast.error(err.message);
        },
      }
    );
  };

  const queryClient = useQueryClient();

  return (
    <motion.div 
      className="max-w-6xl mx-auto p-4 md:p-8 space-y-8 relative"
      variants={containerVariants}
      initial="hidden"
      animate="show"
    >
      {/* تأثيرات الإضاءة الخلفية */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-96 bg-primary/10 blur-[150px] rounded-full pointer-events-none -z-10" />

      {/* الهيدر البصري للمسار */}
      <motion.div variants={cardVariants}>
        <Card className="overflow-hidden border-white/10 bg-card/40 backdrop-blur-2xl shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] rounded-[2.5rem]">
          <div className="relative h-[350px] md:h-[450px] w-full bg-muted">
            {course.thumbnail_url ? (
              <Image
                src={course.thumbnail_url}
                alt={course.title}
                fill
                priority
                className="object-cover"
                sizes="(max-width: 1200px) 100vw, 1200px"
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-background to-primary/5">
                <Shield className="w-32 h-32 text-primary/20" />
              </div>
            )}
            
            <div className="absolute inset-0 bg-gradient-to-t from-background via-background/60 to-transparent" />
            
            <div className="absolute bottom-0 left-0 w-full p-8 md:p-12 z-10">
              <div className="flex flex-wrap items-center gap-3 mb-4">
                <span className="bg-primary/20 text-primary border border-primary/30 px-4 py-1.5 rounded-full text-sm font-black backdrop-blur-md shadow-inner">
                  {course.level === "BEGINNER" ? "مستوى تأسيسي" : course.level === "INTERMEDIATE" ? "مستوى تطبيقي" : "مستوى احترافي"}
                </span>
                {(course.is_free || course.price_mrusdt === 0) && (
                  <span className="bg-emerald-500/20 text-emerald-500 border border-emerald-500/30 px-4 py-1.5 rounded-full text-sm font-black backdrop-blur-md shadow-inner">
                    منحة سيادية (مجاني)
                  </span>
                )}
              </div>
              <h1 className="text-4xl md:text-6xl font-black text-foreground drop-shadow-lg tracking-tight mb-4">
                {course.title}
              </h1>
              {isEnrolled && (
                <div className="inline-flex items-center gap-2 bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 px-4 py-2 rounded-xl backdrop-blur-md font-bold">
                  <CheckCircle className="w-5 h-5" /> أنت ملتحق رسمياً بهذا المسار
                </div>
              )}
            </div>
          </div>

          <CardContent className="p-8 md:p-12 grid grid-cols-1 lg:grid-cols-3 gap-10">
            {/* المحتوى والتفاصيل */}
            <div className="lg:col-span-2 space-y-8">
              <Tabs defaultValue="overview" className="w-full" onValueChange={setActiveTab}>
                <TabsList className="bg-background/50 backdrop-blur-md p-1.5 rounded-2xl border border-white/10 shadow-inner w-full sm:w-fit mb-8">
                  <TabsTrigger value="overview" className="rounded-xl px-8 h-10 font-bold data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                    النشرة التعريفية
                  </TabsTrigger>
                  <TabsTrigger value="curriculum" className="rounded-xl px-8 h-10 font-bold data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                    الهيكل الأكاديمي
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="overview" className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-6">
                  <h2 className="text-2xl font-black text-foreground flex items-center gap-3">
                    <BookOpen className="h-7 w-7 text-primary" /> تفاصيل المسار
                  </h2>
                  <p className="text-muted-foreground leading-loose text-lg font-medium bg-background/30 p-6 rounded-2xl border border-white/5">
                    {course.description || "سيتم إدراج الوصف التفصيلي والأهداف المعرفية لهذا المسار قريباً."}
                  </p>
                </TabsContent>

                <TabsContent value="curriculum" className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-6">
                   <h2 className="text-2xl font-black text-foreground flex items-center gap-3">
                    <Layers className="h-7 w-7 text-primary" /> المنهج الدراسي
                  </h2>
                  <div className="bg-background/30 p-8 rounded-2xl border border-dashed border-white/10 text-center">
                    <Shield className="w-16 h-16 text-muted-foreground/30 mx-auto mb-4" />
                    <p className="text-muted-foreground font-bold text-lg">
                      تتطلب مراجعة الوحدات الدراسية المكتملة الدخول إلى غرفة التعلم الآمنة.
                    </p>
                  </div>
                </TabsContent>
              </Tabs>
            </div>
            
            {/* بطاقة الإجراءات والمواصفات (Sidebar) */}
            <div className="space-y-6">
              <div className="bg-card/40 backdrop-blur-xl p-8 rounded-[2rem] border border-white/10 shadow-lg sticky top-8">
                <div className="space-y-5 mb-8">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-primary/10 rounded-xl border border-primary/20"><Clock className="h-6 w-6 text-primary" /></div>
                    <div><p className="text-sm font-bold text-muted-foreground">المدة الزمنية</p><p className="font-black text-lg text-foreground">مرنة بالكامل</p></div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-amber-500/10 rounded-xl border border-amber-500/20"><Star className="h-6 w-6 text-amber-500" /></div>
                    <div><p className="text-sm font-bold text-muted-foreground">نقاط الخبرة (XP)</p><p className="font-black text-lg text-foreground">{course.reward_xp || 0} نقطة</p></div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-emerald-500/10 rounded-xl border border-emerald-500/20"><Award className="h-6 w-6 text-emerald-500" /></div>
                    <div><p className="text-sm font-bold text-muted-foreground">التوثيق</p><p className="font-black text-lg text-foreground">شهادة سيادية معتمدة</p></div>
                  </div>
                </div>

                <div className="pt-8 border-t border-border/50">
                  {isEnrolled ? (
                    <Button 
                      onClick={() => router.push(`/academy/classroom/${course.id}`)}
                      className="w-full h-16 text-lg font-black rounded-xl bg-primary hover:bg-primary/90 shadow-[0_0_25px_rgba(var(--primary-rgb),0.4)] hover:scale-105 transition-all"
                    >
                      <PlayCircle className="mr-2 h-7 w-7" /> دخول غرفة التعلم
                    </Button>
                  ) : (
                    <CourseActionButton course={course} />
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}