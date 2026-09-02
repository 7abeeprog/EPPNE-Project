// hooks/transport/useTrips.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { TransportService } from '@/services/transport';
import type { TripFormData, TripStatus } from '@/types/transport';

export const useMyTrips = (params?: { status?: TripStatus; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['transport-my-trips', params],
    queryFn: () => TransportService.getMyTrips(params),
    staleTime: 2 * 60 * 1000,
    refetchInterval: (query) => {
      // تحديث مستمر إذا كانت هناك رحلات نشطة
      const data = query.state.data;
      if (data?.some((trip) => trip.status === 'ONGOING' || trip.status === 'SCHEDULED')) {
        return 15000;
      }
      return false;
    },
  });
};

export const useTrip = (id: number) => {
  return useQuery({
    queryKey: ['transport-trip', id],
    queryFn: () => TransportService.getTrip(id),
    enabled: !!id,
    staleTime: 60 * 1000,
    refetchInterval: (query) => {
      if (query.state.data?.status === 'ONGOING') return 10000;
      return false;
    },
  });
};

export const useCreateTrip = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TripFormData) => TransportService.createTrip(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-my-trips'] });
      queryClient.invalidateQueries({ queryKey: ['transport-stats'] });
    },
  });
};

export const useStartTrip = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ tripId, actualStart }: { tripId: number; actualStart: string }) =>
      TransportService.startTrip(tripId, { actual_start: actualStart }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['transport-trip', variables.tripId] });
      queryClient.invalidateQueries({ queryKey: ['transport-my-trips'] });
      queryClient.invalidateQueries({ queryKey: ['transport-stats'] });
    },
  });
};

export const useCompleteTrip = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ tripId, actualEnd, totalDistance }: { tripId: number; actualEnd: string; totalDistance: number }) =>
      TransportService.completeTrip(tripId, { actual_end: actualEnd, total_distance_km: totalDistance }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['transport-trip', variables.tripId] });
      queryClient.invalidateQueries({ queryKey: ['transport-my-trips'] });
      queryClient.invalidateQueries({ queryKey: ['transport-stats'] });
    },
  });
};