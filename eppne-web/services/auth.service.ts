// services/auth.service.ts
import { apiClient } from "@/lib/api-client";
import {
  LoginRequest,
  LoginResponse,
  RefreshTokenResponse,
  RegisterRequest,
  RegisterResponse,
  RevokeAllSessionsResponse,
  SessionInfo,
} from "@/types/auth";
import { handleError } from "@/lib/error-handler";

export const AuthService = {
  // ==========================================
  // 1. تسجيل الدخول
  // ==========================================
  login: async (payload: LoginRequest): Promise<LoginResponse> => {
    try {
      const { data } = await apiClient.post("/auth/login", payload);
      return data;
    } catch (error) {
      throw handleError(error, "فشل تسجيل الدخول");
    }
  },

  // ==========================================
  // 2. تسجيل مستخدم جديد
  // ==========================================
  register: async (payload: RegisterRequest): Promise<RegisterResponse> => {
    try {
      const { data } = await apiClient.post("/auth/register", payload);
      return data;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الحساب");
    }
  },

  // ==========================================
  // 3. تجديد Access Token (يعتمد على httpOnly Cookie)
  // ==========================================
  refreshToken: async (): Promise<RefreshTokenResponse> => {
    try {
      const { data } = await apiClient.post("/auth/refresh");
      return data;
    } catch (error) {
      throw handleError(error, "فشل تجديد الجلسة");
    }
  },

  // ==========================================
  // 4. تسجيل الخروج (يعتمد على httpOnly Cookie)
  // ==========================================
  logout: async (): Promise<void> => {
    try {
      await apiClient.post("/auth/logout");
    } catch (error) {
      throw handleError(error, "فشل تسجيل الخروج");
    }
  },

  // ==========================================
  // 5. إبطال جميع الجلسات
  // ==========================================
  revokeAllSessions: async (): Promise<RevokeAllSessionsResponse> => {
    try {
      const { data } = await apiClient.post("/auth/revoke-all");
      return data;
    } catch (error) {
      throw handleError(error, "فشل إبطال الجلسات");
    }
  },

  // ==========================================
  // 6. جلب الجلسات النشطة
  // ==========================================
  getActiveSessions: async (skip: number = 0, limit: number = 20): Promise<SessionInfo[]> => {
    try {
      const { data } = await apiClient.get("/auth/sessions", {
        params: { skip, limit },
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الجلسات النشطة");
    }
  },
};