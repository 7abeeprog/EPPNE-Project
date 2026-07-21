// app/(dashboard)/academy/layout.tsx
"use client";

import { Suspense } from "react";
import { TenantProvider } from "@/components/academy/tenant-provider";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorBoundary } from "@/components/shared/error-boundary";

// ==========================================
// 1. مكون الاحتياطي (Fallback) أثناء التحميل
// ==========================================

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

// ==========================================
// 2. مكون عرض الخطأ الودي (عند فشل التحميل)
// ==========================================

function AcademyErrorFallback({ error, reset }: { error: Error; reset: () => void }) {
  // استخراج رسالة الخطأ
  const errorMessage = error.message || "حدث خطأ غير متوقع";

  return (
    <div className="w-full h-full min-h-screen flex flex-col items-center justify-center bg-destructive/5 backdrop-blur-sm p-6 text-center">
      <div className="p-4 bg-destructive/10 rounded-full border border-destructive/20 mb-4">
        <span className="text-4xl">📚</span>
      </div>
      <h2 className="text-2xl font-bold text-destructive">عذراً، الأكاديمية غير متاحة حالياً</h2>
      <p className="text-muted-foreground max-w-md mt-2">
        {errorMessage}
      </p>
      <p className="text-sm text-muted-foreground/60 max-w-md mt-1">
        فريقنا يعمل على حل المشكلة. يرجى المحاولة مرة أخرى بعد قليل.
      </p>
      <div className="flex flex-wrap gap-3 mt-6">
        <button
          onClick={reset}
          className="px-6 py-2 bg-primary text-primary-foreground rounded-xl font-bold hover:bg-primary/90 transition-colors shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)]"
        >
          إعادة المحاولة
        </button>
        <button
          onClick={() => window.location.href = "/dashboard"}
          className="px-6 py-2 bg-muted text-muted-foreground rounded-xl font-bold hover:bg-muted/80 transition-colors"
        >
          العودة للوحة الرئيسية
        </button>
      </div>
    </div>
  );
}

// ==========================================
// 3. التخطيط الرئيسي للأكاديمية
// ==========================================

export default function AcademyLayout({ children }: { children: React.ReactNode }) {
  return (
    // ✅ ErrorBoundary ذكي يلتقط أي خطأ في الأكاديمية
    <ErrorBoundary
      componentName="الأكاديمية السيادية"
      fallback={AcademyErrorFallback}
      autoRetry={true}
      retryDelay={5000}
      onError={(error, errorInfo) => {
        // ✅ تسجيل الخطأ في الكونسول مع معلومات إضافية
        console.error("🚨 خطأ في الأكاديمية السيادية:", {
          error: error.message,
          stack: error.stack,
          componentStack: errorInfo.componentStack,
          timestamp: new Date().toISOString(),
        });

        // ✅ هنا يمكن إضافة إرسال إشعار إلى فريق الدعم
        // مثال: إرسال إلى Slack أو بريد إلكتروني
        // await fetch('/api/errors/report', { ... });
      }}
    >
      <Suspense fallback={<AcademyLayoutFallback />}>
        <TenantProvider>
          <div
            className="w-full h-full relative min-h-screen"
            // ✅ تحسين الأداء: تسريع GPU وتقليل إعادة الرسم
            style={{ willChange: "transform", transform: "translateZ(0)" }}
          >
            {/* ✅ خلفية سيادية أحادية الطبقة (تقليل الحمل على GPU) */}
            <div
              className="fixed inset-0 -z-50 pointer-events-none transition-colors duration-700"
              style={{
                background: `
                  radial-gradient(ellipse at 70% 20%, rgba(var(--primary-rgb), 0.12) 0%, transparent 60%),
                  radial-gradient(ellipse at 30% 80%, rgba(var(--primary-rgb), 0.08) 0%, transparent 60%)
                `,
              }}
            />

            {/* ✅ المحتوى الرئيسي */}
            <div className="relative z-10 w-full h-full">
              {children}
            </div>
          </div>
        </TenantProvider>
      </Suspense>
    </ErrorBoundary>
  );
}