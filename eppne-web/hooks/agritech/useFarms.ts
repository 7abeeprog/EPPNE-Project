// hooks/agritech/useFarms.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getFarms, getFarm, createFarm, updateFarm, deleteFarm } from '@/services/agritech';
import type { FarmType, SmartFarm } from '@/types/agritech';

export const useFarms = (params?: { farm_type?: FarmType; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['agritech-farms', params],
    queryFn: () => getFarms(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useFarm = (id: number) => {
  return useQuery({
    queryKey: ['agritech-farm', id],
    queryFn: () => getFarm(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateFarm = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof createFarm>[0]) => createFarm(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agritech-farms'] });
      queryClient.invalidateQueries({ queryKey: ['agritech-stats'] });
    },
  });
};

export const useUpdateFarm = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<{ name: string; has_insurance: boolean }> }) =>
      updateFarm(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['agritech-farm', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['agritech-farms'] });
    },
  });
};

export const useDeleteFarm = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteFarm(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agritech-farms'] });
      queryClient.invalidateQueries({ queryKey: ['agritech-stats'] });
    },
  });
};