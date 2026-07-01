// hooks/realestate/usePropertyOwnerships.ts
import { useQuery } from '@tanstack/react-query';
import { getPropertyOwnerships } from '@/services/realestate';

export const usePropertyOwnerships = (propertyId: number) => {
  return useQuery({
    queryKey: ['realestate-property-ownerships', propertyId],
    queryFn: () => getPropertyOwnerships(propertyId).then((res) => res.data),
    enabled: !!propertyId,
    staleTime: 2 * 60 * 1000,
  });
};