// hooks/invitations/useLeads.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { InvitationsService } from '@/services/invitations';

export const useLeads = (params?: { status?: string; source?: string; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['invitations-leads', params],
    queryFn: () => InvitationsService.listLeads(params as any),
    staleTime: 2 * 60 * 1000,
  });
};

export const useLead = (id: number) => {
  return useQuery({
    queryKey: ['invitations-lead', id],
    queryFn: () => InvitationsService.getLead(id),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateLead = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof InvitationsService.createLead>[0]; idempotencyKey?: string }) =>
      InvitationsService.createLead(data, { 'Idempotency-Key': idempotencyKey }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations-leads'] });
      queryClient.invalidateQueries({ queryKey: ['invitations-stats'] });
    },
  });
};

export const useUpdateLead = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof InvitationsService.updateLead>[1] }) =>
      InvitationsService.updateLead(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['invitations-lead', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['invitations-leads'] });
    },
  });
};

export const useDeleteLead = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => InvitationsService.deleteLead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations-leads'] });
      queryClient.invalidateQueries({ queryKey: ['invitations-stats'] });
    },
  });
};