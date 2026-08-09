// lib/error-handler.ts
import { AxiosError } from "axios";

/**
 * معالج الأخطاء المركزي (Centralized Error Handler)
 * يدعم:
 * - 401 Unauthorized → إعادة توجيه إلى تسجيل الدخول
 * - Network Errors → رسالة مفهومة للمستخدم
 * - 422 Validation → عرض تفاصيل الأخطاء
 */
export const handleError = (
  error: unknown,
  context: string,
  options?: { silent401?: boolean }
): Error => {
  // 1. خطأ الشبكة (انقطاع الإنترنت)
  if (error instanceof TypeError && error.message === "Failed to fetch") {
    console.error(`[${context}] Network Error:`, error);
    return new Error(
      "فشل الاتصال بالخادم. يرجى التحقق من اتصالك بالإنترنت والمحاولة مرة أخرى."
    );
  }

  // 2. خطأ من Axios
  const axiosError = error as AxiosError;

  if (axiosError.isAxiosError) {
    // تسجيل الخطأ التقني في الكونسول (وسيتم ربطه بـ Sentry لاحقاً)
    console.error(`[${context}] Axios Error:`, {
      status: axiosError.response?.status,
      data: axiosError.response?.data,
      url: axiosError.config?.url,
    });

    // حالة 401: انتهت صلاحية التوكن
    if (axiosError.response?.status === 401) {
      // بعض النداءات (تسجيل الدخول، التحقق من الجلسة عند الإقلاع) تتوقع 401
      // كحالة طبيعية (بيانات خاطئة / زائر غير مسجَّل دخول) وليس "جلسة منتهية"
      // — silent401 يمنع التوجيه القسري لـ /login الذي كان يسبب حلقة توجيه
      // على صفحة /login نفسها لأي زائر غير مسجَّل دخول.
      if (options?.silent401) {
        const detail = (axiosError.response?.data as any)?.detail;
        return new Error(typeof detail === "string" ? detail : "غير مصرَّح بالوصول.");
      }

      // محاولة تسجيل الخروج وتنظيف التخزين
      try {
        localStorage.removeItem("auth-storage");
        // إذا كان هناك متجر Zustand، يمكن استدعاؤه هنا
        // useAuthStore.getState().clearAuth();
      } catch (_) {}

      // إعادة التوجيه إلى صفحة تسجيل الدخول
      if (typeof window !== "undefined") {
        window.location.href = "/login?session=expired";
      }
      return new Error("انتهت صلاحية الجلسة. جاري إعادة التوجيه...");
    }

    // حالة 403: غير مصرح
    if (axiosError.response?.status === 403) {
      return new Error("ليس لديك صلاحية للوصول إلى هذه المورد.");
    }

    // حالة 404: غير موجود
    if (axiosError.response?.status === 404) {
      return new Error("المورد المطلوب غير موجود.");
    }

    // حالة 422: خطأ في التحقق من البيانات (معروض بالعربية من الباك إند)
    if (axiosError.response?.status === 422) {
      const detail = (axiosError.response?.data as any)?.detail;
      if (detail && typeof detail === "string") {
        return new Error(detail);
      }
      if (detail && Array.isArray(detail)) {
        const messages = detail.map((err: any) => err.msg || err.message).join(", ");
        return new Error(`خطأ في البيانات: ${messages}`);
      }
      return new Error("بيانات غير صالحة. يرجى التحقق من المدخلات.");
    }

    // حالة 500: خطأ داخلي في الخادم
    if (axiosError.response?.status === 500) {
      return new Error(
        "حدث خلل داخلي في النظام. يرجى المحاولة لاحقاً أو الاتصال بالدعم."
      );
    }

    // أي خطأ آخر من الباك إند مع رسالة
    const message = (axiosError.response?.data as any)?.message || axiosError.message;
    return new Error(message || "حدث خطأ غير متوقع في النظام.");
  }

  // 3. خطأ غير معروف
  console.error(`[${context}] Unknown Error:`, error);
  return new Error("حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.");
};