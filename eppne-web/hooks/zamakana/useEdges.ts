// hooks/zamakana/useEdges.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createEdge } from '@/services/zamakana';

export const useCreateEdge = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof createEdge>[0]; idempotencyKey?: string }) =>
      createEdge(data, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zamakana-graph'] });
      queryClient.invalidateQueries({ queryKey: ['zamakana-nodes'] });
    },
  });
};