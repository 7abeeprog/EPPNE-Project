// hooks/agritech/useSensors.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getWeatherAlerts } from '@/services/agritech';
import { AgritechService } from '@/services/agritech';

export const useSoilReadings = (zoneId: number, params?: { limit?: number }) => {
  return useQuery({
    queryKey: ['agritech-soil-readings', zoneId, params],
    queryFn: () => AgritechService.getSoilReadings(zoneId, params).then((res) => res.data),
    enabled: !!zoneId,
    staleTime: 30 * 1000,
    refetchInterval: 30000,
  });
};

export const useRecordSoilReading = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof AgritechService.recordSoilReading>[0]) => AgritechService.recordSoilReading(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['agritech-soil-readings', variables.zone_id] });
    },
  });
};

export const useWeatherAlerts = () => {
  return useQuery({
    queryKey: ['agritech-weather-alerts'],
    queryFn: () => getWeatherAlerts().then((res) => res.data),
    staleTime: 30 * 1000,
    refetchInterval: 60000,
  });
};