// hooks/insurance/useClaims.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { InsuranceService } from '@/services/insurance';

export const useMyClaims = (params?: { status?: string }) => {
  return useQuery({
    queryKey: ['insurance-claims', params],
    queryFn: () => InsuranceService.getMyClaims(params as any),
    staleTime: 2 * 60 * 1000,
  });
};

export const useClaim = (id: number) => {
  return useQuery({
    queryKey: ['insurance-claim', id],
    queryFn: () => InsuranceService.getClaim(id),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useSubmitClaim = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof InsuranceService.submitClaim>[0]; idempotencyKey?: string }) =>
      InsuranceService.submitClaim(data, { 'Idempotency-Key': idempotencyKey }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['insurance-claims'] });
    },
  });
};

export const useReviewClaim = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ claimId, data, idempotencyKey }: { claimId: number; data: Parameters<typeof InsuranceService.reviewClaim>[1]; idempotencyKey?: string }) =>
      InsuranceService.reviewClaim(claimId, data, { 'Idempotency-Key': idempotencyKey }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['insurance-claim', variables.claimId] });
      queryClient.invalidateQueries({ queryKey: ['insurance-claims'] });
    },
  });
};

export const useUpdateClaim = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof InsuranceService.updateClaim>[1] }) =>
      InsuranceService.updateClaim(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['insurance-claim', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['insurance-claims'] });
    },
  });
};