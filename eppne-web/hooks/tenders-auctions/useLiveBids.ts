// hooks/tenders-auctions/useLiveBids.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAuctionBids, placeBid } from '@/services/tenders-auctions';

export const useAuctionBids = (auctionId: number, limit: number = 50) => {
  return useQuery({
    queryKey: ['auction-bids', auctionId],
    queryFn: () => getAuctionBids(auctionId, { limit }).then((res) => res.data),
    enabled: !!auctionId,
    staleTime: 5 * 1000,
    refetchInterval: (data) => {
      if (data && data.length > 0) return 3000;
      return false;
    },
  });
};

export const usePlaceBid = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ auctionId, data, idempotencyKey }: { auctionId: number; data: { bid_amount_mrusdt: number }; idempotencyKey?: string }) =>
      placeBid(auctionId, data, idempotencyKey),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['auction-bids', variables.auctionId] });
      queryClient.invalidateQueries({ queryKey: ['auction', variables.auctionId] });
    },
  });
};