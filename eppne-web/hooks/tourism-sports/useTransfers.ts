// hooks/tourism-sports/useTransfers.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTransfers, placeTransferBid } from '@/services/tourism-sports';

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
      data: Parameters<typeof placeTransferBid>[0];
      idempotencyKey?: string;
    }) => placeTransferBid(data, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sports-transfers'] });
      queryClient.invalidateQueries({ queryKey: ['sports-players'] });
    },
  });
};