// hooks/manufacturing/useFacilities.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { updateFacility, deleteFacility } from '@/services/manufacturing';
import { ManufacturingService } from '@/services/manufacturing';

export const useFacilities = (params?: { skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['manufacturing-facilities', params],
    queryFn: () => ManufacturingService.listFacilities(params),
    staleTime: 2 * 60 * 1000,
  });
};

export const useFacility = (id: number) => {
  return useQuery({
    queryKey: ['manufacturing-facility', id],
    queryFn: () => ManufacturingService.getFacility(id),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateFacility = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof ManufacturingService.createFacility>[0]) => ManufacturingService.createFacility(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manufacturing-facilities'] });
      queryClient.invalidateQueries({ queryKey: ['manufacturing-stats'] });
    },
  });
};

export const useUpdateFacility = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateFacility>[1] }) =>
      updateFacility(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['manufacturing-facility', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['manufacturing-facilities'] });
    },
  });
};

export const useDeleteFacility = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteFacility(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manufacturing-facilities'] });
      queryClient.invalidateQueries({ queryKey: ['manufacturing-stats'] });
    },
  });
};