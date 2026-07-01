// hooks/transport/useTransportStats.ts
import { useQuery } from '@tanstack/react-query';
import { getTransportStats } from '@/services/transport';

export const useTransportStats = () => {
  return useQuery({
    queryKey: ['transport-stats'],
    queryFn: () => getTransportStats().then((res) => res.data),
    refetchInterval: 30000,
    staleTime: 10000,
  });
};