// services/identity.service.ts
import { apiClient } from "@/lib/api-client";
import {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  UserProfile,
  UpdateProfileRequest,
  ChangePasswordRequest,
  Session,
  Wallet,
} from "@/types/identity";
import { handleError } from "@/lib/error-handler";

export const IdentityService = {
  // ==========================================
  // 1. تسجيل الدخول
  // ==========================================
  login: async (payload: LoginRequest): Promise<LoginResponse> => {
    try {
      const { data } = await apiClient.post("/identity/login", payload);
      return data;
    } catch (error) {
      throw handleError(error, "فشل تسجيل الدخول");
    }
  },

  // ==========================================
  // 2. التسجيل (مع Idempotency Key في الهيدر)
  // ==========================================
  register: async (payload: RegisterRequest): Promise<RegisterResponse> => {
    try {
      const { data } = await apiClient.post("/identity/register", payload, {
        headers: {
          "X-Idempotency-Key": payload.idempotency_key,
        },
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الحساب");
    }
  },

  // ==========================================
  // 3. تسجيل الخروج
  // ==========================================
  logout: async (): Promise<void> => {
    try {
      await apiClient.post("/identity/logout");
    } catch (error) {
      throw handleError(error, "فشل تسجيل الخروج");
    }
  },

  // ==========================================
  // 4. تجديد التوكن
  // ==========================================
  refreshToken: async (): Promise<{ access_token: string }> => {
    try {
      const { data } = await apiClient.post("/identity/refresh");
      return data;
    } catch (error) {
      throw handleError(error, "فشل تجديد الجلسة");
    }
  },

  // ==========================================
  // 5. الملف الشخصي
  // ==========================================
  getProfile: async (): Promise<UserProfile> => {
    try {
      const { data } = await apiClient.get("/identity/me");
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الملف الشخصي");
    }
  },

  updateProfile: async (payload: UpdateProfileRequest): Promise<UserProfile> => {
    try {
      const { data } = await apiClient.put("/identity/me", payload);
      return data;
    } catch (error) {
      throw handleError(error, "فشل تحديث الملف الشخصي");
    }
  },

  // ==========================================
  // 6. تغيير كلمة المرور
  // ==========================================
  changePassword: async (payload: ChangePasswordRequest): Promise<void> => {
    try {
      await apiClient.post("/identity/change-password", payload);
    } catch (error) {
      throw handleError(error, "فشل تغيير كلمة المرور");
    }
  },

  // ==========================================
  // 7. الجلسات
  // ==========================================
  getSessions: async (skip: number = 0, limit: number = 20): Promise<Session[]> => {
    try {
      const { data } = await apiClient.get("/identity/sessions", {
        params: { skip, limit },
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الجلسات");
    }
  },

  revokeAllSessions: async (): Promise<{ message: string; revoked_count: number }> => {
    try {
      const { data } = await apiClient.post("/identity/revoke-all");
      return data;
    } catch (error) {
      throw handleError(error, "فشل إبطال الجلسات");
    }
  },

  // ==========================================
  // 8. المحفظة
  // ==========================================
  getWallet: async (): Promise<Wallet> => {
    try {
      const { data } = await apiClient.get("/identity/wallet");
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المحفظة");
    }
  },
};