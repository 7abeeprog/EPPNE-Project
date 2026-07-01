// hooks/realestate/useMyOwnerships.ts
import { useQuery } from '@tanstack/react-query';
import { getMyOwnerships } from '@/services/realestate';

export const useMyOwnerships = () => {
  return useQuery({
    queryKey: ['realestate-my-ownerships'],
    queryFn: () => getMyOwnerships().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};