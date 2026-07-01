// hooks/transport/useFleets.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getFleets, createFleet, updateFleet, deleteFleet } from '@/services/transport';

export const useFleets = () => {
  return useQuery({
    queryKey: ['transport-fleets'],
    queryFn: () => getFleets().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateFleet = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string }) => createFleet(data),
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
      updateFleet(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-fleets'] });
    },
  });
};

export const useDeleteFleet = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteFleet(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-fleets'] });
      queryClient.invalidateQueries({ queryKey: ['transport-stats'] });
    },
  });
};