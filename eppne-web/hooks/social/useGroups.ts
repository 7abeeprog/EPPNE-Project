// hooks/social/useGroups.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getGroups, getGroup, createGroup, joinGroup, leaveGroup, getGroupMembers } from '@/services/social';

export const useGroups = (params?: { privacy?: string; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['social-groups', params],
    queryFn: () => getGroups(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useGroup = (id: number) => {
  return useQuery({
    queryKey: ['social-group', id],
    queryFn: () => getGroup(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateGroup = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof createGroup>[0]) => createGroup(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-groups'] });
    },
  });
};

export const useJoinGroup = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (groupId: number) => joinGroup(groupId),
    onSuccess: (_, groupId) => {
      queryClient.invalidateQueries({ queryKey: ['social-group', groupId] });
      queryClient.invalidateQueries({ queryKey: ['social-groups'] });
    },
  });
};

export const useLeaveGroup = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (groupId: number) => leaveGroup(groupId),
    onSuccess: (_, groupId) => {
      queryClient.invalidateQueries({ queryKey: ['social-group', groupId] });
      queryClient.invalidateQueries({ queryKey: ['social-groups'] });
    },
  });
};

export const useGroupMembers = (groupId: number, params?: { skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['social-group-members', groupId, params],
    queryFn: () => getGroupMembers(groupId, params).then((res) => res.data),
    enabled: !!groupId,
    staleTime: 2 * 60 * 1000,
  });
};