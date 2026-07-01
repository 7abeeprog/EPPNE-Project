// providers/AuthProvider.tsx
"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/store/auth-store";
import { IdentityService } from "@/services/identity.service";
import { Loader2 } from "lucide-react";

interface AuthProviderProps {
  children: React.ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { setAuth, clearAuth, isLoading, setLoading } = useAuthStore();
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    const initializeAuth = async () => {
      setLoading(true);
      try {
        // ✅ محاولة جلب بيانات المستخدم من الـ API
        const user = await IdentityService.getProfile();
        setAuth(user, ""); // التوكن مخزن في Cookies، لا نحتاج لتمريره
      } catch (error) {
        // ❌ فشل جلب البيانات -> المستخدم غير مسجل
        clearAuth();
      } finally {
        setLoading(false);
        setIsInitialized(true);
      }
    };

    initializeAuth();
  }, [setAuth, clearAuth, setLoading]);

  // ✅ عرض شاشة تحميل أثناء تهيئة المصادقة
  if (!isInitialized || isLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-background">
        <div className="relative">
          <div className="absolute inset-0 bg-primary/20 blur-[80px] rounded-full" />
          <Loader2 className="h-12 w-12 text-primary animate-spin relative z-10" />
        </div>
        <p className="text-muted-foreground mt-4 font-medium animate-pulse">
          جاري تهيئة المنصة السيادية...
        </p>
      </div>
    );
  }

  return <>{children}</>;
}