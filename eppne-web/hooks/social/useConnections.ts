// hooks/social/useConnections.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { acceptConnection, rejectConnection } from '@/services/social';
import { SocialService } from '@/services/social';

export const useConnections = () => {
  return useQuery({
    queryKey: ['social-connections'],
    queryFn: () => SocialService.getMyConnections(),
    staleTime: 2 * 60 * 1000,
  });
};

export const useRequestConnection = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof SocialService.requestConnection>[0]) => SocialService.requestConnection(data),
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