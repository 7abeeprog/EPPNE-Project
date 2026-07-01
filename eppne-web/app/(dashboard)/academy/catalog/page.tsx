// app/(dashboard)/academy/catalog/page.tsx
"use client";

import { useState, useMemo, useCallback } from "react";
import Image from "next/image";
import { toast } from "sonner";

// ✅ استبدال المتاجر القديمة بالهوكات الجديدة
import {
  useStoreCourses,
  useOrganizationEntities,
  useEnrollMutation,
} from "@/hooks/academy-queries";
import { Course, OrganizationEntity } from "@/types/academy";
import { handleError } from "@/lib/error-handler";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Search,
  GraduationCap,
  Star,
  Network,
  Rocket,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { Input } from "@/components/ui/input";

export default function StudentCatalogPage() {
  const [searchQuery, setSearchQuery] = useState("");

  // ✅ 1. جلب الكيانات التنظيمية (مع Cache)
  const {
    data: orgEntitiesData,
    isLoading: isOrgsLoading,
    error: orgsError,
  } = useOrganizationEntities(0, 100);

  const orgEntities = orgEntitiesData?.data || [];

  // ✅ 2. جلب الكورسات المنشورة من المتجر (مع Pagination)
  const {
    data: coursesData,
    isLoading: isCoursesLoading,
    error: coursesError,
  } = useStoreCourses(0, 20); // 20 كورس في الصفحة الأولى

  const courses = coursesData?.data || [];

  const isLoading = isOrgsLoading || isCoursesLoading;

  // ✅ 3. تصفية الكورسات (useMemo)
  const filteredCourses = useMemo(() => {
    if (!searchQuery.trim()) return courses;
    return courses.filter((course: Course) =>
      course.title.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [courses, searchQuery]);

  // ✅ 4. محرك التسجيل (Mutation)
  const enrollMutation = useEnrollMutation();

  // ✅ 5. دالة التسجيل (useCallback)
  const handleEnroll = useCallback(
    (courseId: number) => {
      const course = courses.find((c) => c.id === courseId);
      if (!course) return;

      enrollMutation.mutate(
        {
          courseId,
          payload: {
            payment_method: course.is_free || course.price_mrusdt === 0 ? "FREE" : "WALLET",
          },
        },
        {
          onSuccess: () => {
            toast.success("تم تسجيلك في الكورس بنجاح! 🚀");
          },
          onError: (error) => {
            const err = handleError(error, "التسجيل في الكورس");
            toast.error(err.message);
          },
        }
      );
    },
    [courses, enrollMutation]
  );

  // ✅ 6. معالجة الأخطاء
  if (orgsError) {
    const error = handleError(orgsError, "جلب الكيانات التنظيمية");
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

  return (
    <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative">
      {/* خلفية نيون زجاجية */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(var(--primary-rgb),0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* الهيدر الترحيبي */}
      <div className="relative overflow-hidden rounded-[2rem] bg-card/60 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-12 flex flex-col items-center text-center w-full">
        <div className="absolute top-0 right-0 w-96 h-96 bg-primary/20 blur-[150px] rounded-full pointer-events-none -z-10 animate-pulse duration-1000" />
        <div className="absolute bottom-0 left-0 w-72 h-72 bg-emerald-500/10 blur-[120px] rounded-full pointer-events-none -z-10" />

        <div className="p-4 bg-primary/10 rounded-3xl border border-primary/30 shadow-[0_0_20px_rgba(var(--primary-rgb),0.2)] mb-6">
          <GraduationCap className="h-16 w-16 text-primary animate-bounce" />
        </div>
        <h1 className="text-4xl md:text-6xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-primary mb-4 drop-shadow-sm">
          اكتشف قدراتك السيادية
        </h1>
        <p className="text-muted-foreground text-lg md:text-xl font-medium max-w-2xl">
          تصفح مساراتنا التعليمية، انضم إلى دفعات النخبة، وابدأ رحلتك في أكاديمية EPPNE اليوم.
        </p>

        <div className="relative w-full max-w-2xl mt-10">
          <Search className="absolute right-6 top-1/2 -translate-y-1/2 text-primary/50 h-6 w-6" />
          <Input
            placeholder="عن ماذا تبحث اليوم؟ (مثال: العقود الذكية، الإدارة...)"
            className="w-full h-16 pr-16 text-xl rounded-full bg-background/50 backdrop-blur-md border-primary/20 focus:border-primary focus:ring-1 focus:ring-primary/50 shadow-xl transition-all"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* عرض الكورسات المتاحة للتسجيل */}
      <div className="w-full animate-in fade-in slide-in-from-bottom-8 duration-700">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="flex flex-col gap-4">
                <Skeleton className="h-56 w-full rounded-[2rem] bg-card/40 border border-white/5" />
                <Skeleton className="h-8 w-3/4 bg-card/40" />
                <Skeleton className="h-4 w-full bg-card/40" />
                <Skeleton className="h-12 w-full mt-4 rounded-xl bg-card/40" />
              </div>
            ))}
          </div>
        ) : filteredCourses.length === 0 ? (
          <div className="col-span-full text-center py-20 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-primary/30">
            <Rocket className="mx-auto h-20 w-20 text-primary/20 mb-4 animate-pulse" />
            <h2 className="text-3xl font-bold text-foreground">
              {searchQuery ? "لا توجد كورسات مطابقة" : "لا توجد كورسات متاحة"}
            </h2>
            <p className="text-muted-foreground mt-2 text-lg">
              {searchQuery
                ? "لم يتم العثور على أي مسارات تطابق بحثك الحالي."
                : "سيتم إضافة كورسات جديدة قريباً. تابعنا!"}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {filteredCourses.map((course: Course) => {
              const orgName = orgEntities.find(
                (o: OrganizationEntity) => o.id === course.org_entity_id
              )?.name || "الكيان المركزي";
              const isEnrolling =
                enrollMutation.isPending &&
                enrollMutation.variables?.courseId === course.id;

              return (
                <Card
                  key={course.id}
                  className="group overflow-hidden border-white/10 bg-card/40 backdrop-blur-xl hover:border-primary/50 hover:shadow-[0_0_40px_-10px_rgba(var(--primary-rgb),0.3)] transition-all duration-500 rounded-[2rem] flex flex-col hover:-translate-y-2"
                >
                  <div className="h-56 w-full bg-gradient-to-br from-primary/10 to-background relative overflow-hidden flex items-center justify-center border-b border-white/5">
                    <div className="absolute inset-0 bg-background/20 group-hover:bg-transparent transition-colors duration-500 z-10" />
                    {course.thumbnail_url ? (
                      <Image
                        src={course.thumbnail_url}
                        alt={course.title}
                        fill
                        className="object-cover mix-blend-overlay opacity-60 group-hover:opacity-100 group-hover:scale-110 transition-all duration-700"
                        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                      />
                    ) : (
                      <GraduationCap className="h-20 w-20 text-primary/20 group-hover:scale-110 transition-transform duration-500" />
                    )}

                    <div className="absolute top-4 right-4 z-20 bg-background/80 backdrop-blur-md px-4 py-1.5 rounded-full text-xs font-black border border-primary/20 text-primary shadow-lg">
                      {course.level === "BEGINNER"
                        ? "تأسيسي"
                        : course.level === "INTERMEDIATE"
                        ? "تطبيقي"
                        : "احترافي"}
                    </div>

                    {course.is_free && (
                      <div className="absolute top-4 left-4 z-20 bg-emerald-500/90 backdrop-blur-md px-4 py-1.5 rounded-full text-xs font-black text-white shadow-lg">
                        مجاني
                      </div>
                    )}
                  </div>

                  <CardContent className="p-8 flex-1 flex flex-col relative z-20">
                    <div className="flex items-center gap-2 mb-3 text-emerald-500 text-sm font-bold bg-emerald-500/10 w-fit px-2 py-1 rounded-md border border-emerald-500/20">
                      <Star className="h-4 w-4 fill-emerald-500" /> 4.9 (تقييم استرشادي)
                    </div>

                    <h3 className="text-2xl font-black mb-3 line-clamp-2 leading-tight text-foreground group-hover:text-primary transition-colors">
                      {course.title}
                    </h3>
                    <p className="text-muted-foreground text-sm line-clamp-2 mb-6 font-medium">
                      {course.description || "كورس أكاديمي متخصص لبناء القدرات المعرفية والعملية."}
                    </p>

                    <div className="flex items-center gap-3 text-sm text-muted-foreground bg-background/40 p-3 rounded-xl border border-white/5 mb-6 shadow-inner">
                      <div className="p-1.5 bg-primary/10 rounded-lg">
                        <Network className="h-4 w-4 text-primary" />
                      </div>
                      <span className="truncate font-bold text-foreground">
                        {orgName}
                      </span>
                    </div>

                    <div className="flex items-center justify-between mt-auto pt-6 border-t border-border/50">
                      <div className="flex flex-col">
                        <span className="text-xs text-muted-foreground font-bold mb-1">
                          استثمار الكورس
                        </span>
                        <div className="flex items-baseline gap-1">
                          {course.is_free || course.price_mrusdt === 0 ? (
                            <span className="text-2xl font-black text-emerald-500 drop-shadow-sm">
                              مجاني
                            </span>
                          ) : (
                            <>
                              <span className="text-2xl font-black text-primary drop-shadow-sm">
                                {Number(course.price_mrusdt).toLocaleString("en-US")}
                              </span>
                              <span className="text-xs font-bold text-muted-foreground">
                                {course.currency || "MR_USDT"}
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                      <Button
                        onClick={() => handleEnroll(course.id)}
                        disabled={isEnrolling}
                        size="lg"
                        className={`rounded-xl shadow-[0_0_15px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_25px_rgba(var(--primary-rgb),0.5)] font-bold px-8 h-12 ${
                          course.is_free || course.price_mrusdt === 0
                            ? "bg-emerald-500 hover:bg-emerald-600"
                            : ""
                        }`}
                      >
                        {isEnrolling ? (
                          <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                          "تسجيل الآن"
                        )}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* 🟢 زر تحميل المزيد (Pagination) */}
        {coursesData && coursesData.total > courses.length && (
          <div className="flex justify-center pt-8">
            <Button
              variant="outline"
              className="h-12 px-8 font-bold rounded-xl border-primary/20 hover:bg-primary/10 transition-all"
              onClick={() => {
                // سيتم إضافة منطق تحميل الصفحة التالية مع useInfiniteQuery
                toast.info("سيتم إضافة التحميل التدريجي في التحديث القادم");
              }}
            >
              تحميل المزيد من الكورسات
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}