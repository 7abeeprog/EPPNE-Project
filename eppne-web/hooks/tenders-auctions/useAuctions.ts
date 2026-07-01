// hooks/tenders-auctions/useAuctions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAuctions, getAuction, createAuction, startAuction, closeAuction } from '@/services/tenders-auctions';

export const useAuctions = (params?: { status?: string; asset_type?: string; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['auctions', params],
    queryFn: () => getAuctions(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useAuction = (id: number) => {
  return useQuery({
    queryKey: ['auction', id],
    queryFn: () => getAuction(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
    refetchInterval: (data) => {
      if (data?.status === 'LIVE') return 5000;
      return false;
    },
  });
};

export const useCreateAuction = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof createAuction>[0]) => createAuction(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auctions'] });
    },
  });
};

export const useStartAuction = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => startAuction(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['auction', id] });
      queryClient.invalidateQueries({ queryKey: ['auctions'] });
    },
  });
};

export const useCloseAuction = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => closeAuction(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['auction', id] });
      queryClient.invalidateQueries({ queryKey: ['auctions'] });
    },
  });
};