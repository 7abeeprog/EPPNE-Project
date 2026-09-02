// hooks/tenders-auctions/useUpdateTender.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { TendersAuctionsService } from '@/services/tenders-auctions';

export const useUpdateTender = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof TendersAuctionsService.updateTender>[1] }) =>
      TendersAuctionsService.updateTender(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tender', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['tenders'] });
    },
  });
};