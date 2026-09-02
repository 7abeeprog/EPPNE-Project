// hooks/command/useBrands.ts
import { useQuery } from '@tanstack/react-query';
import { CommandService } from '@/services/command';

export const useBrands = (params?: { skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['command-brands', params],
    queryFn: () => CommandService.listBrands(params),
    staleTime: 2 * 60 * 1000,
  });
};
