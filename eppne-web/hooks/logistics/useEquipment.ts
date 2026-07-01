// hooks/logistics/useEquipment.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getEquipment, getEquipmentItem, createEquipment, updateEquipment, createMaintenance } from '@/services/logistics';

export const useEquipment = (params?: { equipment_type?: string; status?: string; warehouse_id?: number; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['logistics-equipment', params],
    queryFn: () => getEquipment(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useEquipmentItem = (id: number) => {
  return useQuery({
    queryKey: ['logistics-equipment-item', id],
    queryFn: () => getEquipmentItem(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateEquipment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof createEquipment>[0]) => createEquipment(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistics-equipment'] });
      queryClient.invalidateQueries({ queryKey: ['logistics-stats'] });
    },
  });
};

export const useUpdateEquipment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateEquipment>[1] }) =>
      updateEquipment(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['logistics-equipment-item', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['logistics-equipment'] });
    },
  });
};

export const useCreateMaintenance = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ equipmentId, data }: { equipmentId: number; data: Parameters<typeof createMaintenance>[1] }) =>
      createMaintenance(equipmentId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['logistics-equipment-item', variables.equipmentId] });
      queryClient.invalidateQueries({ queryKey: ['logistics-equipment'] });
    },
  });
};