// hooks/insurance/usePensions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMyPensions, getPension, createPension, updatePension, suspendPension } from '@/services/insurance';

export const useMyPensions = () => {
  return useQuery({
    queryKey: ['insurance-pensions'],
    queryFn: () => getMyPensions().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const usePension = (id: number) => {
  return useQuery({
    queryKey: ['insurance-pension', id],
    queryFn: () => getPension(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreatePension = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof createPension>[0]) => createPension(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['insurance-pensions'] });
    },
  });
};

export const useUpdatePension = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updatePension>[1] }) =>
      updatePension(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['insurance-pension', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['insurance-pensions'] });
    },
  });
};

export const useSuspendPension = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => suspendPension(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['insurance-pension', id] });
      queryClient.invalidateQueries({ queryKey: ['insurance-pensions'] });
    },
  });
};