// hooks/saas/useServices.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { SaaSService } from "@/services/saas.service";
import { useAuthStore } from "@/store/auth-store";
import { toast } from "sonner";

export const useServices = () => {
  const { isAuthenticated } = useAuthStore();

  return useQuery({
    queryKey: ['saas', 'services'],
    queryFn: () => SaaSService.getServices(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });
};

export const useServiceAccess = () => {
  const { isAuthenticated } = useAuthStore();

  return useQuery({
    queryKey: ['saas', 'service-access'],
    queryFn: () => SaaSService.getServiceAccess(),
    enabled: isAuthenticated,
    staleTime: 2 * 60 * 1000,
  });
};

export const useToggleService = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ serviceId, isActive }: { serviceId: number; isActive: boolean }) =>
      SaaSService.toggleServiceStatus(serviceId, isActive),
    onSuccess: () => {
      toast.success('تم تحديث حالة الخدمة بنجاح');
      queryClient.invalidateQueries({ queryKey: ['saas', 'services'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'فشل تحديث حالة الخدمة');
    },
  });
};