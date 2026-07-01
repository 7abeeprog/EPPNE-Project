// hooks/tourism-sports/useDestinations.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getDestinations, getDestination, createDestination } from '@/services/tourism-sports';

export const useDestinations = (params?: { destination_type?: string }) => {
  return useQuery({
    queryKey: ['tourism-destinations', params],
    queryFn: () => getDestinations(params).then((res) => res.data),
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
    mutationFn: (data: Parameters<typeof createDestination>[0]) => createDestination(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tourism-destinations'] });
    },
  });
};