// hooks/tenders-auctions/useOpenTender.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { TendersAuctionsService } from '@/services/tenders-auctions';

export const useOpenTender = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tenderId: number) => TendersAuctionsService.openTender(tenderId),
    onSuccess: (_, tenderId) => {
      queryClient.invalidateQueries({ queryKey: ['tender', tenderId] });
      queryClient.invalidateQueries({ queryKey: ['tenders'] });
    },
  });
};