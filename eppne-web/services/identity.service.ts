// services/identity.service.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";

type UserCreate = components['schemas']['UserCreate'];
type UserResponse = components['schemas']['UserResponse'];
type UserUpdate = components['schemas']['UserUpdate'];

export const IdentityService = {
  /**
   * تسجيل مستخدم جديد.
   * POST /identity/identity/register
   */
  register: async (data: UserCreate): Promise<UserResponse> => {
    try {
      const { data: result } = await apiClient.post<UserResponse>("/identity/identity/register", data);
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الحساب");
    }
  },

  /**
   * تسجيل الدخول باستخدام OAuth2 form data.
   * POST /identity/identity/login
   * يتم تعيين email كـ username لتوافق FastAPI.
   */
  login: async (email: string, password: string): Promise<any> => {
    try {
      const params = new URLSearchParams();
      params.append("username", email);
      params.append("password", password);
      const { data } = await apiClient.post("/identity/identity/login", params.toString(), {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل تسجيل الدخول");
    }
  },

  /**
   * جلب الملف الشخصي للمستخدم الحالي.
   * GET /identity/identity/me
   */
  getMe: async (): Promise<UserResponse> => {
    try {
      const { data } = await apiClient.get<UserResponse>("/identity/identity/me", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الملف الشخصي");
    }
  },

  /**
   * تحديث الملف الشخصي للمستخدم الحالي.
   * PUT /identity/identity/me
   */
  updateMe: async (data: UserUpdate): Promise<UserResponse> => {
    try {
      const { data: result } = await apiClient.put<UserResponse>("/identity/identity/me", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث الملف الشخصي");
    }
  },

  /**
   * تسجيل الخروج (إبطال الجلسة الحالية).
   * POST /identity/identity/logout
   */
  logout: async (): Promise<void> => {
    try {
      await apiClient.post("/identity/identity/logout", undefined, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل تسجيل الخروج");
    }
  },

  /**
   * تجديد رمز الوصول (Access Token).
   * POST /identity/identity/refresh
   */
  refresh: async (): Promise<any> => {
    try {
      const { data } = await apiClient.post("/identity/identity/refresh", undefined, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل تجديد الجلسة");
    }
  },

  /**
   * إبطال جميع الجلسات النشطة.
   * POST /identity/identity/revoke-all
   */
  revokeAll: async (): Promise<void> => {
    try {
      await apiClient.post("/identity/identity/revoke-all", undefined, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل إبطال الجلسات");
    }
  },
};