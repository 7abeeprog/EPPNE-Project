"use client";

import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { useMyEnrollments, useEnrollMutation } from "@/hooks/academy-queries";
import { Course } from "@/types/academy";
import { Button } from "@/components/ui/button";
import { Play, ShoppingCart, CheckCircle, ArrowLeft, Loader2 } from "lucide-react";

interface CourseActionButtonProps {
  course: Course;
}

export function CourseActionButton({ course }: CourseActionButtonProps) {
  const router = useRouter();

  // ✅ التصحيح الجوهري: استخدام pages.flatMap للوصول إلى البيانات من InfiniteData
  const { data: enrollmentsData, isLoading: isEnrollmentsLoading } = useMyEnrollments(0, 100);
  const myEnrollments = enrollmentsData?.pages.flatMap((page) => page.data) || [];

  const enrollment = useMemo(
    () => myEnrollments.find((e) => e.course_id === course.id),
    [myEnrollments, course.id]
  );

  const enrollMutation = useEnrollMutation();

  const handleEnroll = () => {
    if (!course.id) return;
    enrollMutation.mutate(
      {
        courseId: course.id,
        payload: {
          payment_method: course.is_free || course.price_mrusdt === 0 ? "FREE" : "WALLET",
        },
      },
      {
        onSuccess: () => {
          router.push(`/academy/classroom/${course.id}`);
        },
        onError: (error: any) => {
          console.error("Enrollment error:", error);
        },
      }
    );
  };

  if (isEnrollmentsLoading) {
    return (
      <Button disabled className="w-full bg-muted/30 backdrop-blur-sm font-black text-lg h-14 rounded-xl border border-white/10">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        جاري التحقق من الاشتراك...
      </Button>
    );
  }

  if (enrollment) {
    const progress = enrollment.progress_percentage || 0;

    if (progress === 0) {
      return (
        <Button
          onClick={() => router.push(`/academy/classroom/${course.id}`)}
          className="w-full bg-emerald-600 hover:bg-emerald-500 font-black text-lg h-14 rounded-xl shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:shadow-[0_0_30px_rgba(16,185,129,0.5)] border border-emerald-500/50 transition-all hover:-translate-y-1"
        >
          <Play className="mr-2 h-5 w-5" /> ابدأ التعلم الآن
        </Button>
      );
    }

    if (progress === 100 || enrollment.is_completed) {
      return (
        <Button
          onClick={() => router.push(`/academy/classroom/${course.id}`)}
          variant="outline"
          className="w-full bg-background/40 backdrop-blur-md border border-emerald-500/40 text-emerald-500 hover:bg-emerald-500 hover:text-white font-black text-lg h-14 rounded-xl shadow-[0_0_15px_rgba(16,185,129,0.15)] transition-all hover:-translate-y-1"
        >
          <CheckCircle className="mr-2 h-5 w-5" /> مكتمل (مراجعة المحتوى)
        </Button>
      );
    }

    return (
      <Button
        onClick={() => router.push(`/academy/classroom/${course.id}`)}
        className="w-full bg-blue-600 hover:bg-blue-500 font-black text-lg h-14 rounded-xl relative overflow-hidden group shadow-[0_0_20px_rgba(37,99,235,0.3)] hover:shadow-[0_0_30px_rgba(37,99,235,0.5)] border border-blue-500/50 transition-all hover:-translate-y-1"
      >
        <div
          className="absolute left-0 top-0 bottom-0 bg-white/20 z-0 transition-all duration-1000"
          style={{ width: `${progress}%` }}
        />
        <span className="relative z-10 flex items-center justify-center w-full drop-shadow-md">
          الاستكمال ({Math.round(progress)}%) <ArrowLeft className="ml-2 h-5 w-5" />
        </span>
      </Button>
    );
  }

  const isFree = course.is_free || course.price_mrusdt === 0;

  return (
    <Button
      onClick={handleEnroll}
      disabled={enrollMutation.isPending}
      className={`w-full font-black text-lg h-14 rounded-xl border transition-all hover:-translate-y-1 ${
        isFree
          ? "bg-primary hover:bg-primary/90 border-primary/50 shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.5)]"
          : "bg-amber-500 hover:bg-amber-400 border-amber-500/50 shadow-[0_0_20px_rgba(245,158,11,0.3)] hover:shadow-[0_0_30px_rgba(245,158,11,0.5)] text-white"
      }`}
    >
      {enrollMutation.isPending ? (
        <Loader2 className="mr-2 h-6 w-6 animate-spin" />
      ) : isFree ? (
        <Play className="mr-2 h-6 w-6" />
      ) : (
        <ShoppingCart className="mr-2 h-6 w-6" />
      )}

      {enrollMutation.isPending
        ? "جاري التشفير..."
        : isFree
          ? "سجل مجاناً بدون محفظة"
          : `اشتري الآن (${Number(course.price_mrusdt).toLocaleString("en-US")} MR_USDT)`}
    </Button>
  );
}