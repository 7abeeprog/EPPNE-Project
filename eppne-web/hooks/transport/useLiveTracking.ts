// hooks/transport/useLiveTracking.ts
import { useQuery } from '@tanstack/react-query';
import { getVehicleLocation } from '@/services/transport';
import { useTransportStore } from '@/store/transportStore';

export const useLiveTracking = (vehicleId: number, enabled: boolean = true) => {
  const { isTrackingLive } = useTransportStore();

  return useQuery({
    queryKey: ['transport-vehicle-location', vehicleId],
    queryFn: () => getVehicleLocation(vehicleId).then((res) => res.data),
    enabled: enabled && isTrackingLive && !!vehicleId,
    refetchInterval: 3000,
    staleTime: 1000,
  });
};