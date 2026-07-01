// hooks/tenders-auctions/useMyBids.ts
import { useQuery } from '@tanstack/react-query';
import { getMyBids } from '@/services/tenders-auctions';

export const useMyBids = () => {
  return useQuery({
    queryKey: ['my-bids'],
    queryFn: () => getMyBids().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};