// hooks/logistics/useInventory.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getInventory, getInventoryItem } from '@/services/logistics';
import { LogisticsService } from '@/services/logistics';

export const useInventory = (params?: { warehouse_id?: number; status?: string; product_category?: string; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['logistics-inventory', params],
    queryFn: () => getInventory(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useInventoryItem = (id: number) => {
  return useQuery({
    queryKey: ['logistics-inventory-item', id],
    queryFn: () => getInventoryItem(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useInventoryTransactions = (itemId: number, params?: { skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['logistics-inventory-transactions', itemId, params],
    queryFn: () => LogisticsService.getInventoryTransactions(itemId, params).then((res) => res.data),
    enabled: !!itemId,
    staleTime: 2 * 60 * 1000,
  });
};

export const useReceiveInventory = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof LogisticsService.receiveInventory>[0]; idempotencyKey?: string }) =>
      LogisticsService.receiveInventory(data, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistics-inventory'] });
      queryClient.invalidateQueries({ queryKey: ['logistics-stats'] });
    },
  });
};

export const useIssueInventory = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, idempotencyKey }: { data: Parameters<typeof LogisticsService.issueInventory>[0]; idempotencyKey?: string }) =>
      LogisticsService.issueInventory(data, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logistics-inventory'] });
      queryClient.invalidateQueries({ queryKey: ['logistics-stats'] });
    },
  });
};

export const useAdjustInventory = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ itemId, data, idempotencyKey }: { itemId: number; data: Parameters<typeof LogisticsService.adjustInventory>[1]; idempotencyKey?: string }) =>
      LogisticsService.adjustInventory(itemId, data, idempotencyKey),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['logistics-inventory-item', variables.itemId] });
      queryClient.invalidateQueries({ queryKey: ['logistics-inventory'] });
      queryClient.invalidateQueries({ queryKey: ['logistics-stats'] });
    },
  });
};

export const useLowStock = (params?: { warehouse_id?: number }) => {
  return useQuery({
    queryKey: ['logistics-low-stock', params],
    queryFn: () => LogisticsService.getLowStock(params).then((res) => res.data),
    staleTime: 1 * 60 * 1000,
    refetchInterval: 60000,
  });
};

export const useExpired = () => {
  return useQuery({
    queryKey: ['logistics-expired'],
    queryFn: () => LogisticsService.getExpired().then((res) => res.data),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 300000,
  });
};