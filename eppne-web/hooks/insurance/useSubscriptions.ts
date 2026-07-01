// hooks/insurance/useSubscriptions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMySubscriptions, getSubscription, subscribe, renewSubscription, cancelSubscription } from '@/services/insurance';

export const useMySubscriptions = (params?: { status?: string; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['insurance-subscriptions', params],
    queryFn: () => getMySubscriptions(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useSubscription = (id: number) => {
  return useQuery({
    queryKey: ['insurance-subscription', id],
    queryFn: () => getSubscription(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useSubscribe = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof subscribe>[0]; idempotencyKey?: string }) =>
      subscribe(data, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['insurance-subscriptions'] });
    },
  });
};

export const useRenewSubscription = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (subscriptionId: number) => renewSubscription(subscriptionId),
    onSuccess: (_, subscriptionId) => {
      queryClient.invalidateQueries({ queryKey: ['insurance-subscription', subscriptionId] });
      queryClient.invalidateQueries({ queryKey: ['insurance-subscriptions'] });
    },
  });
};

export const useCancelSubscription = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (subscriptionId: number) => cancelSubscription(subscriptionId),
    onSuccess: (_, subscriptionId) => {
      queryClient.invalidateQueries({ queryKey: ['insurance-subscription', subscriptionId] });
      queryClient.invalidateQueries({ queryKey: ['insurance-subscriptions'] });
    },
  });
};