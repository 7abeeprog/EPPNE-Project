// hooks/tenders-auctions/useTenders.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { TendersAuctionsService } from '@/services/tenders-auctions';

export const useTenders = (params?: { status?: string; entity_id?: number; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['tenders', params],
    queryFn: () => TendersAuctionsService.listTenders({
      status_filter: params?.status,
      skip: params?.skip,
      limit: params?.limit,
    }),
    staleTime: 2 * 60 * 1000,
  });
};

export const useTender = (id: number) => {
  return useQuery({
    queryKey: ['tender', id],
    queryFn: () => TendersAuctionsService.getTender(id),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateTender = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof TendersAuctionsService.createTender>[0]) => TendersAuctionsService.createTender(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenders'] });
    },
  });
};

export const useOpenTender = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => TendersAuctionsService.openTender(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['tender', id] });
      queryClient.invalidateQueries({ queryKey: ['tenders'] });
    },
  });
};

export const useUpdateTender = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof TendersAuctionsService.updateTender>[1] }) =>
      TendersAuctionsService.updateTender(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tender', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['tenders'] });
    },
  });
};