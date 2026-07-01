// hooks/social/useSubscriptions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getSubscriptionPlans, getGroupSubscription, subscribeGroup, cancelSubscription } from '@/services/social';

export const useSubscriptionPlans = () => {
  return useQuery({
    queryKey: ['social-subscription-plans'],
    queryFn: () => getSubscriptionPlans().then((res) => res.data),
    staleTime: 5 * 60 * 1000,
  });
};

export const useGroupSubscription = (groupId: number) => {
  return useQuery({
    queryKey: ['social-group-subscription', groupId],
    queryFn: () => getGroupSubscription(groupId).then((res) => res.data),
    enabled: !!groupId,
    staleTime: 2 * 60 * 1000,
  });
};

export const useSubscribeGroup = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      groupId,
      data,
      idempotencyKey,
    }: {
      groupId: number;
      data: Parameters<typeof subscribeGroup>[1];
      idempotencyKey?: string;
    }) => subscribeGroup(groupId, data, idempotencyKey),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['social-group-subscription', variables.groupId] });
    },
  });
};

export const useCancelSubscription = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (groupId: number) => cancelSubscription(groupId),
    onSuccess: (_, groupId) => {
      queryClient.invalidateQueries({ queryKey: ['social-group-subscription', groupId] });
    },
  });
};