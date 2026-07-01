import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";
import { toast } from "sonner";

export const useAuth = () => {
  const queryClient = useQueryClient();
  const { setUser, clearAuth } = useAuthStore();

  // 🟢 1. محرك تسجيل الدخول (Mutation)
  const loginMutation = useMutation({
    mutationFn: async ({ usernameOrEmail, password }: any) => {
      const response = await apiClient.post("/identity/login", {
        username_or_email: usernameOrEmail,
        password: password,
      });
      return response.data;
    },
    onSuccess: async () => {
      toast.success("تم تأكيد الهوية. جاري تشفير الاتصال...");
      // إجبار النظام على جلب بيانات المستخدم فوراً بعد النجاح
      await queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
    },
    onError: (error: any) => {
      console.error("Login failed:", error);
      toast.error(error.response?.data?.detail || "فشل تسجيل الدخول. تأكد من هويتك.");
    }
  });

  // 🟢 2. محرك تسجيل الخروج (Mutation)
  const logoutMutation = useMutation({
    mutationFn: async () => await apiClient.post("/identity/logout"),
    onSuccess: () => {
      clearAuth();
      queryClient.clear(); // مسح جميع البيانات المخزنة (المالية، الأكاديمية...) لحماية الخصوصية
      window.location.href = "/login";
    },
    onError: () => {
      // حتى لو فشل الاتصال بالخادم، نقوم بطرده محلياً لحماية البيانات
      clearAuth();
      window.location.href = "/login";
    }
  });

  // 🟢 3. جلب بيانات الهوية (Query)
  const { data: user, isLoading: isFetchingMe } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
      const response = await apiClient.get("/identity/me");
      setUser(response.data); // تحديث الـ Store المحلي
      return response.data;
    },
    retry: false, // لا تحاول مراراً إذا لم يكن مسجلاً
  });

  return {
    user,
    isFetchingMe,
    login: loginMutation.mutateAsync,
    isLoggingIn: loginMutation.isPending,
    logout: logoutMutation.mutate,
    isLoggingOut: logoutMutation.isPending,
  };
};