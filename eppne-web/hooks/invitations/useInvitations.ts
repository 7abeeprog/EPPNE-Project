// hooks/invitations/useInvitations.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { InvitationsService } from '@/services/invitations';

export const useInvitations = (params?: { status?: string; campaign_type?: string; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['invitations', params],
    queryFn: () => InvitationsService.listInvitations(params as any),
    staleTime: 2 * 60 * 1000,
  });
};

export const useInvitation = (id: number) => {
  return useQuery({
    queryKey: ['invitations-invitation', id],
    queryFn: () => InvitationsService.getInvitation(id),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateInvitation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof InvitationsService.createInvitation>[0]; idempotencyKey?: string }) =>
      InvitationsService.createInvitation(data, { 'Idempotency-Key': idempotencyKey }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations'] });
      queryClient.invalidateQueries({ queryKey: ['invitations-stats'] });
    },
  });
};

export const useUpdateInvitation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof InvitationsService.updateInvitation>[1] }) =>
      InvitationsService.updateInvitation(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['invitations-invitation', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['invitations'] });
    },
  });
};

export const useDeleteInvitation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => InvitationsService.deleteInvitation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations'] });
      queryClient.invalidateQueries({ queryKey: ['invitations-stats'] });
    },
  });
};

export const useAcceptInvitation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ invitationId, data, idempotencyKey }: { invitationId: number; data: { email?: string; password?: string; name?: string; phone?: string }; idempotencyKey?: string }) =>
      InvitationsService.acceptInvitation(invitationId, data, { 'Idempotency-Key': idempotencyKey }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['invitations-invitation', variables.invitationId] });
      queryClient.invalidateQueries({ queryKey: ['invitations'] });
      queryClient.invalidateQueries({ queryKey: ['invitations-leads'] });
      queryClient.invalidateQueries({ queryKey: ['invitations-stats'] });
    },
  });
};