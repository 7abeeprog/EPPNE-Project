// hooks/saas/useDashboard.ts
import { useQuery } from "@tanstack/react-query";
import { SaaSService } from "@/services/saas.service";
import { useAuthStore } from "@/store/auth-store";

export const useDashboardStats = () => {
  const { isAuthenticated } = useAuthStore();

  return useQuery({
    queryKey: ['saas', 'dashboard', 'stats'],
    queryFn: () => SaaSService.getDashboardStats(),
    enabled: isAuthenticated,
    staleTime: 2 * 60 * 1000,
    refetchInterval: 60 * 1000, // تحديث كل دقيقة
  });
};