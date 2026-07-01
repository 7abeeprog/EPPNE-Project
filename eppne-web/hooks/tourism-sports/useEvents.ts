// hooks/tourism-sports/useEvents.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getEvents, getEvent, purchaseTicket } from '@/services/tourism-sports';

export const useEvents = () => {
  return useQuery({
    queryKey: ['tourism-events'],
    queryFn: () => getEvents().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useEvent = (id: number) => {
  return useQuery({
    queryKey: ['tourism-event', id],
    queryFn: () => getEvent(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const usePurchaseTicket = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      data,
      idempotencyKey,
    }: {
      data: Parameters<typeof purchaseTicket>[0];
      idempotencyKey?: string;
    }) => purchaseTicket(data, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tourism-tickets'] });
      queryClient.invalidateQueries({ queryKey: ['tourism-stats'] });
    },
  });
};