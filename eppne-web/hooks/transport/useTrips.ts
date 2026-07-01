// hooks/transport/useTrips.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getMyTrips,
  getTrip,
  createTrip,
  startTrip,
  completeTrip,
} from '@/services/transport';
import type { TripFormData, TripStatus } from '@/types/transport';

export const useMyTrips = (params?: { status?: TripStatus; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['transport-my-trips', params],
    queryFn: () => getMyTrips(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
    refetchInterval: (data) => {
      // تحديث مستمر إذا كانت هناك رحلات نشطة
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
    queryFn: () => getTrip(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 60 * 1000,
    refetchInterval: (data) => {
      if (data?.status === 'ONGOING') return 10000;
      return false;
    },
  });
};

export const useCreateTrip = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TripFormData) => createTrip(data),
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
      startTrip(tripId, actualStart),
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
      completeTrip(tripId, actualEnd, totalDistance),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['transport-trip', variables.tripId] });
      queryClient.invalidateQueries({ queryKey: ['transport-my-trips'] });
      queryClient.invalidateQueries({ queryKey: ['transport-stats'] });
    },
  });
};