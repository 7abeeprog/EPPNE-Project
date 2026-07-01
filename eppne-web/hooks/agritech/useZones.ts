// hooks/agritech/useZones.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getZones, createZone } from '@/services/agritech';

export const useZones = (farmId: number) => {
  return useQuery({
    queryKey: ['agritech-zones', farmId],
    queryFn: () => getZones(farmId).then((res) => res.data),
    enabled: !!farmId,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateZone = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ farmId, data }: { farmId: number; data: Parameters<typeof createZone>[1] }) =>
      createZone(farmId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['agritech-zones', variables.farmId] });
    },
  });
};