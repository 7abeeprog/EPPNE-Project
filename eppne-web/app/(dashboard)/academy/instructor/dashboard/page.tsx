// app/(dashboard)/academy/instructor/dashboard/page.tsx
"use client";

import { useMemo } from "react";
import Link from "next/link";
import { motion, Variants } from "framer-motion";

// ✅ الهوكات الجديدة
import { useInstructorCourses, useInstructorStats } from "@/hooks/academy-queries";
import { handleError } from "@/lib/error-handler";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  BarChart3,
  BookOpen,
  Users,
  Award,
  Target,
  FileText,
  Radio,
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

export default function InstructorDashboard() {
  const {
    data: stats,
    isLoading: isStatsLoading,
    error: statsError,
  } = useInstructorStats();

  const {
    data: coursesData,
    isLoading: isCoursesLoading,
    error: coursesError,
  } = useInstructorCourses(0, 10);

  const courses = coursesData?.data || [];

  if (statsError) {
    const error = handleError(statsError, "جلب إحصائيات المدرب");
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

  const isLoading = isStatsLoading || isCoursesLoading;

  const statCards = useMemo(
    () => [
      {
        title: "إجمالي الكورسات",
        value: stats?.total_courses || 0,
        icon: BookOpen,
        color: "text-blue-500",
        bg: "bg-blue-500/10",
        border: "border-blue-500/20",
      },
      {
        title: "الطلاب المسجلين",
        value: stats?.total_students || 0,
        icon: Users,
        color: "text-emerald-500",
        bg: "bg-emerald-500/10",
        border: "border-emerald-500/20",
      },
      {
        title: "التكليفات المعلقة",
        value: stats?.pending_submissions || 0,
        icon: Target,
        color: "text-orange-500",
        bg: "bg-orange-500/10",
        border: "border-orange-500/20",
      },
      {
        title: "الشهادات الصادرة",
        value: stats?.total_certificates || 0,
        icon: Award,
        color: "text-amber-500",
        bg: "bg-amber-500/10",
        border: "border-amber-500/20",
      },
    ],
    [stats]
  );

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative"
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(59,130,246,0.05),_transparent_80%)] pointer-events-none -z-10" />

      <motion.div
        variants={cardVariants}
        className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10"
      >
        <div className="absolute top-0 right-0 w-72 h-72 bg-blue-500/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse" />
        <div className="flex items-center gap-6">
          <div className="p-4 bg-blue-500/10 rounded-2xl border border-blue-500/20 shadow-inner">
            <BarChart3 className="h-12 w-12 text-blue-500" />
          </div>
          <div>
            <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-blue-500 drop-shadow-sm">
              لوحة تحكم المدرب
            </h1>
            <p className="text-muted-foreground mt-2 text-lg md:text-xl font-medium">
              نظرة عامة على الكورسات، الطلاب، والتكليفات الخاصة بك.
            </p>
          </div>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {isLoading ? (
          [1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-36 rounded-[2rem] bg-card/40 border border-white/5" />
          ))
        ) : (
          statCards.map((stat, index) => (
            <motion.div key={index} variants={cardVariants}>
              <Card className={`border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:${stat.border} hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.1)] transition-all group`}>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className={`p-3 ${stat.bg} rounded-xl border ${stat.border}`}>
                      <stat.icon className={`h-6 w-6 ${stat.color}`} />
                    </div>
                    <span className="text-3xl md:text-4xl font-black drop-shadow-sm">
                      {stat.value}
                    </span>
                  </div>
                  <p className="text-muted-foreground font-bold text-sm">
                    {stat.title}
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          ))
        )}
      </div>

      <motion.div variants={cardVariants}>
        <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
          <CardContent className="p-6 md:p-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-black flex items-center gap-3 text-foreground">
                <BookOpen className="h-6 w-6 text-blue-500" />
                كورساتي
              </h2>
              <Link href="/academy/admin/studio">
                <Button size="sm" className="rounded-xl font-bold">
                  إنشاء كورس جديد
                </Button>
              </Link>
            </div>

            {isCoursesLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-20 rounded-xl bg-card/40 border border-white/5" />
                ))}
              </div>
            ) : coursesError ? (
              <div className="p-6 bg-destructive/10 rounded-xl border border-destructive/20 text-center">
                <p className="text-destructive font-bold">
                  {handleError(coursesError, "جلب كورسات المدرب").message}
                </p>
              </div>
            ) : courses.length === 0 ? (
              <div className="text-center py-12 bg-background/30 rounded-xl border border-dashed border-blue-500/20">
                <BookOpen className="mx-auto h-12 w-12 text-blue-500/30 mb-4" />
                <p className="text-muted-foreground text-lg font-medium">
                  لا توجد كورسات مسجلة باسمك.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {courses.map((course: any) => (
                  <div
                    key={course.id}
                    className="flex flex-col md:flex-row items-start md:items-center justify-between p-4 bg-background/40 rounded-xl border border-white/5 hover:border-blue-500/30 transition-all group"
                  >
                    <div className="flex-1 min-w-0">
                      <h3 className="font-black text-lg group-hover:text-blue-500 transition-colors">
                        {course.title}
                      </h3>
                      <div className="flex flex-wrap items-center gap-3 mt-1">
                        <Badge variant="outline" className="border-white/10 text-xs">
                          {course.students_count || 0} طالب
                        </Badge>
                        <Badge variant="outline" className="border-white/10 text-xs">
                          {course.tasks_count || 0} تكليف
                        </Badge>
                        <Badge
                          className={`text-xs ${
                            course.is_published
                              ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                              : "bg-orange-500/10 text-orange-500 border-orange-500/20"
                          } border font-bold`}
                        >
                          {course.is_published ? "منشور" : "مسودة"}
                        </Badge>
                      </div>
                    </div>
                    <div className="flex gap-2 mt-3 md:mt-0">
                      <Link href={`/academy/admin/studio?courseId=${course.id}`}>
                        <Button
                          variant="outline"
                          size="sm"
                          className="rounded-xl border-blue-500/30 text-blue-500 hover:bg-blue-500 hover:text-white transition-colors font-bold"
                        >
                          <FileText className="h-4 w-4 ml-1" />
                          تحرير
                        </Button>
                      </Link>
                      <Link href={`/academy/classroom/${course.id}`}>
                        <Button
                          size="sm"
                          className="rounded-xl bg-blue-600 hover:bg-blue-500 font-bold"
                        >
                          <Radio className="h-4 w-4 ml-1" />
                          عرض
                        </Button>
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      <motion.div variants={cardVariants}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Link href="/academy/instructor/grading">
            <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-blue-500/50 hover:shadow-[0_0_30px_rgba(59,130,246,0.15)] transition-all group">
              <CardContent className="p-6 text-center">
                <div className="p-3 bg-orange-500/10 rounded-xl border border-orange-500/20 w-fit mx-auto mb-3 group-hover:scale-110 transition-transform">
                  <Target className="h-6 w-6 text-orange-500" />
                </div>
                <p className="font-bold text-sm">التقييم والاعتماد</p>
              </CardContent>
            </Card>
          </Link>

          <Link href="/academy/admin/live-sessions">
            <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-blue-500/50 hover:shadow-[0_0_30px_rgba(59,130,246,0.15)] transition-all group">
              <CardContent className="p-6 text-center">
                <div className="p-3 bg-blue-500/10 rounded-xl border border-blue-500/20 w-fit mx-auto mb-3 group-hover:scale-110 transition-transform">
                  <Radio className="h-6 w-6 text-blue-500" />
                </div>
                <p className="font-bold text-sm">الجلسات الحية</p>
              </CardContent>
            </Card>
          </Link>

          <Link href="/academy/admin/tasks">
            <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-blue-500/50 hover:shadow-[0_0_30px_rgba(59,130,246,0.15)] transition-all group">
              <CardContent className="p-6 text-center">
                <div className="p-3 bg-purple-500/10 rounded-xl border border-purple-500/20 w-fit mx-auto mb-3 group-hover:scale-110 transition-transform">
                  <FileText className="h-6 w-6 text-purple-500" />
                </div>
                <p className="font-bold text-sm">إدارة التكليفات</p>
              </CardContent>
            </Card>
          </Link>

          <Link href="/academy/leaderboard">
            <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-blue-500/50 hover:shadow-[0_0_30px_rgba(59,130,246,0.15)] transition-all group">
              <CardContent className="p-6 text-center">
                <div className="p-3 bg-amber-500/10 rounded-xl border border-amber-500/20 w-fit mx-auto mb-3 group-hover:scale-110 transition-transform">
                  <Award className="h-6 w-6 text-amber-500" />
                </div>
                <p className="font-bold text-sm">لوحة الشرف</p>
              </CardContent>
            </Card>
          </Link>
        </div>
      </motion.div>
    </motion.div>
  );
}