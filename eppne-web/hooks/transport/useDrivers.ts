// hooks/transport/useDrivers.ts
import { useQuery } from '@tanstack/react-query';
import { TransportService } from '@/services/transport';

// بدون كيان/دور "سائق" منفصل [قرار مستخدم، جلسة
// transport-vehicles-drivers-feature-build، 2026-09-04]: مجرد سرد
// للمستخدمين النشطين بنفس التينانت — create_trip أصلًا بتقبل أي user_id
// كـdriver_id بلا فحص دور.
export const useDrivers = (params?: { skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['transport-drivers', params],
    queryFn: () => TransportService.listDrivers(params),
    staleTime: 5 * 60 * 1000,
  });
};
