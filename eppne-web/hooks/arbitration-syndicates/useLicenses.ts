// hooks/arbitration-syndicates/useLicenses.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArbitrationSyndicatesService } from '@/services/arbitration-syndicates';

export const useMyLicenses = () => {
  return useQuery({
    queryKey: ['arbitration-licenses'],
    queryFn: () => ArbitrationSyndicatesService.getMyLicenses().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useIssueLicense = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof ArbitrationSyndicatesService.issueLicense>[0]; idempotencyKey?: string }) =>
      ArbitrationSyndicatesService.issueLicense(data, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['arbitration-licenses'] });
    },
  });
};