// hooks/tenders-auctions/useTenders.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTenders, getTender, createTender, openTender, updateTender } from '@/services/tenders-auctions';

export const useTenders = (params?: { status?: string; entity_id?: number; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['tenders', params],
    queryFn: () => getTenders(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useTender = (id: number) => {
  return useQuery({
    queryKey: ['tender', id],
    queryFn: () => getTender(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateTender = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof createTender>[0]) => createTender(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenders'] });
    },
  });
};

export const useOpenTender = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => openTender(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['tender', id] });
      queryClient.invalidateQueries({ queryKey: ['tenders'] });
    },
  });
};

export const useUpdateTender = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateTender>[1] }) =>
      updateTender(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tender', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['tenders'] });
    },
  });
};