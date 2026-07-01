// hooks/agritech/useTraceability.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTraceability, addTraceabilityStage, generateTraceabilityQR } from '@/services/agritech';

export const useTraceability = (traceableType: string, traceableId: number) => {
  return useQuery({
    queryKey: ['agritech-traceability', traceableType, traceableId],
    queryFn: () => getTraceability(traceableType, traceableId).then((res) => res.data),
    enabled: !!traceableId && !!traceableType,
    staleTime: 2 * 60 * 1000,
  });
};

export const useAddTraceabilityStage = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof addTraceabilityStage>[0]) => addTraceabilityStage(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['agritech-traceability', variables.traceable_type, variables.traceable_id],
      });
    },
  });
};

export const useGenerateTraceabilityQR = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ traceableType, traceableId }: { traceableType: string; traceableId: number }) =>
      generateTraceabilityQR(traceableType, traceableId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['agritech-traceability', variables.traceableType, variables.traceableId],
      });
    },
  });
};