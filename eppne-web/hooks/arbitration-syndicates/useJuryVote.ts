// hooks/arbitration-syndicates/useJuryVote.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { castJuryVote } from '@/services/arbitration-syndicates';

export const useJuryVote = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ caseId, data, idempotencyKey }: { caseId: number; data: { vote: boolean; justification?: string }; idempotencyKey?: string }) =>
      castJuryVote(caseId, data, idempotencyKey),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['arbitration-case', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['arbitration-cases'] });
    },
  });
};