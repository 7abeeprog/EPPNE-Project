// hooks/tenders-auctions/useEvaluateBid.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { evaluateBid } from '@/services/tenders-auctions';

export const useEvaluateBid = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ bidId, data, idempotencyKey }: { bidId: number; data: { technical_score: number }; idempotencyKey?: string }) =>
      evaluateBid(bidId, data, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tender-bids'] });
      queryClient.invalidateQueries({ queryKey: ['tenders'] });
    },
  });
};