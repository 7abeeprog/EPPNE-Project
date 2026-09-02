// hooks/invitations/useStats.ts
import { useQuery } from '@tanstack/react-query';
import { InvitationsService } from '@/services/invitations';

export const useInvitationStats = () => {
  return useQuery({
    queryKey: ['invitations-stats'],
    queryFn: () => InvitationsService.getInvitationStats(),
    refetchInterval: 30000,
    staleTime: 10000,
  });
};