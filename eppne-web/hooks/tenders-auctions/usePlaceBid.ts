// hooks/tenders-auctions/usePlaceBid.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { TendersAuctionsService } from '@/services/tenders-auctions';

export const usePlaceBid = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ auctionId, data, idempotencyKey }: { auctionId: number; data: { bid_amount_mrusdt: number }; idempotencyKey?: string }) =>
      TendersAuctionsService.placeBid(auctionId, data, { 'Idempotency-Key': idempotencyKey }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['auction-bids', variables.auctionId] });
      queryClient.invalidateQueries({ queryKey: ['auction', variables.auctionId] });
    },
  });
};