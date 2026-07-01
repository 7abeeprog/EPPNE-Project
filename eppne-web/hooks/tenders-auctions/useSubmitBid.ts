// hooks/tenders-auctions/useSubmitBid.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { submitBid } from '@/services/tenders-auctions';

export const useSubmitBid = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof submitBid>[0]; idempotencyKey?: string }) =>
      submitBid(data, idempotencyKey),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tender-bids', variables.data.tender_id] });
      queryClient.invalidateQueries({ queryKey: ['my-bids'] });
    },
  });
};