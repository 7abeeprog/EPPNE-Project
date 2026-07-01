// hooks/agritech/useSensors.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getSoilReadings, recordSoilReading, getWeatherAlerts } from '@/services/agritech';

export const useSoilReadings = (zoneId: number, params?: { limit?: number }) => {
  return useQuery({
    queryKey: ['agritech-soil-readings', zoneId, params],
    queryFn: () => getSoilReadings(zoneId, params).then((res) => res.data),
    enabled: !!zoneId,
    staleTime: 30 * 1000,
    refetchInterval: 30000,
  });
};

export const useRecordSoilReading = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof recordSoilReading>[0]) => recordSoilReading(data),
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