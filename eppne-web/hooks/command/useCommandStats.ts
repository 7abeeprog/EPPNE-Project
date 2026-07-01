// hooks/command/useCommandStats.ts
import { useQuery } from '@tanstack/react-query';
import { getCommandStats, getDashboardMetrics } from '@/services/command';

export const useCommandStats = () => {
  return useQuery({
    queryKey: ['command-stats'],
    queryFn: () => getCommandStats().then((res) => res.data),
    refetchInterval: 30000,
    staleTime: 10000,
  });
};

export const useDashboardMetrics = (period?: string) => {
  return useQuery({
    queryKey: ['command-metrics', period],
    queryFn: () => getDashboardMetrics({ period }).then((res) => res.data),
    refetchInterval: 60000,
    staleTime: 30000,
  });
};