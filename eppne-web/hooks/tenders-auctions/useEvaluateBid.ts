// hooks/tenders-auctions/useEvaluateBid.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { TendersAuctionsService } from '@/services/tenders-auctions';

export const useEvaluateBid = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ bidId, data, idempotencyKey }: { bidId: number; data: { technical_score: number }; idempotencyKey?: string }) =>
      TendersAuctionsService.evaluateBid(bidId, data, { 'Idempotency-Key': idempotencyKey }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tender-bids'] });
      queryClient.invalidateQueries({ queryKey: ['tenders'] });
    },
  });
};