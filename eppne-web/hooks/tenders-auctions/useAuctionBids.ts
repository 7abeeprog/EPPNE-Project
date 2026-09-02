// hooks/tenders-auctions/useAuctionBids.ts
import { useQuery } from '@tanstack/react-query';
import { TendersAuctionsService } from '@/services/tenders-auctions';

export const useAuctionBids = (auctionId: number, limit: number = 50) => {
  return useQuery({
    queryKey: ['auction-bids', auctionId],
    queryFn: () => TendersAuctionsService.getAuctionBids(auctionId, limit),
    enabled: !!auctionId,
    staleTime: 5 * 1000,
    refetchInterval: (data) => {
      if (data && data.length > 0) return 3000;
      return false;
    },
  });
};