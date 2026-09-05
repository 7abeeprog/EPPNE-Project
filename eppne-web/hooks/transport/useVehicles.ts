// hooks/transport/useVehicles.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { TransportService } from '@/services/transport';
import type { VehicleFormData, VehicleStatus } from '@/types/transport';

export const useVehicles = (params?: { fleet_id?: number; status?: VehicleStatus; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['transport-vehicles', params],
    queryFn: () => TransportService.listVehicles(params),
    staleTime: 2 * 60 * 1000,
  });
};

export const useAvailableVehicles = (params?: { fleet_id?: number }) => {
  return useQuery({
    queryKey: ['transport-available-vehicles', params],
    queryFn: () => TransportService.getAvailableVehicles(params),
    staleTime: 60 * 1000,
  });
};

export const useVehicle = (id: number) => {
  return useQuery({
    queryKey: ['transport-vehicle', id],
    queryFn: () => TransportService.getVehicle(id),
    enabled: !!id,
    staleTime: 60 * 1000,
  });
};

export const useCreateVehicle = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: VehicleFormData) => TransportService.createVehicle(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-vehicles'] });
      queryClient.invalidateQueries({ queryKey: ['transport-available-vehicles'] });
      queryClient.invalidateQueries({ queryKey: ['transport-stats'] });
    },
  });
};

export const useUpdateVehicle = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<VehicleFormData> }) =>
      TransportService.updateVehicle(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['transport-vehicle', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['transport-vehicles'] });
      queryClient.invalidateQueries({ queryKey: ['transport-available-vehicles'] });
    },
  });
};

export const useDeleteVehicle = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => TransportService.deleteVehicle(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-vehicles'] });
      queryClient.invalidateQueries({ queryKey: ['transport-available-vehicles'] });
      queryClient.invalidateQueries({ queryKey: ['transport-stats'] });
    },
  });
};

export const useUpdateVehicleLocation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, location }: { id: number; location: Record<string, number> }) =>
      TransportService.updateVehicleLocation(id, location),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['transport-vehicle', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['transport-vehicles'] });
      queryClient.invalidateQueries({ queryKey: ['transport-available-vehicles'] });
    },
  });
};
