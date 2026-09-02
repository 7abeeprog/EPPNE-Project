// hooks/tenders-auctions/useBids.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMyBids } from '@/services/tenders-auctions';
import { TendersAuctionsService } from '@/services/tenders-auctions';

export const useTenderBids = (tenderId: number) => {
  return useQuery({
    queryKey: ['tender-bids', tenderId],
    queryFn: () => TendersAuctionsService.getTenderBids(tenderId),
    enabled: !!tenderId,
    staleTime: 2 * 60 * 1000,
  });
};

export const useSubmitBid = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof TendersAuctionsService.submitBid>[0]; idempotencyKey?: string }) =>
      TendersAuctionsService.submitBid(data, { 'Idempotency-Key': idempotencyKey }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tender-bids', variables.data.tender_id] });
      queryClient.invalidateQueries({ queryKey: ['my-bids'] });
    },
  });
};

export const useEvaluateBid = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ bidId, data, idempotencyKey }: { bidId: number; data: { technical_score: number }; idempotencyKey?: string }) =>
      TendersAuctionsService.evaluateBid(bidId, data, { 'Idempotency-Key': idempotencyKey }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tender-bids'] });
    },
  });
};

export const useMyBids = () => {
  return useQuery({
    queryKey: ['my-bids'],
    queryFn: () => getMyBids().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};