// hooks/tourism-sports/useMyTickets.ts
import { useQuery } from '@tanstack/react-query';
import { getMyTickets } from '@/services/tourism-sports';

export const useMyTickets = () => {
  return useQuery({
    queryKey: ['tourism-tickets'],
    queryFn: () => getMyTickets().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};