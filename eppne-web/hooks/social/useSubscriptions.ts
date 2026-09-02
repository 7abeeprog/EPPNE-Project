// hooks/social/useSubscriptions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getSubscriptionPlans, cancelSubscription } from '@/services/social';
import { SocialService } from '@/services/social';

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
    queryFn: () => SocialService.getGroupSubscription(groupId),
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
      data: Parameters<typeof SocialService.subscribeGroup>[1];
      idempotencyKey?: string;
    }) => SocialService.subscribeGroup(groupId, data),
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