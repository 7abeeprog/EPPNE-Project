// hooks/social/useContracts.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getContracts } from '@/services/social';
import { SocialService } from '@/services/social';

export const useContracts = (params?: { status?: string; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['social-contracts', params],
    queryFn: () => getContracts(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useContract = (id: number) => {
  return useQuery({
    queryKey: ['social-contract', id],
    queryFn: () => SocialService.getContract(id),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateContract = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof SocialService.createContract>[0]) => SocialService.createContract(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-contracts'] });
    },
  });
};

export const useSignContract = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ contractId, data, idempotencyKey }: { contractId: number; data: { digital_signature_hash: string }; idempotencyKey?: string }) =>
      SocialService.signContract(contractId, { contract_id: contractId, ...data }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['social-contract', variables.contractId] });
      queryClient.invalidateQueries({ queryKey: ['social-contracts'] });
    },
  });
};