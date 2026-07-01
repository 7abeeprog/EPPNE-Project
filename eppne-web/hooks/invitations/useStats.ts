// hooks/invitations/useStats.ts
import { useQuery } from '@tanstack/react-query';
import { getInvitationStats } from '@/services/invitations';

export const useInvitationStats = () => {
  return useQuery({
    queryKey: ['invitations-stats'],
    queryFn: () => getInvitationStats().then((res) => res.data),
    refetchInterval: 30000,
    staleTime: 10000,
  });
};