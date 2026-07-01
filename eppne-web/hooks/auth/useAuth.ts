// hooks/auth/useAuth.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AuthService } from "@/services/auth.service";
import {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  RefreshTokenResponse,
  RevokeAllSessionsResponse,
  SessionInfo,
} from "@/types/auth";
import { useAuthStore } from "@/store/auth-store";
import { toast } from "sonner";

// ==========================================
// 1. تسجيل الدخول
// ==========================================
export const useLogin = () => {
  const queryClient = useQueryClient();
  const { setAuth, setAccessToken } = useAuthStore();

  return useMutation({
    mutationFn: (payload: LoginRequest) => AuthService.login(payload),
    onSuccess: (data: LoginResponse) => {
      setAuth(data.user, data.access_token);
      queryClient.setQueryData(["auth", "user"], data.user);
      toast.success(`مرحباً ${data.user.username}! 🚀`);
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
  return useMutation({
    mutationFn: (payload: RegisterRequest) => AuthService.register(payload),
    onSuccess: (data: RegisterResponse) => {
      toast.success(data.message || "تم إنشاء الحساب بنجاح! 🎉");
    },
    onError: (error: any) => {
      toast.error(error.message || "فشل إنشاء الحساب");
    },
  });
};

// ==========================================
// 3. تجديد Access Token (يعتمد على httpOnly Cookie)
// ==========================================
export const useRefreshToken = () => {
  const { setAccessToken, clearAuth } = useAuthStore();

  return useMutation({
    mutationFn: () => AuthService.refreshToken(),
    onSuccess: (data: RefreshTokenResponse) => {
      setAccessToken(data.access_token);
    },
    onError: () => {
      clearAuth();
      window.location.href = "/login";
    },
  });
};

// ==========================================
// 4. تسجيل الخروج (يعتمد على httpOnly Cookie)
// ==========================================
export const useLogout = () => {
  const queryClient = useQueryClient();
  const { clearAuth } = useAuthStore();

  return useMutation({
    mutationFn: () => AuthService.logout(),
    onSuccess: () => {
      clearAuth();
      queryClient.clear();
      toast.success("تم تسجيل الخروج بنجاح");
      window.location.href = "/login";
    },
    onError: (error: any) => {
      clearAuth();
      toast.error(error.message || "حدث خطأ أثناء تسجيل الخروج");
    },
  });
};

// ==========================================
// 5. إبطال جميع الجلسات
// ==========================================
export const useRevokeAllSessions = () => {
  const queryClient = useQueryClient();

  return useMutation({
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
  return useQuery({
    queryKey: ["auth", "sessions", skip, limit],
    queryFn: () => AuthService.getActiveSessions(skip, limit),
    staleTime: 2 * 60 * 1000,
    enabled: true,
  });
};

// ==========================================
// 7. جلب بيانات المستخدم الحالي (من Cache)
// ==========================================
export const useCurrentUser = () => {
  const { user } = useAuthStore();
  return user;
};