// hooks/tourism-sports/useDestinations.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getDestination } from '@/services/tourism-sports';
import { TourismSportsService } from '@/services/tourism-sports';

export const useDestinations = (params?: { destination_type?: string }) => {
  return useQuery({
    queryKey: ['tourism-destinations', params],
    queryFn: () => TourismSportsService.listDestinations(params),
    staleTime: 2 * 60 * 1000,
  });
};

export const useDestination = (id: number) => {
  return useQuery({
    queryKey: ['tourism-destination', id],
    queryFn: () => getDestination(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateDestination = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof TourismSportsService.createDestination>[0]) => TourismSportsService.createDestination(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tourism-destinations'] });
    },
  });
};