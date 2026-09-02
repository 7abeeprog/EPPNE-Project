// hooks/social/useMatchmaking.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { acceptConnection, rejectConnection } from '@/services/social';
import { SocialService } from '@/services/social';

export const useMatchProfile = () => {
  return useQuery({
    queryKey: ['social-match-profile'],
    queryFn: () => SocialService.getMatchProfile(),
    staleTime: 2 * 60 * 1000,
  });
};

export const useUpdateMatchProfile = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof SocialService.setupMatchProfile>[0]) => SocialService.setupMatchProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-match-profile'] });
    },
  });
};

export const useMatchSuggestions = (params?: { limit?: number }) => {
  return useQuery({
    queryKey: ['social-match-suggestions', params],
    queryFn: () => SocialService.getMatchSuggestions(params),
    staleTime: 5 * 60 * 1000,
  });
};

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