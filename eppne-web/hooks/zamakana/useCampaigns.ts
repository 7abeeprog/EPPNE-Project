// hooks/zamakana/useCampaigns.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getCampaigns, getCampaign, createCampaign } from '@/services/zamakana';

export const useCampaigns = (params?: { status?: string; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['zamakana-campaigns', params],
    queryFn: () => getCampaigns(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useCampaign = (id: number) => {
  return useQuery({
    queryKey: ['zamakana-campaign', id],
    queryFn: () => getCampaign(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateCampaign = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof createCampaign>[0]) => createCampaign(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zamakana-campaigns'] });
    },
  });
};