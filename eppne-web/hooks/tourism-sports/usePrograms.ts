// hooks/tourism-sports/usePrograms.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getPrograms } from '@/services/tourism-sports';
import { TourismSportsService } from '@/services/tourism-sports';

export const usePrograms = () => {
  return useQuery({
    queryKey: ['tourism-programs'],
    queryFn: () => getPrograms().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useProgram = (id: number) => {
  return useQuery({
    queryKey: ['tourism-program', id],
    queryFn: () => TourismSportsService.getProgram(id),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useBookProgram = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ programId, idempotencyKey }: { programId: number; idempotencyKey?: string }) =>
      TourismSportsService.bookProgram(programId, { 'Idempotency-Key': idempotencyKey }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tourism-programs'] });
      queryClient.invalidateQueries({ queryKey: ['tourism-stats'] });
    },
  });
};