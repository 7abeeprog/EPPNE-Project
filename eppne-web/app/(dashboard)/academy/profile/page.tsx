// app/(dashboard)/academy/profile/page.tsx
"use client";

import { useMemo } from "react";
import Link from "next/link";
import { motion, Variants } from "framer-motion";

// ✅ الهوكات الجديدة
import {
  useMyEnrollments,
  useMyCertificates,
  useDigitalTwin,
  useLeaderboard,
} from "@/hooks/academy-queries";
import { handleError } from "@/lib/error-handler";
import { Enrollment, Certificate } from "@/types/academy";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  User,
  Award,
  BookOpen,
  BrainCircuit,
  Trophy,
  ShieldCheck,
  CalendarDays,
  AlertCircle,
} from "lucide-react";

// ✅ تعريف الحركات باستخدام النوع الصحيح Variants
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

const statCardVariants: Variants = {
  hidden: { opacity: 0, scale: 0.9 },
  show: {
    opacity: 1,
    scale: 1,
    transition: { type: "spring", stiffness: 400, damping: 25 },
  },
};

export default function StudentProfilePage() {
  // ✅ 1. جلب اشتراكات الطالب (مع Infinite Query)
  const {
    data: enrollmentsData,
    isLoading: isEnrollmentsLoading,
    error: enrollmentsError,
  } = useMyEnrollments(0, 100);

  // ✅ التصحيح: استخراج البيانات من InfiniteData باستخدام pages.flatMap
  const enrollments = useMemo(
    () => enrollmentsData?.pages.flatMap((page) => page.data) || [],
    [enrollmentsData]
  );

  // ✅ 2. جلب شهادات الطالب (مع Pagination عادية)
  const {
    data: certificatesData,
    isLoading: isCertificatesLoading,
    error: certificatesError,
  } = useMyCertificates(0, 50);

  const certificates = certificatesData?.data || [];

  // ✅ 3. جلب التوأم الرقمي
  const {
    data: digitalTwin,
    isLoading: isTwinLoading,
    error: twinError,
  } = useDigitalTwin();

  // ✅ 4. جلب لوحة الشرف (لترتيب الطالب)
  const {
    data: leaderboardData,
    isLoading: isLeaderboardLoading,
  } = useLeaderboard(100);

  const leaderboard = leaderboardData?.data || [];

  // ✅ 5. معالجة الأخطاء
  if (enrollmentsError) {
    const error = handleError(enrollmentsError, "جلب اشتراكاتك");
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
        <div className="p-6 bg-destructive/10 rounded-full mb-6 border border-destructive/20">
          <AlertCircle className="h-16 w-16 text-destructive" />
        </div>
        <h2 className="text-3xl font-bold mb-2">فشل في تحميل الملف الشخصي</h2>
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

  const isLoading =
    isEnrollmentsLoading ||
    isCertificatesLoading ||
    isTwinLoading ||
    isLeaderboardLoading;

  // ✅ 6. حساب الإحصائيات
  const stats = useMemo(() => {
    const completedCourses = enrollments.filter(
      (e: Enrollment) => e.is_completed || e.progress_percentage === 100
    );
    const totalXp = certificates.reduce((acc: number, c: Certificate) => acc + (c.grade || 0), 0);
    const avgGrade =
      certificates.length > 0
        ? Math.round(
            certificates.reduce((acc: number, c: Certificate) => acc + (c.grade || 0), 0) /
              certificates.length
          )
        : 0;

    // البحث عن ترتيب الطالب في لوحة الشرف
    const firstEnrollment = enrollments[0];
    const studentRank =
      firstEnrollment && leaderboard.length > 0
        ? leaderboard.findIndex(
            (entry) => entry.user_id === firstEnrollment.user_id
          ) + 1
        : 0;

    return {
      totalCourses: enrollments.length,
      completedCourses: completedCourses.length,
      totalCertificates: certificates.length,
      totalXp,
      avgGrade,
      studentRank: studentRank > 0 ? studentRank : null,
    };
  }, [enrollments, certificates, leaderboard]);

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative"
    >
      {/* خلفية نيون زجاجية */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(139,92,246,0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* رأس الصفحة */}
      <motion.div
        variants={cardVariants}
        className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10"
      >
        <div className="absolute top-0 right-0 w-72 h-72 bg-purple-500/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse" />
        <div className="flex items-center gap-6">
          <div className="p-4 bg-purple-500/10 rounded-2xl border border-purple-500/20 shadow-inner">
            <User className="h-12 w-12 text-purple-500" />
          </div>
          <div>
            <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-purple-500 drop-shadow-sm">
              ملفي الأكاديمي
            </h1>
            <p className="text-muted-foreground mt-2 text-lg md:text-xl font-medium">
              مساري التعليمي، إنجازاتي، والشهادات السيادية.
            </p>
          </div>
        </div>
      </motion.div>

      {/* بطاقات الإحصائيات */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
        {isLoading ? (
          [1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-28 rounded-[2rem] bg-card/40 border border-white/5" />
          ))
        ) : (
          <>
            <motion.div variants={statCardVariants}>
              <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-purple-500/30 transition-all group">
                <CardContent className="p-4 md:p-6 text-center">
                  <p className="text-3xl md:text-4xl font-black text-purple-500">
                    {stats.totalCourses}
                  </p>
                  <p className="text-xs text-muted-foreground font-bold mt-1">
                    المقررات
                  </p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div variants={statCardVariants}>
              <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-emerald-500/30 transition-all group">
                <CardContent className="p-4 md:p-6 text-center">
                  <p className="text-3xl md:text-4xl font-black text-emerald-500">
                    {stats.completedCourses}
                  </p>
                  <p className="text-xs text-muted-foreground font-bold mt-1">
                    مكتملة
                  </p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div variants={statCardVariants}>
              <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-amber-500/30 transition-all group">
                <CardContent className="p-4 md:p-6 text-center">
                  <p className="text-3xl md:text-4xl font-black text-amber-500">
                    {stats.totalCertificates}
                  </p>
                  <p className="text-xs text-muted-foreground font-bold mt-1">
                    الشهادات
                  </p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div variants={statCardVariants}>
              <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-blue-500/30 transition-all group">
                <CardContent className="p-4 md:p-6 text-center">
                  <p className="text-3xl md:text-4xl font-black text-blue-500">
                    {stats.studentRank ? `#${stats.studentRank}` : "—"}
                  </p>
                  <p className="text-xs text-muted-foreground font-bold mt-1">
                    الترتيب
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          </>
        )}
      </div>

      {/* التوأم الرقمي */}
      <motion.div variants={cardVariants}>
        <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
          <CardContent className="p-6 md:p-8">
            <h2 className="text-2xl font-black flex items-center gap-3 text-foreground mb-6">
              <BrainCircuit className="h-6 w-6 text-purple-500" />
              التوأم الرقمي
            </h2>

            {isTwinLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-20 w-full rounded-xl bg-card/40 border border-white/5" />
                <Skeleton className="h-20 w-full rounded-xl bg-card/40 border border-white/5" />
              </div>
            ) : twinError ? (
              <div className="p-4 bg-destructive/10 rounded-xl border border-destructive/20 text-center">
                <p className="text-destructive font-bold">
                  {handleError(twinError, "جلب التوأم الرقمي").message}
                </p>
              </div>
            ) : digitalTwin ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-background/40 rounded-xl border border-white/5">
                  <p className="text-sm text-muted-foreground font-bold">
                    نمط التعلم
                  </p>
                  <p className="text-2xl font-black mt-1">
                    {digitalTwin.learning_style === "VISUAL"
                      ? "بصري 👁️"
                      : digitalTwin.learning_style === "AUDITORY"
                      ? "سمعي 🎧"
                      : digitalTwin.learning_style === "KINESTHETIC"
                      ? "حركي 🏃"
                      : "متكيف 🔄"}
                  </p>
                </div>
                <div className="p-4 bg-background/40 rounded-xl border border-white/5">
                  <p className="text-sm text-muted-foreground font-bold">
                    نقاط القوة
                  </p>
                  <p className="font-medium mt-1">
                    {digitalTwin.cognitive_map?.strengths || "تحليل مستمر..."}
                  </p>
                </div>
                <div className="p-4 bg-background/40 rounded-xl border border-white/5 md:col-span-2">
                  <p className="text-sm text-muted-foreground font-bold">
                    مناطق التطوير
                  </p>
                  <p className="font-medium mt-1">
                    {digitalTwin.cognitive_map?.weak_areas || "تحليل مستمر..."}
                  </p>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 bg-background/30 rounded-xl border border-dashed border-purple-500/20">
                <BrainCircuit className="mx-auto h-12 w-12 text-purple-500/30 mb-4" />
                <p className="text-muted-foreground font-medium">
                  جاري بناء التوأم الرقمي...
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* قائمة الشهادات */}
      <motion.div variants={cardVariants}>
        <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
          <CardContent className="p-6 md:p-8">
            <h2 className="text-2xl font-black flex items-center gap-3 text-foreground mb-6">
              <Award className="h-6 w-6 text-amber-500" />
              شهاداتي السيادية
            </h2>

            {isCertificatesLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-20 w-full rounded-xl bg-card/40 border border-white/5" />
                ))}
              </div>
            ) : certificatesError ? (
              <div className="p-4 bg-destructive/10 rounded-xl border border-destructive/20 text-center">
                <p className="text-destructive font-bold">
                  {handleError(certificatesError, "جلب الشهادات").message}
                </p>
              </div>
            ) : certificates.length === 0 ? (
              <div className="text-center py-12 bg-background/30 rounded-xl border border-dashed border-amber-500/20">
                <Award className="mx-auto h-12 w-12 text-amber-500/30 mb-4" />
                <p className="text-muted-foreground text-lg font-medium">
                  لم تحصل على أي شهادات بعد
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {certificates.map((cert: Certificate) => (
                  <div
                    key={cert.id}
                    className="flex flex-col md:flex-row items-start md:items-center justify-between p-4 bg-background/40 rounded-xl border border-white/5 hover:border-amber-500/30 transition-all group"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3">
                        <ShieldCheck className="h-5 w-5 text-amber-500" />
                        <h3 className="font-black text-lg group-hover:text-amber-500 transition-colors truncate">
                          {cert.course?.title || `كورس #${cert.course_id}`}
                        </h3>
                        <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 font-bold shrink-0">
                          {cert.grade}%
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 flex items-center gap-2">
                        <CalendarDays className="h-3 w-3" />
                        صدرت في{" "}
                        {new Date(cert.issued_at).toLocaleDateString("ar-EG")}
                      </p>
                    </div>
                    <Link href={`/academy/certificates/${cert.course_id}`}>
                      <Button
                        size="sm"
                        variant="outline"
                        className="rounded-xl border-amber-500/30 text-amber-500 hover:bg-amber-500 hover:text-white transition-colors font-bold mt-3 md:mt-0"
                      >
                        عرض الشهادة
                      </Button>
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}