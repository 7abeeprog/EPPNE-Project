// hooks/tenders-auctions/useTenderBids.ts
import { useQuery } from '@tanstack/react-query';
import { TendersAuctionsService } from '@/services/tenders-auctions';

export const useTenderBids = (tenderId: number) => {
  return useQuery({
    queryKey: ['tender-bids', tenderId],
    queryFn: () => TendersAuctionsService.getTenderBids(tenderId),
    enabled: !!tenderId,
    staleTime: 2 * 60 * 1000,
  });
};