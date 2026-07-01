// hooks/tenders-auctions/useTenderBids.ts
import { useQuery } from '@tanstack/react-query';
import { getTenderBids } from '@/services/tenders-auctions';

export const useTenderBids = (tenderId: number) => {
  return useQuery({
    queryKey: ['tender-bids', tenderId],
    queryFn: () => getTenderBids(tenderId).then((res) => res.data),
    enabled: !!tenderId,
    staleTime: 2 * 60 * 1000,
  });
};