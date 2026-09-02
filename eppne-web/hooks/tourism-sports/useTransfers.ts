// hooks/tourism-sports/useTransfers.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTransfers } from '@/services/tourism-sports';
import { TourismSportsService } from '@/services/tourism-sports';

export const useTransfers = (params?: { status?: string }) => {
  return useQuery({
    queryKey: ['sports-transfers', params],
    queryFn: () => getTransfers(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const usePlaceTransferBid = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      data,
      idempotencyKey,
    }: {
      data: Parameters<typeof TourismSportsService.placeTransferBid>[0];
      idempotencyKey?: string;
    }) => TourismSportsService.placeTransferBid(data, { 'Idempotency-Key': idempotencyKey }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sports-transfers'] });
      queryClient.invalidateQueries({ queryKey: ['sports-players'] });
    },
  });
};