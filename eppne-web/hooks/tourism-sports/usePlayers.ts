// hooks/tourism-sports/usePlayers.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getPlayers } from '@/services/tourism-sports';
import { TourismSportsService } from '@/services/tourism-sports';

export const usePlayers = (params?: { club_id?: number; sport_category?: string }) => {
  return useQuery({
    queryKey: ['sports-players', params],
    queryFn: () => getPlayers(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const usePlayer = (id: number) => {
  return useQuery({
    queryKey: ['sports-player', id],
    queryFn: () => TourismSportsService.getPlayer(id),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreatePlayerProfile = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof TourismSportsService.createPlayerProfile>[0]) => TourismSportsService.createPlayerProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sports-players'] });
    },
  });
};