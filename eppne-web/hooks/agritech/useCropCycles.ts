// hooks/agritech/useCropCycles.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getCropCycles } from '@/services/agritech';
import { AgritechService } from '@/services/agritech';

export const useCropCycles = (zoneId: number) => {
  return useQuery({
    queryKey: ['agritech-crop-cycles', zoneId],
    queryFn: () => getCropCycles(zoneId).then((res) => res.data),
    enabled: !!zoneId,
    staleTime: 2 * 60 * 1000,
  });
};

export const useStartCropCycle = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ zoneId, data }: { zoneId: number; data: Parameters<typeof AgritechService.startCropCycle>[1] }) =>
      AgritechService.startCropCycle(zoneId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['agritech-crop-cycles', variables.zoneId] });
      queryClient.invalidateQueries({ queryKey: ['agritech-stats'] });
    },
  });
};