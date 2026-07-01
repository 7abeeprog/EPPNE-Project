// hooks/invitations/useCampaigns.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getCampaigns, getCampaign, createCampaign, updateCampaign, deleteCampaign } from '@/services/invitations';

export const useCampaigns = (params?: { status?: string; campaign_type?: string; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['invitations-campaigns', params],
    queryFn: () => getCampaigns(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useCampaign = (id: number) => {
  return useQuery({
    queryKey: ['invitations-campaign', id],
    queryFn: () => getCampaign(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateCampaign = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof createCampaign>[0]; idempotencyKey?: string }) =>
      createCampaign(data, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations-campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['invitations-stats'] });
    },
  });
};

export const useUpdateCampaign = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateCampaign>[1] }) =>
      updateCampaign(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['invitations-campaign', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['invitations-campaigns'] });
    },
  });
};

export const useDeleteCampaign = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteCampaign(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations-campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['invitations-stats'] });
    },
  });
};