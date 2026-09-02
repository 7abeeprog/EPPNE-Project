// hooks/tourism-sports/useEvents.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getEvents } from '@/services/tourism-sports';
import { TourismSportsService } from '@/services/tourism-sports';

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
    queryFn: () => TourismSportsService.getEvent(id),
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
      data: Parameters<typeof TourismSportsService.buyTicket>[0];
      idempotencyKey?: string;
    }) => TourismSportsService.buyTicket(data, { 'Idempotency-Key': idempotencyKey }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tourism-tickets'] });
      queryClient.invalidateQueries({ queryKey: ['tourism-stats'] });
    },
  });
};