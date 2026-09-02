// hooks/tenders-auctions/useAuctions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { TendersAuctionsService } from '@/services/tenders-auctions';

export const useAuctions = (params?: { status?: string; asset_type?: string; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['auctions', params],
    queryFn: () => TendersAuctionsService.listAuctions({
      status_filter: params?.status,
      asset_type: params?.asset_type,
      skip: params?.skip,
      limit: params?.limit,
    }),
    staleTime: 2 * 60 * 1000,
  });
};

export const useAuction = (id: number) => {
  return useQuery({
    queryKey: ['auction', id],
    queryFn: () => TendersAuctionsService.getAuction(id),
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
    mutationFn: (data: Parameters<typeof TendersAuctionsService.createAuction>[0]) => TendersAuctionsService.createAuction(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auctions'] });
    },
  });
};

export const useStartAuction = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => TendersAuctionsService.startAuction(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['auction', id] });
      queryClient.invalidateQueries({ queryKey: ['auctions'] });
    },
  });
};

export const useCloseAuction = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => TendersAuctionsService.closeAuction(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['auction', id] });
      queryClient.invalidateQueries({ queryKey: ['auctions'] });
    },
  });
};