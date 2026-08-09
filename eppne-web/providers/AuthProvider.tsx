// providers/AuthProvider.tsx
"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth-store";
import { useMe } from "@/hooks/identity/useAuth";

const PUBLIC_PATHS = ["/login", "/register"];

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading, isInitialized, setLoading, setInitialized } = useAuthStore();
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // ✅ التحقق الفعلي من الجلسة عبر GET /identity/me (الكوكي HttpOnly)
  // بدل الوثوق بـ localStorage — هذا يُصلح الثغرة الأمنية المسجَّلة في PROGRESS_LOG.md
  const { isFetched } = useMe();

  useEffect(() => {
    if (!isMounted) return;
    setLoading(!isFetched);
    if (isFetched) setInitialized(true);
  }, [isMounted, isFetched, setLoading, setInitialized]);

  // ✅ التوجيه: يتم تنفيذه في useEffect وليس أثناء الرسم
  useEffect(() => {
    if (!isInitialized || isLoading) return;

    const isAuthPage = PUBLIC_PATHS.includes(pathname || "");

    if (!isAuthenticated && !isAuthPage) {
      router.push("/login");
    }

    if (isAuthenticated && isAuthPage) {
      router.push("/dashboard");
    }
  }, [isAuthenticated, isInitialized, isLoading, pathname, router]);

  // ✅ عرض حالة التحميل
  if (!isMounted || !isInitialized || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground text-lg">جاري تهيئة المنصة السيادية...</p>
        </div>
      </div>
    );
  }

  // ✅ منع رسم المحتوى في حالة عدم المصادقة (سيتم التوجيه عبر useEffect)
  const isAuthPage = PUBLIC_PATHS.includes(pathname || "");
  if (!isAuthenticated && !isAuthPage) {
    return null;
  }

  return <>{children}</>;
}
