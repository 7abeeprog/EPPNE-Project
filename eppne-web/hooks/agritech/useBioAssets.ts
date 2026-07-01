// hooks/agritech/useBioAssets.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getBioCohorts, createBioCohort, registerBioYield } from '@/services/agritech';

export const useBioCohorts = (zoneId: number) => {
  return useQuery({
    queryKey: ['agritech-bio-cohorts', zoneId],
    queryFn: () => getBioCohorts(zoneId).then((res) => res.data),
    enabled: !!zoneId,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateBioCohort = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ zoneId, data }: { zoneId: number; data: Parameters<typeof createBioCohort>[1] }) =>
      createBioCohort(zoneId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['agritech-bio-cohorts', variables.zoneId] });
      queryClient.invalidateQueries({ queryKey: ['agritech-stats'] });
    },
  });
};

export const useRegisterBioYield = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      cohortId,
      data,
      idempotencyKey,
    }: {
      cohortId: number;
      data: Parameters<typeof registerBioYield>[1];
      idempotencyKey?: string;
    }) => registerBioYield(cohortId, data, idempotencyKey),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['agritech-bio-yields', variables.cohortId] });
      queryClient.invalidateQueries({ queryKey: ['agritech-stats'] });
    },
  });
};