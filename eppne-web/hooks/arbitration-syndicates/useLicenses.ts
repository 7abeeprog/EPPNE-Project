// hooks/arbitration-syndicates/useLicenses.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMyLicenses, issueLicense } from '@/services/arbitration-syndicates';

export const useMyLicenses = () => {
  return useQuery({
    queryKey: ['arbitration-licenses'],
    queryFn: () => getMyLicenses().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useIssueLicense = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof issueLicense>[0]; idempotencyKey?: string }) =>
      issueLicense(data, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['arbitration-licenses'] });
    },
  });
};