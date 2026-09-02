// hooks/tenders-auctions/useSubmitBid.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { TendersAuctionsService } from '@/services/tenders-auctions';

export const useSubmitBid = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof TendersAuctionsService.submitBid>[0]; idempotencyKey?: string }) =>
      TendersAuctionsService.submitBid(data, { 'Idempotency-Key': idempotencyKey }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tender-bids', variables.data.tender_id] });
      queryClient.invalidateQueries({ queryKey: ['my-bids'] });
    },
  });
};