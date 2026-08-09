// services/auth.service.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";

type RevokeAllSessionsResponse = components['schemas']['RevokeAllSessionsResponse'];
type SessionInfoResponse = components['schemas']['SessionInfoResponse'];
type UserCreate = components['schemas']['UserCreate'];
type UserResponse = components['schemas']['UserResponse'];
type UserUpdate = components['schemas']['UserUpdate'];

// ملاحظة: مخطط LoginResponse المولَّد آليًا في api-types.ts يعكس شكل استجابة
// auth القديم (refresh_token في الجسم، إلخ)، وليس شكل استجابة identity الفعلي
// (لا response_model على /identity/login) — لذلك نوع محلي دقيق بدلاً منه.
interface IdentityLoginResponse {
  access_token: string;
  token_type: string;
  message: string;
  user_id: number;
  user: UserResponse;
}

export const AuthService = {
  // ==========================================
  // 1. تسجيل الدخول
  // ==========================================
  login: async (data: any): Promise<IdentityLoginResponse> => {
    try {
      // الباك اند يتوقع username_or_email
      const payload = {
        username_or_email: data.username || data.username_or_email || data.email,
        password: data.password,
      };
      const { data: result } = await apiClient.post<IdentityLoginResponse>("/identity/login", payload);
      return result;
    } catch (error) {
      // 401 هنا يعني بيانات دخول خاطئة — ليس جلسة منتهية، فلا توجيه قسري
      throw handleError(error, "فشل تسجيل الدخول", { silent401: true });
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
  refreshToken: async (): Promise<{ message: string }> => {
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
  logout: async (): Promise<void> => {
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
  getMe: async (): Promise<UserResponse> => {
    try {
      const { data } = await apiClient.get<UserResponse>("/identity/me");
      return data;
    } catch (error) {
      // 401 هنا يعني ببساطة "زائر غير مسجَّل دخول" (يُستدعى عند كل تحميل صفحة
      // عبر AuthProvider/useMe) — ليس جلسة منتهية فعليًا، فلا توجيه قسري
      throw handleError(error, "فشل جلب الملف الشخصي", { silent401: true });
    }
  },

  // ==========================================
  // 8. تحديث الملف الشخصي
  // ==========================================
  updateProfile: async (data: UserUpdate): Promise<UserResponse> => {
    try {
      const { data: result } = await apiClient.put<UserResponse>("/identity/me", data);
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث الملف الشخصي");
    }
  },

  // ==========================================
  // 9. تغيير كلمة المرور
  // ==========================================
  changePassword: async (data: { old_password: string; new_password: string }): Promise<{ message: string }> => {
    try {
      const { data: result } = await apiClient.put("/identity/me/password", data);
      return result;
    } catch (error) {
      throw handleError(error, "فشل تغيير كلمة المرور");
    }
  },
};