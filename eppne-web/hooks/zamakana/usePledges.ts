// hooks/zamakana/usePledges.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ZamakanaService } from '@/services/zamakana';

export const useCampaignPledges = (campaignId: number, params?: { status?: string }) => {
  return useQuery({
    queryKey: ['zamakana-pledges', campaignId, params],
    queryFn: () => ZamakanaService.getCampaignPledges(campaignId, params),
    enabled: !!campaignId,
    staleTime: 60 * 1000,
  });
};

export const usePledgeTime = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof ZamakanaService.pledgeTime>[0]) => ZamakanaService.pledgeTime(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['zamakana-pledges', variables.campaign_id] });
      queryClient.invalidateQueries({ queryKey: ['zamakana-campaign', variables.campaign_id] });
      queryClient.invalidateQueries({ queryKey: ['zamakana-campaigns'] });
    },
  });
};

export const useFulfillPledge = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ pledgeId, data }: { pledgeId: number; data: Parameters<typeof ZamakanaService.fulfillPledge>[1] }) =>
      ZamakanaService.fulfillPledge(pledgeId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zamakana-pledges'] });
    },
  });
};
