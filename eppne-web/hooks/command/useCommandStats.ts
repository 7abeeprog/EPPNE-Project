// hooks/command/useCommandStats.ts
import { useQuery } from '@tanstack/react-query';
import { getCommandStats } from '@/services/command';
import { CommandService } from '@/services/command';

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
    queryFn: () => CommandService.listMetrics({ period }),
    refetchInterval: 60000,
    staleTime: 30000,
  });
};