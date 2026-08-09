// hooks/auth/useAuth.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AuthService } from "@/services/auth.service";
import { useAuthStore } from "@/store/auth-store";
import { toast } from "sonner";
import type {
  RevokeAllSessionsResponse,
  SessionInfo,
  RegisterRequest,
  RegisterResponse,
  User,
} from "@/types/auth";

const ME_QUERY_KEY = ["identity", "me"] as const;

// ==========================================
// 1. تسجيل الدخول (كوكيز HttpOnly فقط — لا localStorage)
// ==========================================
export const useLogin = () => {
  const queryClient = useQueryClient();
  const { setUser, setAccessToken } = useAuthStore();

  return useMutation<any, Error, { username?: string; username_or_email?: string; email?: string; password: string }>({
    mutationFn: (payload) => AuthService.login(payload),
    onSuccess: (data) => {
      setUser(data.user ?? null);
      // في الذاكرة فقط، لاستثناء WebSocket الوحيد (انظر ملاحظة store/auth-store.ts)
      if (data.access_token) setAccessToken(data.access_token);
      queryClient.setQueryData(ME_QUERY_KEY, data.user ?? null);

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
// 3. تسجيل الخروج
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
      // حتى لو فشل الاتصال بالخادم، نطرد المستخدم محليًا لحماية البيانات
      clearAuth();
      queryClient.clear();
      toast.error(error.message || "حدث خطأ أثناء تسجيل الخروج");
      window.location.href = "/login";
    },
  });
};

// ==========================================
// 4. إبطال جميع الجلسات
// ==========================================
export const useRevokeAllSessions = () => {
  const queryClient = useQueryClient();

  return useMutation<RevokeAllSessionsResponse, Error>({
    mutationFn: () => AuthService.revokeAllSessions(),
    onSuccess: (data: RevokeAllSessionsResponse) => {
      toast.success(data.message || `تم إبطال ${data.revoked_count} جلسة`);
      queryClient.invalidateQueries({ queryKey: ["identity", "sessions"] });
    },
    onError: (error: any) => {
      toast.error(error.message || "فشل إبطال الجلسات");
    },
  });
};

// ==========================================
// 5. جلب الجلسات النشطة
// ==========================================
export const useActiveSessions = (skip: number = 0, limit: number = 20) => {
  return useQuery<SessionInfo[], Error>({
    queryKey: ["identity", "sessions", skip, limit],
    queryFn: () => AuthService.getActiveSessions(skip, limit),
    staleTime: 2 * 60 * 1000,
  });
};

// ==========================================
// 6. تغيير كلمة المرور
// ==========================================
export const useChangePassword = () => {
  return useMutation<{ message: string }, Error, { old_password: string; new_password: string }>({
    mutationFn: (payload) => AuthService.changePassword(payload),
    onSuccess: (data) => {
      toast.success(data.message || "تم تغيير كلمة المرور بنجاح");
    },
    onError: (error: any) => {
      toast.error(error.message || "فشل تغيير كلمة المرور");
    },
  });
};

// ==========================================
// 7. التحقق الحقيقي من الجلسة عبر GET /identity/me
// (المصدر الوحيد للحقيقة — لا وثوق بأي حالة محلية قديمة)
// ==========================================
export const useMe = () => {
  const setUser = useAuthStore((state) => state.setUser);
  const clearAuth = useAuthStore((state) => state.clearAuth);

  return useQuery<User, Error>({
    queryKey: ME_QUERY_KEY,
    queryFn: async () => {
      try {
        const user = await AuthService.getMe();
        setUser(user);
        return user;
      } catch (error) {
        clearAuth();
        throw error;
      }
    },
    retry: false,
    staleTime: 60 * 1000,
  });
};

// ==========================================
// 8. جلب بيانات المستخدم الحالي (قيمة مباشرة وليس كائن الاستعلام)
// ==========================================
export const useCurrentUser = () => {
  const { data } = useMe();
  return data ?? null;
};

// ==========================================
// 9. تصدير مركّب يحل محل الاستيرادات المكسورة القديمة
// ==========================================
export const useAuth = () => {
  const loginMutation = useLogin();
  const logoutMutation = useLogout();
  const { data: user, isLoading: isFetchingMe } = useMe();
  const accessToken = useAuthStore((state) => state.accessToken);

  return {
    user: user ?? null,
    isFetchingMe,
    isLoading: isFetchingMe,
    login: loginMutation.mutateAsync,
    isLoggingIn: loginMutation.isPending,
    logout: logoutMutation.mutate,
    isLoggingOut: logoutMutation.isPending,
    // للاستخدام الحصري في مصافحة WebSocket (hooks/communications/useWebSocket.ts)
    token: accessToken,
  };
};
