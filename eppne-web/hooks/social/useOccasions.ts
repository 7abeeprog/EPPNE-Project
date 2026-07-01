// hooks/social/useOccasions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getOccasions, getUpcomingOccasions, createOccasion, deleteOccasion } from '@/services/social';

export const useOccasions = () => {
  return useQuery({
    queryKey: ['social-occasions'],
    queryFn: () => getOccasions().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useUpcomingOccasions = (daysAhead: number = 30) => {
  return useQuery({
    queryKey: ['social-upcoming-occasions', daysAhead],
    queryFn: () => getUpcomingOccasions({ days_ahead: daysAhead }).then((res) => res.data),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 60000,
  });
};

export const useCreateOccasion = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof createOccasion>[0]) => createOccasion(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-occasions'] });
      queryClient.invalidateQueries({ queryKey: ['social-upcoming-occasions'] });
    },
  });
};

export const useDeleteOccasion = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteOccasion(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-occasions'] });
      queryClient.invalidateQueries({ queryKey: ['social-upcoming-occasions'] });
    },
  });
};