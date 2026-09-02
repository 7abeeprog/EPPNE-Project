// hooks/tenders-auctions/useStartAuction.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { TendersAuctionsService } from '@/services/tenders-auctions';

export const useStartAuction = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (auctionId: number) => TendersAuctionsService.startAuction(auctionId),
    onSuccess: (_, auctionId) => {
      queryClient.invalidateQueries({ queryKey: ['auction', auctionId] });
      queryClient.invalidateQueries({ queryKey: ['auctions'] });
    },
  });
};