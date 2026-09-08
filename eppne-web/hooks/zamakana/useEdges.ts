// hooks/zamakana/useEdges.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ZamakanaService } from '@/services/zamakana';

export const useCreateEdge = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof ZamakanaService.createEdge>[0]; idempotencyKey?: string }) =>
      ZamakanaService.createEdge(data, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zamakana-graph'] });
      queryClient.invalidateQueries({ queryKey: ['zamakana-nodes'] });
    },
  });
};