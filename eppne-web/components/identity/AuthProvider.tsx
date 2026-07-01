// components/identity/AuthProvider.tsx
"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/store/auth-store";
import { IdentityService } from "@/services/identity.service";
import { useRouter, usePathname } from "next/navigation";
import { toast } from "sonner";

interface AuthProviderProps {
  children: React.ReactNode;
}

// ✅ المسارات العامة (لا تتطلب مصادقة)
const PUBLIC_PATHS = [
  "/login",
  "/register",
  "/forgot-password",
  "/verify-email",
];

export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { setAuth, clearAuth, setLoading, setInitialized, isAuthenticated, user } =
    useAuthStore();
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    if (!isMounted) return;

    const initializeAuth = async () => {
      try {
        setLoading(true);

        // ✅ محاولة جلب الملف الشخصي (يتم إرسال التوكنات تلقائياً عبر Cookies)
        const profile = await IdentityService.getProfile();

        if (profile && profile.id) {
          setAuth(profile);
        } else {
          clearAuth();
          // ✅ إذا كان المسار محمياً، إعادة التوجيه إلى تسجيل الدخول
          if (!PUBLIC_PATHS.includes(pathname || "")) {
            router.push("/login");
          }
        }
      } catch (error) {
        // ❌ فشل جلب الملف الشخصي → غير مصادق
        clearAuth();
        if (!PUBLIC_PATHS.includes(pathname || "")) {
          router.push("/login");
        }
      } finally {
        setLoading(false);
        setInitialized(true);
      }
    };

    initializeAuth();
  }, [isMounted]);

  // ✅ عرض حالة التحميل أثناء التهيئة
  if (!isMounted || !useAuthStore.getState().isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 border-4 border-primary/30 border-t-primary rounded-full animate-spin" />
          <p className="text-muted-foreground font-medium">جاري تهيئة الجلسة...</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}