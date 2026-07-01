// app/(dashboard)/academy/admin/courses/page.tsx
"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";

// ✅ استبدال academy-store بالهوكات الجديدة
import { useCourses, useOrganizationEntities } from "@/hooks/academy-queries";
import { Course, OrganizationEntity } from "@/types/academy";
import { handleError } from "@/lib/error-handler";

import {
  BookOpen,
  Search,
  Shield,
  Network,
  ArrowLeft,
  Tent,
  Route,
  Layers,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

// ✅ دالة ترويض الأصفار (محسّنة للاستخدام المتكرر)
const formatSovereignPrice = (price: number | string) => {
  const numericPrice = typeof price === "string" ? parseFloat(price) : price;
  if (isNaN(numericPrice)) return "0";
  return numericPrice.toLocaleString("en-US", { maximumFractionDigits: 2 });
};

export default function CoursesDashboard() {
  const router = useRouter();
  const [searchTerm, setSearchTerm] = useState("");

  // ✅ 1. جلب الكيانات التنظيمية (مع Pagination و Cache)
  const {
    data: orgEntitiesData,
    isLoading: isOrgsLoading,
    error: orgsError,
  } = useOrganizationEntities(0, 100);

  const orgEntities = orgEntitiesData?.data || [];

  // ✅ 2. جلب الكورسات (مع Pagination)
  const {
    data: coursesData,
    isLoading: isCoursesLoading,
    error: coursesError,
  } = useCourses(0, 50);

  const courses = coursesData?.data || [];

  const isLoading = isOrgsLoading || isCoursesLoading;

  // ✅ 3. إنشاء خريطة الكيانات للوصول السريع (useMemo)
  const orgMap = useMemo(() => {
    const map: Record<number, string> = {};
    orgEntities.forEach((org: OrganizationEntity) => {
      map[org.id] = org.name;
    });
    return map;
  }, [orgEntities]);

  // ✅ 4. فلترة الكورسات (useMemo)
  const filteredCourses = useMemo(() => {
    if (!searchTerm.trim()) return courses;
    return courses.filter((course: Course) =>
      course.title.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [courses, searchTerm]);

  // ✅ 5. دالة الحصول على اسم الكيان
  const getOrgName = (id: number) => {
    return orgMap[id] || "كيان غير معروف";
  };

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
    <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* خلفية النيون الزجاجي */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,_rgba(var(--primary-rgb),0.05),_transparent_70%)] pointer-events-none -z-10" />

      {/* رأس الصفحة */}
      <div className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_40px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 w-full">
        <div className="absolute top-0 right-0 w-72 h-72 bg-primary/20 blur-[120px] rounded-full pointer-events-none -z-10" />
        <div className="flex-1">
          <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-primary flex items-center gap-4 drop-shadow-sm">
            <div className="p-3 bg-primary/10 rounded-2xl border border-primary/20 shadow-inner">
              <BookOpen className="h-10 w-10 text-primary" />
            </div>
            الترسانة المركزية للمقررات
          </h1>
          <p className="text-muted-foreground mt-4 text-lg md:text-xl font-medium max-w-2xl">
            مستودع الكورسات السيادية. راجع، أدر، وتتبع كافة المقررات المصنعة في الأكاديمية.
          </p>
        </div>
        <Link href="/academy/admin/studio">
          <Button
            size="lg"
            className="h-16 px-8 text-xl font-bold shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:scale-105 transition-transform rounded-2xl w-full md:w-auto"
          >
            الذهاب لاستوديو الإبداع <ArrowLeft className="mr-2 h-6 w-6" />
          </Button>
        </Link>
      </div>

      {/* شريط البحث والفلترة */}
      <div className="flex items-center gap-4 w-full bg-card/40 backdrop-blur-md p-4 rounded-2xl border border-white/5 shadow-inner">
        <div className="relative flex-1">
          <Search className="absolute right-4 top-1/2 -translate-y-1/2 text-primary/50 h-5 w-5" />
          <Input
            placeholder="ابحث في الترسانة بالاسم..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full h-14 pr-12 text-lg rounded-xl bg-background/50 border-primary/20 focus:border-primary focus:ring-1 focus:ring-primary/50 transition-all shadow-sm"
          />
        </div>
      </div>

      {/* شبكة عرض الكورسات */}
      <div className="w-full">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton
                key={i}
                className="h-96 rounded-[2rem] bg-card/40 border border-white/5"
              />
            ))}
          </div>
        ) : filteredCourses.length === 0 ? (
          <div className="text-center py-20 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-primary/30">
            <Layers className="mx-auto h-20 w-20 text-primary/20 mb-4 animate-pulse" />
            <h2 className="text-2xl font-bold text-foreground">
              {searchTerm ? "لا توجد كورسات تطابق بحثك" : "الترسانة فارغة"}
            </h2>
            <p className="text-muted-foreground mt-2 text-lg">
              {searchTerm
                ? "جرب كلمات بحث مختلفة أو امسح الفلتر."
                : "قم بتأسيس كورس سيادي جديد من استوديو الإبداع."}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
            {filteredCourses.map((course: Course) => (
              <div
                key={course.id}
                className="flex flex-col h-full bg-card/40 backdrop-blur-2xl border border-white/10 rounded-[2rem] overflow-hidden hover:border-primary/50 transition-all duration-300 hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] group hover:-translate-y-1"
              >
                {/* منطقة الصورة العلوية */}
                <div className="h-52 w-full bg-background/50 relative overflow-hidden border-b border-white/5">
                  {course.thumbnail_url ? (
                    <Image
                      src={course.thumbnail_url}
                      alt={course.title}
                      fill
                      className="object-cover transition-transform duration-700 group-hover:scale-110"
                      sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center bg-[radial-gradient(ellipse_at_center,_rgba(var(--primary-rgb),0.1),_transparent)]">
                      <Shield className="w-24 h-24 text-primary/20 group-hover:scale-110 group-hover:text-primary/40 transition-all duration-500" />
                    </div>
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-background/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

                  {/* شارة المستوى */}
                  <div className="absolute top-4 right-4 bg-background/80 backdrop-blur-md px-4 py-1.5 rounded-full text-xs font-black border border-primary/20 text-primary shadow-sm">
                    {course.level === "BEGINNER"
                      ? "تأسيسي"
                      : course.level === "INTERMEDIATE"
                      ? "تطبيقي"
                      : "احترافي"}
                  </div>

                  {/* شارة المجانية */}
                  {course.is_free && (
                    <div className="absolute top-4 left-4 bg-emerald-500/90 backdrop-blur-md px-4 py-1.5 rounded-full text-xs font-black text-white shadow-sm">
                      مجاني
                    </div>
                  )}
                </div>

                {/* منطقة المحتوى والمعلومات */}
                <div className="p-6 flex flex-col flex-grow relative z-10">
                  <h3 className="text-2xl font-black mb-4 line-clamp-2 text-foreground group-hover:text-primary transition-colors">
                    {course.title}
                  </h3>

                  <div className="space-y-3 mb-8">
                    <div className="flex items-center text-sm font-medium bg-background/40 p-2.5 rounded-xl border border-white/5 shadow-inner">
                      <div className="p-1.5 bg-emerald-500/10 rounded-lg mr-2">
                        <Network className="h-4 w-4 text-emerald-500" />
                      </div>
                      <span className="truncate text-muted-foreground ml-2">
                        الكيان:{" "}
                        <strong className="text-foreground">
                          {getOrgName(course.org_entity_id)}
                        </strong>
                      </span>
                    </div>

                    {course.bootcamp_id && (
                      <div className="flex items-center text-sm font-medium bg-background/40 p-2.5 rounded-xl border border-white/5 shadow-inner">
                        <div className="p-1.5 bg-primary/10 rounded-lg mr-2">
                          <Tent className="h-4 w-4 text-primary" />
                        </div>
                        <span className="truncate text-muted-foreground ml-2">
                          مقيد بمعسكر:{" "}
                          <strong className="text-foreground">
                            #{course.bootcamp_id}
                          </strong>
                        </span>
                      </div>
                    )}

                    {course.track_id && (
                      <div className="flex items-center text-sm font-medium bg-background/40 p-2.5 rounded-xl border border-white/5 shadow-inner">
                        <div className="p-1.5 bg-purple-500/10 rounded-lg mr-2">
                          <Route className="h-4 w-4 text-purple-500" />
                        </div>
                        <span className="truncate text-muted-foreground ml-2">
                          مسار:{" "}
                          <strong className="text-foreground">
                            #{course.track_id}
                          </strong>
                        </span>
                      </div>
                    )}
                  </div>

                  {/* التسعير وزر الإدارة */}
                  <div className="mt-auto pt-5 border-t border-border/50">
                    <div className="flex justify-between items-end mb-5">
                      <span className="text-sm text-muted-foreground font-bold flex items-center gap-2">
                        <Shield className="w-4 h-4 text-primary" />
                        الاستثمار السيادي
                      </span>
                      <div className="text-left flex items-baseline gap-1.5">
                        <span className="text-sm font-black text-muted-foreground">
                          {course.currency}
                        </span>
                        <span className="text-3xl font-black text-primary drop-shadow-sm">
                          {course.is_free
                            ? "مجاني"
                            : formatSovereignPrice(course.price_mrusdt)}
                        </span>
                      </div>
                    </div>

                    <Button
                      onClick={() =>
                        router.push(
                          `/academy/admin/studio?courseId=${course.id}`
                        )
                      }
                      className="w-full h-14 rounded-xl text-lg font-bold shadow-[0_0_15px_rgba(var(--primary-rgb),0.2)] hover:shadow-[0_0_25px_rgba(var(--primary-rgb),0.4)] transition-all"
                    >
                      إدارة الكورس
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}