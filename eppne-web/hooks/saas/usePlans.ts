// hooks/saas/usePlans.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { SaaSService } from "@/services/saas.service";
import { ServicePlan } from "@/types/saas";
import { toast } from "sonner";

export const usePlans = (serviceId?: number) => {
  return useQuery({
    queryKey: ['saas', 'plans', serviceId],
    queryFn: () => SaaSService.getPlans(serviceId),
    staleTime: 5 * 60 * 1000,
  });
};

export const useCreatePlan = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: Omit<ServicePlan, 'id' | 'created_at' | 'updated_at'>) =>
      SaaSService.createPlan(payload),
    onSuccess: () => {
      toast.success('تم إنشاء الخطة بنجاح');
      queryClient.invalidateQueries({ queryKey: ['saas', 'plans'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'فشل إنشاء الخطة');
    },
  });
};

export const useUpdatePlan = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ planId, payload }: { planId: number; payload: Partial<ServicePlan> }) =>
      SaaSService.updatePlan(planId, payload),
    onSuccess: () => {
      toast.success('تم تحديث الخطة بنجاح');
      queryClient.invalidateQueries({ queryKey: ['saas', 'plans'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'فشل تحديث الخطة');
    },
  });
};

export const useDeletePlan = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (planId: number) => SaaSService.deletePlan(planId),
    onSuccess: () => {
      toast.success('تم حذف الخطة بنجاح');
      queryClient.invalidateQueries({ queryKey: ['saas', 'plans'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'فشل حذف الخطة');
    },
  });
};