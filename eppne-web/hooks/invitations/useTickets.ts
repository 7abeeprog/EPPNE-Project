// hooks/invitations/useTickets.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTickets, getTicket, createTicket, updateTicket, getTicketComments, createTicketComment } from '@/services/invitations';

export const useTickets = (params?: { status?: string; assigned_to?: number; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['invitations-tickets', params],
    queryFn: () => getTickets(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useTicket = (id: number) => {
  return useQuery({
    queryKey: ['invitations-ticket', id],
    queryFn: () => getTicket(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateTicket = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof createTicket>[0]; idempotencyKey?: string }) =>
      createTicket(data, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations-tickets'] });
      queryClient.invalidateQueries({ queryKey: ['invitations-stats'] });
    },
  });
};

export const useUpdateTicket = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateTicket>[1] }) =>
      updateTicket(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['invitations-ticket', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['invitations-tickets'] });
    },
  });
};

export const useTicketComments = (ticketId: number) => {
  return useQuery({
    queryKey: ['invitations-ticket-comments', ticketId],
    queryFn: () => getTicketComments(ticketId).then((res) => res.data),
    enabled: !!ticketId,
    staleTime: 1 * 60 * 1000,
  });
};

export const useCreateTicketComment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ ticketId, data, idempotencyKey }: { ticketId: number; data: { comment: string; is_internal?: boolean }; idempotencyKey?: string }) =>
      createTicketComment(ticketId, data, idempotencyKey),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['invitations-ticket-comments', variables.ticketId] });
    },
  });
};