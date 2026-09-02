// hooks/manufacturing/useRawMaterials.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ManufacturingService } from '@/services/manufacturing';

export const useRawMaterials = (params?: { skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['manufacturing-raw-materials', params],
    queryFn: () => ManufacturingService.listRawMaterials(params),
    staleTime: 2 * 60 * 1000,
  });
};

export const useRegisterRawMaterial = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof ManufacturingService.registerRawMaterial>[0]) => ManufacturingService.registerRawMaterial(data),
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
      data: Parameters<typeof ManufacturingService.consumeRawMaterial>[1];
      idempotencyKey?: string;
    }) => ManufacturingService.consumeRawMaterial(batchId, data, { 'Idempotency-Key': idempotencyKey }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manufacturing-raw-materials'] });
      queryClient.invalidateQueries({ queryKey: ['manufacturing-batches'] });
      queryClient.invalidateQueries({ queryKey: ['manufacturing-stats'] });
    },
  });
};