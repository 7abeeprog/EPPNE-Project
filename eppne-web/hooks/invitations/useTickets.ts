// hooks/invitations/useTickets.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { InvitationsService } from '@/services/invitations';

export const useTickets = (params?: { status?: string; assigned_to?: number; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['invitations-tickets', params],
    queryFn: () => InvitationsService.listTickets(params as any),
    staleTime: 2 * 60 * 1000,
  });
};

export const useTicket = (id: number) => {
  return useQuery({
    queryKey: ['invitations-ticket', id],
    queryFn: () => InvitationsService.getTicket(id),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateTicket = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof InvitationsService.createTicket>[0]; idempotencyKey?: string }) =>
      InvitationsService.createTicket(data, { 'Idempotency-Key': idempotencyKey }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations-tickets'] });
      queryClient.invalidateQueries({ queryKey: ['invitations-stats'] });
    },
  });
};

export const useUpdateTicket = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof InvitationsService.updateTicket>[1] }) =>
      InvitationsService.updateTicket(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['invitations-ticket', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['invitations-tickets'] });
    },
  });
};

export const useTicketComments = (ticketId: number) => {
  return useQuery({
    queryKey: ['invitations-ticket-comments', ticketId],
    queryFn: () => InvitationsService.getTicketComments(ticketId),
    enabled: !!ticketId,
    staleTime: 1 * 60 * 1000,
  });
};

export const useCreateTicketComment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ ticketId, data, idempotencyKey }: { ticketId: number; data: { comment: string; is_internal?: boolean }; idempotencyKey?: string }) =>
      InvitationsService.addTicketComment(ticketId, data as any, { 'Idempotency-Key': idempotencyKey }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['invitations-ticket-comments', variables.ticketId] });
    },
  });
};