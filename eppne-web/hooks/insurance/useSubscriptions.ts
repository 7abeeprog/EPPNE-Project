// hooks/insurance/useSubscriptions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { InsuranceService } from '@/services/insurance';

export const useMySubscriptions = (params?: { status?: string; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['insurance-subscriptions', params],
    queryFn: () => InsuranceService.getMySubscriptions(params),
    staleTime: 2 * 60 * 1000,
  });
};

export const useSubscription = (id: number) => {
  return useQuery({
    queryKey: ['insurance-subscription', id],
    queryFn: () => InsuranceService.getSubscription(id),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useSubscribe = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof InsuranceService.subscribe>[0]; idempotencyKey?: string }) =>
      InsuranceService.subscribe(data, { 'Idempotency-Key': idempotencyKey }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['insurance-subscriptions'] });
    },
  });
};

export const useRenewSubscription = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (subscriptionId: number) => InsuranceService.renewSubscription(subscriptionId),
    onSuccess: (_, subscriptionId) => {
      queryClient.invalidateQueries({ queryKey: ['insurance-subscription', subscriptionId] });
      queryClient.invalidateQueries({ queryKey: ['insurance-subscriptions'] });
    },
  });
};

export const useCancelSubscription = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (subscriptionId: number) => InsuranceService.cancelSubscription(subscriptionId),
    onSuccess: (_, subscriptionId) => {
      queryClient.invalidateQueries({ queryKey: ['insurance-subscription', subscriptionId] });
      queryClient.invalidateQueries({ queryKey: ['insurance-subscriptions'] });
    },
  });
};