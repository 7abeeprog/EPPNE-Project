// hooks/logistics/useForecast.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { generateForecast, getForecasts } from '@/services/logistics';

export const useForecasts = (params?: { product_id?: number; period?: string; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['logistics-forecasts', params],
    queryFn: () => getForecasts(params).then((res) => res.data),
    staleTime: 5 * 60 * 1000,
  });
};

export const useGenerateForecast = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ productId, period, idempotencyKey }: { productId: number; period?: string; idempotencyKey?: string }) =>
      generateForecast(productId, period, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistics-forecasts'] });
    },
  });
};