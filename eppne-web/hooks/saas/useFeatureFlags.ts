// hooks/saas/useFeatureFlags.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { SaaSService } from "@/services/saas.service";
import { toast } from "sonner";

export const useFeatureFlags = (serviceCode?: string) => {
  return useQuery({
    queryKey: ['saas', 'feature-flags', serviceCode],
    queryFn: () => SaaSService.getFeatureFlags(serviceCode),
    staleTime: 2 * 60 * 1000,
  });
};

export const useToggleFeatureFlag = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ serviceCode, featureKey, enabled }: { serviceCode: string; featureKey: string; enabled: boolean }) =>
      SaaSService.toggleFeatureFlag(serviceCode, featureKey, enabled),
    onSuccess: (_, variables) => {
      toast.success(`تم ${variables.enabled ? 'تفعيل' : 'تعطيل'} الميزة بنجاح`);
      queryClient.invalidateQueries({ queryKey: ['saas', 'feature-flags'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'فشل تحديث الميزة');
    },
  });
};