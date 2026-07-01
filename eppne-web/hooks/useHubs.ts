// hooks/transport/useHubs.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getHubs, createHub, updateHub, deleteHub } from '@/services/transport';
import type { HubFormData, HubType } from '@/types/transport';

export const useHubs = (params?: { hub_type?: HubType; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['transport-hubs', params],
    queryFn: () => getHubs(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateHub = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: HubFormData) => createHub(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-hubs'] });
      queryClient.invalidateQueries({ queryKey: ['transport-stats'] });
    },
  });
};

export const useUpdateHub = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<HubFormData> }) =>
      updateHub(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-hubs'] });
    },
  });
};

export const useDeleteHub = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteHub(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-hubs'] });
      queryClient.invalidateQueries({ queryKey: ['transport-stats'] });
    },
  });
};