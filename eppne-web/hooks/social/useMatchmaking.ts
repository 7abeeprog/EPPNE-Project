// hooks/social/useMatchmaking.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMatchProfile, updateMatchProfile, getMatchSuggestions, getConnections, requestConnection, acceptConnection, rejectConnection } from '@/services/social';

export const useMatchProfile = () => {
  return useQuery({
    queryKey: ['social-match-profile'],
    queryFn: () => getMatchProfile().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useUpdateMatchProfile = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof updateMatchProfile>[0]) => updateMatchProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-match-profile'] });
    },
  });
};

export const useMatchSuggestions = (params?: { limit?: number }) => {
  return useQuery({
    queryKey: ['social-match-suggestions', params],
    queryFn: () => getMatchSuggestions(params).then((res) => res.data),
    staleTime: 5 * 60 * 1000,
  });
};

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
    mutationFn: (data: { target_user_id: number; connection_type: string }) => requestConnection(data),
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