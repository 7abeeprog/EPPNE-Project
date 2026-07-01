// hooks/transport/useDeliveries.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getDeliveries,
  getMyDeliveries,
  createDelivery,
  payDelivery,
  completeDelivery,
  assignDeliveryToTrip,
} from '@/services/transport';
import type { DeliveryFormData } from '@/types/transport';

export const useDeliveries = (params?: { status?: string; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['transport-deliveries', params],
    queryFn: () => getDeliveries(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
    refetchInterval: (data) => {
      if (data?.some((d) => d.status === 'ASSIGNED' || d.status === 'PICKED_UP')) {
        return 15000;
      }
      return false;
    },
  });
};

export const useMyDeliveries = () => {
  return useQuery({
    queryKey: ['transport-my-deliveries'],
    queryFn: () => getMyDeliveries().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
    refetchInterval: (data) => {
      if (data?.some((d) => d.status === 'ASSIGNED' || d.status === 'PICKED_UP')) {
        return 15000;
      }
      return false;
    },
  });
};

export const useCreateDelivery = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: DeliveryFormData) => createDelivery(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-deliveries'] });
      queryClient.invalidateQueries({ queryKey: ['transport-my-deliveries'] });
    },
  });
};

export const usePayDelivery = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, idempotencyKey }: { taskId: number; idempotencyKey?: string }) =>
      payDelivery(taskId, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-deliveries'] });
      queryClient.invalidateQueries({ queryKey: ['transport-my-deliveries'] });
      queryClient.invalidateQueries({ queryKey: ['transport-stats'] });
    },
  });
};

export const useCompleteDelivery = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, proofHash }: { taskId: number; proofHash: string }) =>
      completeDelivery(taskId, proofHash),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-deliveries'] });
      queryClient.invalidateQueries({ queryKey: ['transport-my-deliveries'] });
    },
  });
};

export const useAssignDeliveryToTrip = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, tripId }: { taskId: number; tripId: number }) =>
      assignDeliveryToTrip(taskId, tripId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-deliveries'] });
      queryClient.invalidateQueries({ queryKey: ['transport-my-deliveries'] });
    },
  });
};