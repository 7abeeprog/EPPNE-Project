// hooks/tourism-sports/useMatches.ts
import { useQuery } from '@tanstack/react-query';
import { getMatches } from '@/services/tourism-sports';

export const useMatches = (params?: { tournament_id?: number; status?: string }) => {
  return useQuery({
    queryKey: ['sports-matches', params],
    queryFn: () => getMatches(params).then((res) => res.data),
    staleTime: 1 * 60 * 1000,
    refetchInterval: (data) => {
      if (data?.some((m) => m.status === 'LIVE')) return 10000;
      return false;
    },
  });
};