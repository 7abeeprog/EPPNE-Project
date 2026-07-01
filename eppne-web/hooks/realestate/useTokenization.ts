// hooks/realestate/useTokenization.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAssetTokenization, createTokenization, buyFractionalShare } from '@/services/realestate';
import type { TokenizationFormData } from '@/types/realestate';

export const useAssetTokenization = (unitId: number) => {
  return useQuery({
    queryKey: ['realestate-tokenization', unitId],
    queryFn: () => getAssetTokenization(unitId).then((res) => res.data),
    enabled: !!unitId,
    staleTime: 5 * 60 * 1000,
  });
};

export const useCreateTokenization = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TokenizationFormData) => createTokenization(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['realestate-tokenization', variables.unit_id] });
      queryClient.invalidateQueries({ queryKey: ['realestate-properties'] });
    },
  });
};

export const useBuyFractionalShare = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ unitId, percentage, idempotencyKey }: { unitId: number; percentage: number; idempotencyKey: string }) =>
      buyFractionalShare(unitId, { ownership_percentage: percentage }, idempotencyKey),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['realestate-tokenization', variables.unitId] });
      queryClient.invalidateQueries({ queryKey: ['realestate-my-ownerships'] });
    },
  });
};