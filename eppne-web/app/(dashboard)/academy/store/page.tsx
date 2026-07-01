"use client";

// 🟢 1. استدعاء المحرك السيادي (TanStack Query) بدلاً من Zustand لإدارة حالة الخادم والكاش
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CourseActionButton } from "@/components/academy/CourseActionButton";
import { Shield, Sparkles } from "lucide-react";
import Link from "next/link";

export default function AcademyStorefront() {
  
  // 🟢 2. جلب الكورسات المعروضة في المتجر عبر الكاش السيادي
  const { data: storeCourses = [], isLoading: isCoursesLoading } = useQuery({
    queryKey: ['academy', 'store-courses'],
    queryFn: () => apiClient.get('/academy/store/courses').then(res => res.data),
    staleTime: 1000 * 60 * 15, // كاش تكتيكي لمدة 15 دقيقة
  });

  // 🟢 3. جلب تسجيلات الطالب لضمان تحديث حالة المكون الذكي (CourseActionButton)
  const { isLoading: isEnrollmentsLoading } = useQuery({
    queryKey: ['student', 'my-enrollments'],
    queryFn: () => apiClient.get('/academy/student/enrollments').then(res => res.data),
    staleTime: 1000 * 60 * 5,
  });

  const isLoading = isCoursesLoading || isEnrollmentsLoading;

  return (
    <div className="flex flex-col w-full min-w-0 space-y-10 p-4 md:p-8 max-w-7xl mx-auto relative animate-in fade-in slide-in-from-bottom-4 duration-700">
      
      {/* 🟢 خلفية نيون زجاجية متغيرة */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(var(--primary-rgb),0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* 🟢 هيدر المتجر المبهر (Glassmorphism) */}
      <div className="relative rounded-[2.5rem] bg-card/40 backdrop-blur-2xl border border-white/10 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-10 md:p-16 overflow-hidden flex flex-col md:flex-row items-center gap-8 w-full">
        <div className="absolute top-[-50%] right-[-10%] w-96 h-96 bg-primary/20 blur-[150px] rounded-full animate-pulse duration-1000 pointer-events-none -z-10" />
        <div className="flex-1 relative z-10">
          <h1 className="text-4xl md:text-6xl font-black mb-4 bg-clip-text text-transparent bg-gradient-to-r from-foreground to-primary drop-shadow-sm">
            المتجر الأكاديمي السيادي
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl font-medium">
            تصفح مسارات الذكاء الاصطناعي، المعسكرات، والكورسات المعتمدة. استثمر في عقلك بعملات نبت أو مجاناً.
          </p>
        </div>
      </div>

      {/* 🟢 شبكة الكورسات */}
      <div className="w-full">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[1, 2, 3, 4, 5, 6].map(i => (
              <Skeleton key={i} className="h-96 rounded-[2.5rem] bg-card/40 border border-white/5" />
            ))}
          </div>
        ) : storeCourses.length === 0 ? (
          <div className="text-center py-20 bg-card/20 backdrop-blur-sm rounded-[2.5rem] border border-dashed border-primary/20">
            <Sparkles className="mx-auto h-16 w-16 text-primary/30 mb-4 animate-pulse" />
            <h2 className="text-3xl font-black text-foreground">المتجر قيد التجهيز</h2>
            <p className="text-muted-foreground mt-2 text-lg">لم يتم طرح أي مسارات جديدة في المتجر حالياً.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {storeCourses.map((course: any) => (
              <Card key={course.id} className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2.5rem] overflow-hidden hover:border-primary/50 hover:shadow-[0_0_40px_rgba(var(--primary-rgb),0.15)] transition-all duration-500 group flex flex-col relative">
                
                {/* تأثير اللمعان العلوي عند المرور */}
                <div className="absolute top-0 right-0 w-full h-1 bg-gradient-to-r from-primary/50 to-primary opacity-0 group-hover:opacity-100 transition-opacity z-20" />
                
                <Link href={`/academy/store/${course.id}`} className="block relative h-56 overflow-hidden bg-background/50 border-b border-white/5">
                  {course.thumbnail_url ? (
                    <img 
                      src={course.thumbnail_url} 
                      alt={course.title} 
                      className="absolute inset-0 w-full h-full object-cover mix-blend-overlay opacity-80 transition-transform duration-700 group-hover:scale-110 group-hover:opacity-100" 
                      onError={e => { e.currentTarget.style.display = 'none'; e.currentTarget.parentElement?.classList.add('fallback'); }} 
                    />
                  ) : null}
                  
                  {/* شيلد الطوارئ (Fallback) إذا لم توجد صورة */}
                  <div className="fallback-shield absolute inset-0 hidden items-center justify-center bg-gradient-to-br from-background/50 to-card/50 group-[.fallback]:flex z-10">
                    <Shield className="w-20 h-20 text-primary/20 group-hover:scale-110 transition-transform duration-500" />
                  </div>
                  
                  {/* 🟢 شارة مجاني */}
                  {(course.is_free || course.price_mrusdt === 0) && (
                    <div className="absolute top-4 right-4 z-30 bg-emerald-500 text-white text-xs font-black px-4 py-1.5 rounded-full shadow-[0_0_15px_rgba(16,185,129,0.4)]">
                      مجاني بالكامل
                    </div>
                  )}
                </Link>
                
                <CardContent className="p-8 flex flex-col flex-1 relative z-20">
                  <h3 className="text-2xl font-black mb-3 line-clamp-2 text-foreground group-hover:text-primary transition-colors leading-tight">
                    {course.title}
                  </h3>
                  <p className="text-muted-foreground text-sm font-medium line-clamp-2 mb-8 flex-1">
                    {course.description}
                  </p>
                  
                  <div className="mt-auto pt-6 border-t border-border/50">
                    {/* 🟢 المكون الذكي الذي يحدد الحالة بناءً على التنزيلات */}
                    <CourseActionButton course={course} />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}