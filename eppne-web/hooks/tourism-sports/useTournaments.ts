// hooks/tourism-sports/useTournaments.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTournaments, getTournament } from '@/services/tourism-sports';
import { TourismSportsService } from '@/services/tourism-sports';

export const useTournaments = () => {
  return useQuery({
    queryKey: ['sports-tournaments'],
    queryFn: () => getTournaments().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useTournament = (id: number) => {
  return useQuery({
    queryKey: ['sports-tournament', id],
    queryFn: () => getTournament(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateTournament = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof TourismSportsService.createTournament>[0]) => TourismSportsService.createTournament(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sports-tournaments'] });
    },
  });
};