// hooks/arbitration-syndicates/useCases.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMyCases, getCase, createCase } from '@/services/arbitration-syndicates';

export const useMyCases = () => {
  return useQuery({
    queryKey: ['arbitration-cases'],
    queryFn: () => getMyCases().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useCase = (id: number) => {
  return useQuery({
    queryKey: ['arbitration-case', id],
    queryFn: () => getCase(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateCase = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof createCase>[0]; idempotencyKey?: string }) =>
      createCase(data, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['arbitration-cases'] });
    },
  });
};