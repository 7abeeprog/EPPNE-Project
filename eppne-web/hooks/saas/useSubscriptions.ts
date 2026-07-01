// hooks/saas/useSubscriptions.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { SaaSService } from "@/services/saas.service";
import { SubscribeRequest, UpdateSubscriptionRequest } from "@/types/saas";
import { toast } from "sonner";

export const useSubscriptions = (skip: number = 0, limit: number = 20, status?: string) => {
  return useQuery({
    queryKey: ['saas', 'subscriptions', skip, limit, status],
    queryFn: () => SaaSService.getSubscriptions(skip, limit, status),
    staleTime: 2 * 60 * 1000,
  });
};

export const useSubscribe = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: SubscribeRequest) => SaaSService.subscribe(payload),
    onSuccess: () => {
      toast.success('تم الاشتراك بنجاح! 🎉');
      queryClient.invalidateQueries({ queryKey: ['saas', 'subscriptions'] });
      queryClient.invalidateQueries({ queryKey: ['saas', 'service-access'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'فشل الاشتراك');
    },
  });
};

export const useUpdateSubscription = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ subscriptionId, payload }: { subscriptionId: number; payload: UpdateSubscriptionRequest }) =>
      SaaSService.updateSubscription(subscriptionId, payload),
    onSuccess: () => {
      toast.success('تم تحديث الاشتراك بنجاح');
      queryClient.invalidateQueries({ queryKey: ['saas', 'subscriptions'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'فشل تحديث الاشتراك');
    },
  });
};

export const useCancelSubscription = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (subscriptionId: number) => SaaSService.cancelSubscription(subscriptionId),
    onSuccess: () => {
      toast.success('تم إلغاء الاشتراك بنجاح');
      queryClient.invalidateQueries({ queryKey: ['saas', 'subscriptions'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'فشل إلغاء الاشتراك');
    },
  });
};

export const useRenewSubscription = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (subscriptionId: number) => SaaSService.renewSubscription(subscriptionId),
    onSuccess: () => {
      toast.success('تم تجديد الاشتراك بنجاح');
      queryClient.invalidateQueries({ queryKey: ['saas', 'subscriptions'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'فشل تجديد الاشتراك');
    },
  });
};