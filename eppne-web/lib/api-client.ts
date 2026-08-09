// lib/api-client.ts
import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosError } from "axios";
import { toast } from "sonner";
import { useAuthStore } from "@/store/auth-store";

// 🟢 إعدادات الاتصال
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const MAX_RETRIES = 2;
const RETRY_DELAY = 1000;

// 🔥 نظام إدارة طلبات الـ Refresh (منع التضارب)
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (reason?: any) => void;
  config: InternalAxiosRequestConfig;
}> = [];

const processQueue = (error: Error | null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(apiClient(prom.config));
    }
  });
  failedQueue = [];
};

// ✅ إنشاء عميل Axios
export const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 120000, // ⏳ تم الزيادة إلى 120 ثانية لتجاوز بطء الباك اند المؤقت
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
});

// ==========================================
// 🛡️ Interceptor للطلب (Request)
// ==========================================
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const csrfToken = document.cookie
      .split("; ")
      .find((row) => row.startsWith("csrf_token="))
      ?.split("=")[1];

    if (csrfToken) {
      config.headers["X-CSRF-Token"] = csrfToken;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// ==========================================
// 🛡️ Interceptor للاستجابة (Response)
// ==========================================
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (!error.response) {
      // إذا حدث Timeout سيتم التقاطه هنا
      if (error.code === 'ECONNABORTED') {
        toast.error("تأخر الخادم في الرد. يرجى الانتظار...");
      } else {
        toast.error("خطأ في الاتصال بالخادم. تحقق من اتصالك بالإنترنت.");
      }
      return Promise.reject(error);
    }

    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    const status = error.response.status;

    // نقاط تحقق/تأسيس الجلسة: 401 هنا حالة طبيعية متوقعة (زائر غير مسجَّل
    // دخول، أو بيانات دخول خاطئة) وليس "جلسة منتهية" — لا يجب محاولة تجديد
    // التوكن ولا التوجيه القسري لـ /login (كان سيسبب حلقة توجيه على صفحة
    // /login نفسها لأي زائر غير مسجَّل، لأن AuthProvider يستدعي GET
    // /identity/me عند تحميل كل صفحة).
    const requestUrl = originalRequest.url || "";
    const requestMethod = (originalRequest.method || "get").toLowerCase();
    const isAuthBootstrapCall =
      (requestMethod === "get" && requestUrl.includes("/identity/me")) ||
      requestUrl.includes("/identity/login") ||
      requestUrl.includes("/identity/register") ||
      requestUrl.includes("/identity/refresh");

    if (status === 401 && !isAuthBootstrapCall && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject, config: originalRequest });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // الكوكيز HttpOnly تُرسَل تلقائيًا عبر withCredentials؛ لا حاجة لأي body أو header يدوي
        await axios.post(`${BASE_URL}/identity/refresh`, undefined, { withCredentials: true });

        processQueue(null);
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError as Error);
        useAuthStore.getState().clearAuth();
        window.location.href = "/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    if (status === 429) toast.error("تم تجاوز حد الطلبات. يرجى الانتظار.");
    if (status === 403) toast.error("ليس لديك صلاحية للقيام بهذا الإجراء.");
    if (status >= 500) toast.error("حدث خطأ في الخادم. يرجى المحاولة لاحقاً.");

    const retries = (originalRequest as any).__retryCount || 0;
    if (retries < MAX_RETRIES && [408, 500, 502, 503, 504].includes(status)) {
      (originalRequest as any).__retryCount = retries + 1;
      await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY * (retries + 1)));
      return apiClient(originalRequest);
    }

    return Promise.reject(error);
  }
);