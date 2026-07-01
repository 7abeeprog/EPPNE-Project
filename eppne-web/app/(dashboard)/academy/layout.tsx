// app/(dashboard)/academy/layout.tsx
"use client";

import { Suspense } from "react";
import { TenantProvider } from "@/components/academy/tenant-provider";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorBoundary } from "@/components/shared/error-boundary";

// 🔥 مكون احتياطي (Fallback) أثناء تحميل TenantProvider
function AcademyLayoutFallback() {
  return (
    <div className="w-full h-full min-h-screen flex items-center justify-center bg-background/50 backdrop-blur-sm">
      <div className="space-y-4 text-center">
        <Skeleton className="h-12 w-64 mx-auto bg-primary/10" />
        <Skeleton className="h-6 w-48 mx-auto bg-primary/5" />
        <div className="flex gap-4 justify-center">
          <Skeleton className="h-32 w-48 rounded-2xl bg-card/40" />
          <Skeleton className="h-32 w-48 rounded-2xl bg-card/40" />
          <Skeleton className="h-32 w-48 rounded-2xl bg-card/40" />
        </div>
      </div>
    </div>
  );
}

// 🔥 معالج الأخطاء (Error Boundary) لعرض رسالة ودية عند فشل التحميل
function AcademyErrorFallback({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="w-full h-full min-h-screen flex flex-col items-center justify-center bg-destructive/5 backdrop-blur-sm p-6 text-center">
      <div className="p-4 bg-destructive/10 rounded-full border border-destructive/20 mb-4">
        <span className="text-4xl">⚠️</span>
      </div>
      <h2 className="text-2xl font-bold text-destructive">فشل تحميل الأكاديمية</h2>
      <p className="text-muted-foreground max-w-md mt-2">
        {error.message || "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."}
      </p>
      <button
        onClick={reset}
        className="mt-4 px-6 py-2 bg-primary text-primary-foreground rounded-xl font-bold hover:bg-primary/90 transition-colors"
      >
        إعادة المحاولة
      </button>
    </div>
  );
}

export default function AcademyLayout({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary fallback={AcademyErrorFallback}>
      <Suspense fallback={<AcademyLayoutFallback />}>
        <TenantProvider>
          <div
            className="w-full h-full relative min-h-screen"
            // 🔥 تحسين الأداء: تفعيل تسريع GPU وتقليل إعادة الرسم
            style={{ willChange: "transform", transform: "translateZ(0)" }}
          >
            {/* 🟢 خلفية سيادية أحادية الطبقة (تقليل الحمل على GPU) */}
            <div
              className="fixed inset-0 -z-50 pointer-events-none transition-colors duration-700"
              style={{
                background: `
                  radial-gradient(ellipse at 70% 20%, rgba(var(--primary-rgb), 0.12) 0%, transparent 60%),
                  radial-gradient(ellipse at 30% 80%, rgba(var(--primary-rgb), 0.08) 0%, transparent 60%)
                `,
              }}
            />
            
            {/* 🟢 المحتوى الرئيسي */}
            <div className="relative z-10 w-full h-full">
              {children}
            </div>
          </div>
        </TenantProvider>
      </Suspense>
    </ErrorBoundary>
  );
}