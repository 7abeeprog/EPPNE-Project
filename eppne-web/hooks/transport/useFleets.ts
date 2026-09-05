// hooks/transport/useFleets.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { TransportService } from '@/services/transport';

export const useFleets = (params?: { skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['transport-fleets', params],
    queryFn: () => TransportService.listFleets(params),
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateFleet = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string }) => TransportService.createFleet(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-fleets'] });
      queryClient.invalidateQueries({ queryKey: ['transport-stats'] });
    },
  });
};

export const useUpdateFleet = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: { name: string } }) =>
      TransportService.updateFleet(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-fleets'] });
    },
  });
};

export const useDeleteFleet = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => TransportService.deleteFleet(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-fleets'] });
      queryClient.invalidateQueries({ queryKey: ['transport-stats'] });
    },
  });
};
