// hooks/invitations/useInteractions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getLeadInteractions, createInteraction } from '@/services/invitations';

export const useLeadInteractions = (leadId: number, params?: { limit?: number }) => {
  return useQuery({
    queryKey: ['invitations-interactions', leadId, params],
    queryFn: () => getLeadInteractions(leadId, params).then((res) => res.data),
    enabled: !!leadId,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateInteraction = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ leadId, data, idempotencyKey }: { leadId: number; data: { interaction_type: string; title?: string; content: string; metadata?: Record<string, any> }; idempotencyKey?: string }) =>
      createInteraction(leadId, data, idempotencyKey),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['invitations-interactions', variables.leadId] });
    },
  });
};