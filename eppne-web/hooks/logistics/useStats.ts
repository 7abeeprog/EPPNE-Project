// hooks/logistics/useStats.ts
import { useQuery } from '@tanstack/react-query';
import { LogisticsService } from '@/services/logistics';

export const useLogisticsStats = () => {
  return useQuery({
    queryKey: ['logistics-stats'],
    queryFn: () => LogisticsService.getLogisticsStats(),
    staleTime: 60 * 1000,
  });
};
