// providers/AuthProvider.tsx
"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth-store";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { setAuth, setLoading, setInitialized, isInitialized, isLoading, isAuthenticated } = useAuthStore();
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // ✅ تهيئة المصادقة
  useEffect(() => {
    if (!isMounted) return;

    const initAuth = async () => {
      try {
        setLoading(true);
        const storedToken = localStorage.getItem("access_token");
        const storedUser = localStorage.getItem("user");

        if (storedToken && storedUser) {
          try {
            const user = JSON.parse(storedUser);
            setAuth(user, storedToken, localStorage.getItem("refresh_token") || "");
          } catch {
            setAuth(null as any, "", "");
          }
        } else {
          setAuth(null as any, "", "");
        }
      } catch (error) {
        console.error("Auth initialization error:", error);
        setAuth(null as any, "", "");
      } finally {
        setLoading(false);
        setInitialized(true);
      }
    };

    initAuth();
  }, [isMounted, setAuth, setLoading, setInitialized]);

  // ✅ التوجيه: يتم تنفيذه في useEffect وليس أثناء الرسم
  useEffect(() => {
    // انتظر حتى يكتمل التهيئة
    if (!isInitialized || isLoading) return;

    const isAuthPage = pathname === "/login" || pathname === "/register";

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
  const isAuthPage = pathname === "/login" || pathname === "/register";
  if (!isAuthenticated && !isAuthPage) {
    return null;
  }

  return <>{children}</>;
}