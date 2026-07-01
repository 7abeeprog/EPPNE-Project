// app/(dashboard)/academy/page.tsx
"use client";

import { useState, useMemo, useCallback } from "react";
import Link from "next/link";
import Image from "next/image";
import { useQuery } from "@tanstack/react-query";
import { AcademyService } from "@/services/academy.service";
import { Course } from "@/types/academy";
import { handleError } from "@/lib/error-handler";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Search, BookOpen, Crown, Loader2 } from "lucide-react";
import { useDebounce } from "@/hooks/use-debounce";

export default function AcademyPage() {
  const [search, setSearch] = useState("");
  const [level, setLevel] = useState("");
  const debouncedSearch = useDebounce(search, 300);

  // 🔥 الحصول على النطاق الحالي
  const domain = typeof window !== "undefined" ? window.location.hostname : "localhost.com";

  // 🔥 1. جلب بيانات المستأجر (Tenant)
  const {
    data: tenant,
    isLoading: isTenantLoading,
    error: tenantError,
  } = useQuery({
    queryKey: ["academy", "tenant", domain],
    queryFn: () => AcademyService.getTenantByDomain(domain),
    enabled: !!domain,
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });

  // 🔥 2. جلب الكورسات المنشورة (مع Pagination)
  const {
    data: coursesData,
    isLoading: isCoursesLoading,
    error: coursesError,
  } = useQuery({
    queryKey: ["academy", "store-courses", tenant?.id],
    queryFn: () => AcademyService.getStoreCourses(0, 50),
    enabled: !!tenant?.id,
    staleTime: 2 * 60 * 1000,
    retry: 1,
  });

  const isLoading = isTenantLoading || isCoursesLoading;
  const courses = coursesData?.data || [];

  // 🔥 3. تصفية الكورسات (مع useMemo)
  const filteredCourses = useMemo(() => {
    if (!courses.length) return [];
    return courses.filter((course: Course) => {
      const matchSearch = course.title.toLowerCase().includes(debouncedSearch.toLowerCase());
      const matchLevel = level ? course.level === level : true;
      return matchSearch && matchLevel;
    });
  }, [courses, debouncedSearch, level]);

  // 🔥 4. معالجة الأخطاء
  if (tenantError) {
    const error = handleError(tenantError, "جلب بيانات الأكاديمية");
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="p-8 bg-destructive/10 backdrop-blur-md rounded-[2rem] border border-destructive/20 text-destructive font-bold text-center">
          <p>فشل في جلب بيانات الأكاديمية: {error.message}</p>
          <Button
            onClick={() => window.location.reload()}
            className="mt-4 bg-primary hover:bg-primary/90"
          >
            إعادة المحاولة
          </Button>
        </div>
      </div>
    );
  }

  if (coursesError && !isLoading) {
    const error = handleError(coursesError, "جلب الكورسات");
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="p-8 bg-destructive/10 backdrop-blur-md rounded-[2rem] border border-destructive/20 text-destructive font-bold text-center">
          <p>فشل في جلب الكورسات: {error.message}</p>
          <Button
            onClick={() => window.location.reload()}
            className="mt-4 bg-primary hover:bg-primary/90"
          >
            إعادة المحاولة
          </Button>
        </div>
      </div>
    );
  }

  // 🔥 5. حالة التحميل
  if (isLoading && !courses.length) {
    return (
      <div className="space-y-6 p-6 max-w-7xl mx-auto animate-in fade-in duration-500">
        <Skeleton className="h-48 w-full rounded-3xl bg-card/40" />
        <div className="flex justify-between items-center">
          <Skeleton className="h-8 w-48 bg-primary/10" />
          <Skeleton className="h-10 w-64 bg-primary/10" />
        </div>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-80 rounded-2xl bg-card/40 border border-primary/5" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 p-6 max-w-7xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* 🟢 رأس الصفحة الديناميكي (Glassmorphism & Neon Glow) */}
      <div className="relative overflow-hidden rounded-3xl bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 transition-all duration-500">
        <div className="absolute top-0 right-0 w-72 h-72 bg-primary/20 blur-[120px] rounded-full pointer-events-none -z-10 transition-colors duration-500" />
        <div className="flex items-center gap-4 mb-2">
          <div className="p-3 bg-primary/10 rounded-2xl border border-primary/30 shadow-[0_0_15px_rgba(var(--primary-rgb),0.2)]">
            <Crown className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-4xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-foreground to-primary drop-shadow-sm">
            {tenant?.name || "الأكاديمية السيادية"}
          </h1>
        </div>
        <p className="text-muted-foreground mt-4 text-lg max-w-2xl font-medium">
          أهلاً بك في مقر القيادة الأكاديمية. من هنا يمكنك استكشاف المسارات التعليمية المتاحة، بناء مهاراتك، والحصول على شهادات موثقة في منصة EPPNE.COM.
        </p>
      </div>

      {/* 🟢 شريط البحث والفلترة */}
      <div className="flex flex-col sm:flex-row gap-4 bg-card/30 p-4 rounded-2xl border border-primary/10 backdrop-blur-md shadow-sm">
        <div className="relative flex-1">
          <Search className="absolute right-4 top-1/2 -translate-y-1/2 h-5 w-5 text-primary/50" />
          <Input
            placeholder="ابحث عن كورس..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pr-12 h-12 text-md bg-background/50 border-primary/20 rounded-xl focus:border-primary focus:ring-1 focus:ring-primary/50 transition-all"
          />
        </div>
        <select
          className="border border-primary/20 rounded-xl px-4 h-12 bg-background/50 text-foreground focus:ring-2 focus:ring-primary/50 outline-none transition-all cursor-pointer"
          value={level}
          onChange={(e) => setLevel(e.target.value)}
        >
          <option value="">جميع المستويات</option>
          <option value="BEGINNER">مبتدئ</option>
          <option value="INTERMEDIATE">متوسط</option>
          <option value="ADVANCED">متقدم</option>
        </select>
      </div>

      {/* 🟢 عرض الكورسات */}
      {filteredCourses.length === 0 ? (
        <div className="text-center py-20 bg-card/20 backdrop-blur-sm rounded-3xl border border-dashed border-primary/30 relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent to-primary/5 pointer-events-none" />
          <BookOpen className="h-16 w-16 mx-auto text-primary/40 mb-4 animate-pulse" />
          <h3 className="text-2xl font-bold">المستودع فارغ حالياً</h3>
          <p className="text-muted-foreground mt-2">
            {search || level ? "لا توجد كورسات تطابق معايير البحث." : "لم يتم إطلاق أي كورسات في هذه الأكاديمية حتى الآن."}
          </p>
          <Link href="/academy/admin/studio">
            <Button className="mt-6 font-bold shadow-[0_0_20px_rgba(var(--primary-rgb),0.2)] hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.4)] hover:scale-105 transition-all duration-300 rounded-xl px-8 h-12">
              الانتقال لاستوديو الإدارة لبناء كورس
            </Button>
          </Link>
        </div>
      ) : (
        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
          {filteredCourses.map((course: Course) => (
            <Card
              key={course.id}
              className="hover:shadow-[0_0_30px_-10px_rgba(var(--primary-rgb),0.4)] transition-all duration-500 border-primary/10 overflow-hidden group bg-card/40 backdrop-blur-lg hover:bg-card/60 hover:-translate-y-1"
            >
              {course.thumbnail_url ? (
                <div className="relative h-48 w-full overflow-hidden bg-muted">
                  <Image
                    src={course.thumbnail_url}
                    alt={course.title}
                    fill
                    className="object-cover group-hover:scale-110 transition-transform duration-700 ease-in-out"
                    loading="lazy"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-background/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                </div>
              ) : (
                <div className="relative h-48 w-full overflow-hidden bg-gradient-to-br from-primary/10 to-background flex items-center justify-center group-hover:from-primary/20 transition-colors duration-500">
                  <BookOpen className="h-12 w-12 text-primary/30 group-hover:scale-110 transition-transform duration-500" />
                </div>
              )}
              <CardHeader className="relative z-10">
                <CardTitle className="line-clamp-1 text-xl group-hover:text-primary transition-colors">
                  {course.title}
                </CardTitle>
                <CardDescription className="line-clamp-2 h-10 mt-1">
                  {course.description || "لا يوجد وصف متاح لهذا الكورس حتى الآن."}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between mt-2">
                  <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 shadow-inner">
                    {course.level === "BEGINNER" && "مبتدئ"}
                    {course.level === "INTERMEDIATE" && "متوسط"}
                    {course.level === "ADVANCED" && "متقدم"}
                  </Badge>
                  <span className="font-extrabold text-lg bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-emerald-600 drop-shadow-md">
                    {course.is_free ? "مجاني" : `${Number(course.price_mrusdt).toLocaleString("en-US")} ${course.currency}`}
                  </span>
                </div>
              </CardContent>
              <CardFooter>
                <Link href={`/academy/courses/${course.id}`} className="w-full">
                  <Button className="w-full h-12 text-md shadow-md bg-primary/90 hover:bg-primary hover:shadow-[0_0_20px_rgba(var(--primary-rgb),0.4)] transition-all duration-300 rounded-xl">
                    استكشاف الكورس
                  </Button>
                </Link>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}

      {/* 🟢 تحميل المزيد (إذا كان هناك المزيد من الصفحات) */}
      {coursesData && coursesData.total > coursesData.data.length && (
        <div className="flex justify-center pt-4">
          <Button
            variant="outline"
            className="h-12 px-8 font-bold rounded-xl border-primary/20 hover:bg-primary/10 transition-all"
            onClick={() => {
              // يمكن إضافة منطق تحميل الصفحة التالية هنا باستخدام useInfiniteQuery
            }}
          >
            تحميل المزيد من الكورسات
          </Button>
        </div>
      )}
    </div>
  );
}