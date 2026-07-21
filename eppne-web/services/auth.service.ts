// services/auth.service.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";

type LoginRequest = components['schemas']['LoginRequest'];
type LoginResponse = components['schemas']['LoginResponse'];
type RevokeAllSessionsResponse = components['schemas']['RevokeAllSessionsResponse'];
type SessionInfoResponse = components['schemas']['SessionInfoResponse'];
type UserCreate = components['schemas']['UserCreate'];
type UserResponse = components['schemas']['UserResponse'];

export const AuthService = {
  // ==========================================
  // 1. تسجيل الدخول
  // ==========================================
  login: async (data: any): Promise<LoginResponse> => {
    try {
      // الباك اند يتوقع username_or_email
      const payload = {
        username_or_email: data.username || data.username_or_email || data.email,
        password: data.password,
      };
      const { data: result } = await apiClient.post<LoginResponse>("/identity/login", payload);
      return result;
    } catch (error) {
      throw handleError(error, "فشل تسجيل الدخول");
    }
  },

  // ==========================================
  // 2. تسجيل مستخدم جديد
  // ==========================================
  register: async (data: UserCreate): Promise<UserResponse> => {
    try {
      const { data: result } = await apiClient.post<UserResponse>("/identity/register", data);
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الحساب");
    }
  },

  // ==========================================
  // 3. تجديد Access Token
  // ==========================================
  refreshToken: async (refreshToken?: string): Promise<any> => {
    try {
      // الكوكيز يتم إرسالها تلقائياً بفضل withCredentials في apiClient
      const { data: result } = await apiClient.post("/identity/refresh");
      return result;
    } catch (error) {
      throw handleError(error, "فشل تجديد الجلسة");
    }
  },

  // ==========================================
  // 4. تسجيل الخروج
  // ==========================================
  logout: async (refreshToken?: string): Promise<void> => {
    try {
      await apiClient.post("/identity/logout");
    } catch (error) {
      throw handleError(error, "فشل تسجيل الخروج");
    }
  },

  // ==========================================
  // 5. إبطال جميع الجلسات
  // ==========================================
  revokeAllSessions: async (): Promise<RevokeAllSessionsResponse> => {
    try {
      const { data: result } = await apiClient.post<RevokeAllSessionsResponse>("/identity/revoke-all");
      return result;
    } catch (error) {
      throw handleError(error, "فشل إبطال الجلسات");
    }
  },

  // ==========================================
  // 6. جلب الجلسات النشطة
  // ==========================================
  getActiveSessions: async (skip: number = 0, limit: number = 20): Promise<SessionInfoResponse[]> => {
    try {
      const { data } = await apiClient.get<SessionInfoResponse[]>("/identity/sessions", {
        params: { skip, limit },
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الجلسات النشطة");
    }
  },

  // ==========================================
  // 7. جلب الملف الشخصي للمستخدم الحالي
  // ==========================================
  getProfile: async (): Promise<UserResponse> => {
    try {
      const { data } = await apiClient.get<UserResponse>("/identity/me");
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الملف الشخصي");
    }
  },
};