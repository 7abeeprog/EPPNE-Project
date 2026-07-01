// hooks/insurance/useClaims.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMyClaims, getClaim, submitClaim, reviewClaim, updateClaim } from '@/services/insurance';

export const useMyClaims = (params?: { status?: string }) => {
  return useQuery({
    queryKey: ['insurance-claims', params],
    queryFn: () => getMyClaims(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useClaim = (id: number) => {
  return useQuery({
    queryKey: ['insurance-claim', id],
    queryFn: () => getClaim(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useSubmitClaim = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof submitClaim>[0]; idempotencyKey?: string }) =>
      submitClaim(data, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['insurance-claims'] });
    },
  });
};

export const useReviewClaim = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ claimId, data, idempotencyKey }: { claimId: number; data: Parameters<typeof reviewClaim>[1]; idempotencyKey?: string }) =>
      reviewClaim(claimId, data, idempotencyKey),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['insurance-claim', variables.claimId] });
      queryClient.invalidateQueries({ queryKey: ['insurance-claims'] });
    },
  });
};

export const useUpdateClaim = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateClaim>[1] }) =>
      updateClaim(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['insurance-claim', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['insurance-claims'] });
    },
  });
};