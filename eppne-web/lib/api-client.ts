// lib/api-client.ts
import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosError } from "axios";
import { toast } from "sonner";
import { useAuthStore } from "@/store/auth-store";

// 🟢 إعدادات الاتصال
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const MAX_RETRIES = 2;
const RETRY_DELAY = 1000;

// 🔥 نظام إدارة طلبات الـ Refresh (منع التضارب)
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (reason?: any) => void;
  config: InternalAxiosRequestConfig;
}> = [];

const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      if (prom.config.headers) {
        prom.config.headers.Authorization = `Bearer ${token}`;
      }
      prom.resolve(apiClient(prom.config));
    }
  });
  failedQueue = [];
};

// ✅ إنشاء عميل Axios
export const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
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
    // 1. إضافة الـ Access Token من الـ Store
    const { accessToken } = useAuthStore.getState();
    if (accessToken && config.headers) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }

    // 2. إضافة CSRF Token كطبقة حماية إضافية
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
    // معالجة انقطاع الشبكة
    if (!error.response) {
      toast.error("خطأ في الاتصال بالخادم. تحقق من اتصالك بالإنترنت.");
      return Promise.reject(error);
    }

    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    const status = error.response.status;

    // 1. معالجة 401 وتجديد التوكن
    if (status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject, config: originalRequest });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const response = await axios.post(
          `${BASE_URL}/auth/refresh`,
          {},
          { withCredentials: true }
        );

        const newAccessToken = response.data.access_token;
        useAuthStore.getState().setAccessToken(newAccessToken);

        processQueue(null, newAccessToken);
        
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        }
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError as Error, null);
        useAuthStore.getState().clearAuth();
        window.location.href = "/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // 2. معالجة الأخطاء العامة
    if (status === 429) toast.error("تم تجاوز حد الطلبات. يرجى الانتظار.");
    if (status === 403) toast.error("ليس لديك صلاحية للقيام بهذا الإجراء.");
    if (status >= 500) toast.error("حدث خطأ في الخادم. يرجى المحاولة لاحقاً.");

    // 3. منطق إعادة المحاولة التلقائية (Auto-Retries) للأخطاء العابرة
    const retries = (originalRequest as any).__retryCount || 0;
    if (retries < MAX_RETRIES && [408, 500, 502, 503, 504].includes(status)) {
      (originalRequest as any).__retryCount = retries + 1;
      await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY * (retries + 1)));
      return apiClient(originalRequest);
    }

    return Promise.reject(error);
  }
);