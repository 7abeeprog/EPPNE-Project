// hooks/tenders-auctions/useCloseAuction.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { closeAuction } from '@/services/tenders-auctions';

export const useCloseAuction = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (auctionId: number) => closeAuction(auctionId),
    onSuccess: (_, auctionId) => {
      queryClient.invalidateQueries({ queryKey: ['auction', auctionId] });
      queryClient.invalidateQueries({ queryKey: ['auctions'] });
    },
  });
};