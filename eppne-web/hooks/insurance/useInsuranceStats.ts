// hooks/insurance/useInsuranceStats.ts
import { useQuery } from '@tanstack/react-query';
import { getInsuranceStats } from '@/services/insurance';

export const useInsuranceStats = () => {
  return useQuery({
    queryKey: ['insurance-stats'],
    queryFn: () => getInsuranceStats().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};