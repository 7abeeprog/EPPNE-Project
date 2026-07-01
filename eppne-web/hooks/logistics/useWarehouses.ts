// hooks/logistics/useWarehouses.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getWarehouses, getWarehouse, createWarehouse, updateWarehouse, deleteWarehouse } from '@/services/logistics';

export const useWarehouses = (params?: { warehouse_type?: string; is_active?: boolean; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['logistics-warehouses', params],
    queryFn: () => getWarehouses(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useWarehouse = (id: number) => {
  return useQuery({
    queryKey: ['logistics-warehouse', id],
    queryFn: () => getWarehouse(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateWarehouse = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof createWarehouse>[0]) => createWarehouse(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistics-warehouses'] });
      queryClient.invalidateQueries({ queryKey: ['logistics-stats'] });
    },
  });
};

export const useUpdateWarehouse = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateWarehouse>[1] }) =>
      updateWarehouse(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['logistics-warehouse', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['logistics-warehouses'] });
    },
  });
};

export const useDeleteWarehouse = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteWarehouse(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistics-warehouses'] });
      queryClient.invalidateQueries({ queryKey: ['logistics-stats'] });
    },
  });
};