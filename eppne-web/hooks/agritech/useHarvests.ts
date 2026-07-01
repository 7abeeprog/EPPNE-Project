// hooks/agritech/useHarvests.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getHarvests, registerHarvest } from '@/services/agritech';

export const useHarvests = (cycleId: number) => {
  return useQuery({
    queryKey: ['agritech-harvests', cycleId],
    queryFn: () => getHarvests(cycleId).then((res) => res.data),
    enabled: !!cycleId,
    staleTime: 2 * 60 * 1000,
  });
};

export const useRegisterHarvest = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      cycleId,
      data,
      idempotencyKey,
    }: {
      cycleId: number;
      data: Parameters<typeof registerHarvest>[1];
      idempotencyKey?: string;
    }) => registerHarvest(cycleId, data, idempotencyKey),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['agritech-harvests', variables.cycleId] });
      queryClient.invalidateQueries({ queryKey: ['agritech-stats'] });
    },
  });
};