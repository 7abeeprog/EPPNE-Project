// hooks/auth/useAuth.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AuthService } from "@/services/auth.service";
import { useAuthStore } from "@/store/auth-store";
import { toast } from "sonner";
import type {
  LoginRequest,
  LoginResponse,
  RefreshTokenResponse,
  RevokeAllSessionsResponse,
  SessionInfo,
  RegisterRequest,
  RegisterResponse,
} from "@/types/auth";

// ==========================================
// 1. تسجيل الدخول ✅ (السطر 32)
// ==========================================
export const useLogin = () => {
  const queryClient = useQueryClient();
  const { setAuth, setAccessToken } = useAuthStore();

  return useMutation<LoginResponse, Error, LoginRequest>({
    mutationFn: (payload: LoginRequest) => AuthService.login(payload),
    onSuccess: (data: LoginResponse) => {
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      localStorage.setItem("user", JSON.stringify(data.user));

      // ✅ السطر 32: تمرير data.user مباشرة مع as any
      setAuth(data.user as any, data.access_token, data.refresh_token);
      setAccessToken(data.access_token);
      queryClient.setQueryData(["auth", "user"], data.user);

      const username = data.user?.username || "مستخدم";
      toast.success(`مرحباً ${username}! 🚀`);
    },
    onError: (error: any) => {
      toast.error(error.message || "فشل تسجيل الدخول");
    },
  });
};

// ==========================================
// 2. تسجيل مستخدم جديد
// ==========================================
export const useRegister = () => {
  return useMutation<RegisterResponse, Error, RegisterRequest>({
    mutationFn: (payload: RegisterRequest) => AuthService.register(payload),
    onSuccess: (data: RegisterResponse) => {
      const username = (data as any)?.username || "مستخدم";
      toast.success(`تم إنشاء الحساب بنجاح! مرحباً ${username} 🎉`);
    },
    onError: (error: any) => {
      toast.error(error.message || "فشل إنشاء الحساب");
    },
  });
};

// ==========================================
// 3. تجديد Access Token
// ==========================================
export const useRefreshToken = () => {
  const { refreshToken, setAccessToken, clearAuth } = useAuthStore();

  return useMutation<RefreshTokenResponse, Error>({
    mutationFn: async () => {
      if (!refreshToken) throw new Error("لا يوجد Refresh Token");
      return AuthService.refreshToken(refreshToken);
    },
    onSuccess: (data: RefreshTokenResponse) => {
      localStorage.setItem("access_token", data.access_token);
      setAccessToken(data.access_token);
    },
    onError: () => {
      clearAuth();
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    },
  });
};

// ==========================================
// 4. تسجيل الخروج
// ==========================================
export const useLogout = () => {
  const queryClient = useQueryClient();
  const { refreshToken, clearAuth } = useAuthStore();

  return useMutation({
    mutationFn: async () => {
      if (!refreshToken) return;
      await AuthService.logout(refreshToken);
    },
    onSuccess: () => {
      clearAuth();
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
      queryClient.clear();
      toast.success("تم تسجيل الخروج بنجاح");
      window.location.href = "/login";
    },
    onError: (error: any) => {
      clearAuth();
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
      toast.error(error.message || "حدث خطأ أثناء تسجيل الخروج");
    },
  });
};

// ==========================================
// 5. إبطال جميع الجلسات
// ==========================================
export const useRevokeAllSessions = () => {
  const queryClient = useQueryClient();

  return useMutation<RevokeAllSessionsResponse, Error>({
    mutationFn: () => AuthService.revokeAllSessions(),
    onSuccess: (data: RevokeAllSessionsResponse) => {
      toast.success(data.message || `تم إبطال ${data.revoked_count} جلسة`);
      queryClient.invalidateQueries({ queryKey: ["auth", "sessions"] });
    },
    onError: (error: any) => {
      toast.error(error.message || "فشل إبطال الجلسات");
    },
  });
};

// ==========================================
// 6. جلب الجلسات النشطة
// ==========================================
export const useActiveSessions = (skip: number = 0, limit: number = 20) => {
  return useQuery<SessionInfo[], Error>({
    queryKey: ["auth", "sessions", skip, limit],
    queryFn: () => AuthService.getActiveSessions(skip, limit),
    staleTime: 2 * 60 * 1000,
    enabled: true,
  });
};

// ==========================================
// 7. جلب بيانات المستخدم الحالي
// ==========================================
export const useCurrentUser = () => {
  const { user } = useAuthStore();
  return user;
};