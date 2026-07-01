// hooks/arbitration-syndicates/useSyndicates.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getSyndicates, getSyndicate, createSyndicate, joinSyndicate } from '@/services/arbitration-syndicates';

export const useSyndicates = () => {
  return useQuery({
    queryKey: ['syndicates'],
    queryFn: () => getSyndicates().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useSyndicate = (id: number) => {
  return useQuery({
    queryKey: ['syndicate', id],
    queryFn: () => getSyndicate(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateSyndicate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof createSyndicate>[0]) => createSyndicate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['syndicates'] });
    },
  });
};

export const useJoinSyndicate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ syndicateId, idempotencyKey }: { syndicateId: number; idempotencyKey?: string }) =>
      joinSyndicate(syndicateId, idempotencyKey),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['syndicate', variables.syndicateId] });
      queryClient.invalidateQueries({ queryKey: ['syndicates'] });
    },
  });
};