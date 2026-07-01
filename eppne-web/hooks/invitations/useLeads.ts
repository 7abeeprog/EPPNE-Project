// hooks/invitations/useLeads.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getLeads, getLead, createLead, updateLead, deleteLead } from '@/services/invitations';

export const useLeads = (params?: { status?: string; source?: string; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['invitations-leads', params],
    queryFn: () => getLeads(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useLead = (id: number) => {
  return useQuery({
    queryKey: ['invitations-lead', id],
    queryFn: () => getLead(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateLead = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof createLead>[0]; idempotencyKey?: string }) =>
      createLead(data, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations-leads'] });
      queryClient.invalidateQueries({ queryKey: ['invitations-stats'] });
    },
  });
};

export const useUpdateLead = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateLead>[1] }) =>
      updateLead(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['invitations-lead', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['invitations-leads'] });
    },
  });
};

export const useDeleteLead = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteLead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations-leads'] });
      queryClient.invalidateQueries({ queryKey: ['invitations-stats'] });
    },
  });
};