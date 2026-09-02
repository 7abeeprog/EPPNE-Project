// hooks/transport/useDeliveries.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getDeliveries,
  getMyDeliveries,
} from '@/services/transport';
import { TransportService } from '@/services/transport';
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
    mutationFn: (data: DeliveryFormData) => TransportService.createDelivery(data),
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
      TransportService.payDelivery(taskId, { 'Idempotency-Key': idempotencyKey }),
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
      TransportService.completeDelivery(taskId, { proof_hash: proofHash }),
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
      TransportService.assignDeliveryToTrip(taskId, tripId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transport-deliveries'] });
      queryClient.invalidateQueries({ queryKey: ['transport-my-deliveries'] });
    },
  });
};