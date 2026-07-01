// hooks/transport/useBookings.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getBookings, getMyBookings, bookTrip, cancelBooking } from '@/services/transport';
import type { TripBooking } from '@/types/transport';

export const useBookings = (params?: { trip_id?: number; passenger_id?: number; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['transport-bookings', params],
    queryFn: () => getBookings(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useMyBookings = () => {
  return useQuery({
    queryKey: ['transport-my-bookings'],
    queryFn: () => getMyBookings().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useBookTrip = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Partial<TripBooking>; idempotencyKey?: string }) =>
      bookTrip(data, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-my-bookings'] });
      queryClient.invalidateQueries({ queryKey: ['transport-bookings'] });
      queryClient.invalidateQueries({ queryKey: ['transport-my-trips'] });
    },
  });
};

export const useCancelBooking = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (bookingId: number) => cancelBooking(bookingId),
    onSuccess: (_, bookingId) => {
      queryClient.invalidateQueries({ queryKey: ['transport-my-bookings'] });
      queryClient.invalidateQueries({ queryKey: ['transport-bookings'] });
    },
  });
};