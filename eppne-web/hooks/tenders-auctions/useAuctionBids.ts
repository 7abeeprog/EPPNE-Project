// hooks/tenders-auctions/useAuctionBids.ts
import { useQuery } from '@tanstack/react-query';
import { getAuctionBids } from '@/services/tenders-auctions';

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