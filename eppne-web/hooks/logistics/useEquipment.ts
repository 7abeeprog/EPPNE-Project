// hooks/logistics/useEquipment.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getEquipmentItem } from '@/services/logistics';
import { LogisticsService } from '@/services/logistics';

export const useEquipment = (params?: { equipment_type?: string; status?: string; warehouse_id?: number; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['logistics-equipment', params],
    queryFn: () => LogisticsService.getEquipment(params).then((res) => res.data),
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
    mutationFn: (data: Parameters<typeof LogisticsService.createEquipment>[0]) => LogisticsService.createEquipment(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistics-equipment'] });
      queryClient.invalidateQueries({ queryKey: ['logistics-stats'] });
    },
  });
};

export const useUpdateEquipment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof LogisticsService.updateEquipment>[1] }) =>
      LogisticsService.updateEquipment(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['logistics-equipment-item', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['logistics-equipment'] });
    },
  });
};

export const useCreateMaintenance = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ equipmentId, data }: { equipmentId: number; data: Parameters<typeof LogisticsService.createMaintenance>[1] }) =>
      LogisticsService.createMaintenance(equipmentId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['logistics-equipment-item', variables.equipmentId] });
      queryClient.invalidateQueries({ queryKey: ['logistics-equipment'] });
    },
  });
};