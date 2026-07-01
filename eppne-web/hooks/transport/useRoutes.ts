// hooks/transport/useRoutes.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getRoutes, getRoute, createRoute, updateRoute, deleteRoute, optimizeRoute } from '@/services/transport';
import type { RouteFormData } from '@/types/transport';

export const useRoutes = (params?: { is_active?: boolean; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['transport-routes', params],
    queryFn: () => getRoutes(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useRoute = (id: number) => {
  return useQuery({
    queryKey: ['transport-route', id],
    queryFn: () => getRoute(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateRoute = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RouteFormData) => createRoute(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-routes'] });
      queryClient.invalidateQueries({ queryKey: ['transport-stats'] });
    },
  });
};

export const useUpdateRoute = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<RouteFormData> }) =>
      updateRoute(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-routes'] });
      queryClient.invalidateQueries({ queryKey: ['transport-route'] });
    },
  });
};

export const useDeleteRoute = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteRoute(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-routes'] });
      queryClient.invalidateQueries({ queryKey: ['transport-stats'] });
    },
  });
};

export const useOptimizeRoute = () => {
  return useMutation({
    mutationFn: ({ startHubId, endHubId }: { startHubId: number; endHubId: number }) =>
      optimizeRoute(startHubId, endHubId).then((res) => res.data),
  });
};