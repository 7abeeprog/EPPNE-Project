// hooks/manufacturing/useRawMaterials.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getRawMaterials, registerRawMaterial, consumeRawMaterial } from '@/services/manufacturing';

export const useRawMaterials = (params?: { skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['manufacturing-raw-materials', params],
    queryFn: () => getRawMaterials(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useRegisterRawMaterial = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof registerRawMaterial>[0]) => registerRawMaterial(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manufacturing-raw-materials'] });
      queryClient.invalidateQueries({ queryKey: ['manufacturing-stats'] });
    },
  });
};

export const useConsumeRawMaterial = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      batchId,
      data,
      idempotencyKey,
    }: {
      batchId: number;
      data: Parameters<typeof consumeRawMaterial>[1];
      idempotencyKey?: string;
    }) => consumeRawMaterial(batchId, data, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manufacturing-raw-materials'] });
      queryClient.invalidateQueries({ queryKey: ['manufacturing-batches'] });
      queryClient.invalidateQueries({ queryKey: ['manufacturing-stats'] });
    },
  });
};