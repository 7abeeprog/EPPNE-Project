// hooks/transport/useLiveTracking.ts
import { useQuery } from '@tanstack/react-query';
import { TransportService } from '@/services/transport';
import { useTransportStore } from '@/store/transportStore';

export const useLiveTracking = (vehicleId: number, enabled: boolean = true) => {
  const { isTrackingLive } = useTransportStore();

  return useQuery({
    queryKey: ['transport-vehicle-location', vehicleId],
    queryFn: () => TransportService.getVehicle(vehicleId).then((vehicle) => vehicle.current_location),
    enabled: enabled && isTrackingLive && !!vehicleId,
    refetchInterval: 3000,
    staleTime: 1000,
  });
};