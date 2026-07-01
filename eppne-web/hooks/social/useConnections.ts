// hooks/social/useConnections.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getConnections, requestConnection, acceptConnection, rejectConnection } from '@/services/social';

export const useConnections = () => {
  return useQuery({
    queryKey: ['social-connections'],
    queryFn: () => getConnections().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useRequestConnection = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof requestConnection>[0]) => requestConnection(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-connections'] });
    },
  });
};

export const useAcceptConnection = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (connectionId: number) => acceptConnection(connectionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-connections'] });
    },
  });
};

export const useRejectConnection = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (connectionId: number) => rejectConnection(connectionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-connections'] });
    },
  });
};