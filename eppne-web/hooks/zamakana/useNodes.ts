// hooks/zamakana/useNodes.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getNodes } from '@/services/zamakana';
import { ZamakanaService } from '@/services/zamakana';

export const useNodes = (params?: { node_type?: string; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['zamakana-nodes', params],
    queryFn: () => getNodes(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useNode = (id: number) => {
  return useQuery({
    queryKey: ['zamakana-node', id],
    queryFn: () => ZamakanaService.getNode(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateNode = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof ZamakanaService.createNode>[0]) => ZamakanaService.createNode(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zamakana-nodes'] });
      queryClient.invalidateQueries({ queryKey: ['zamakana-graph'] });
    },
  });
};

export const useUpdateNode = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof ZamakanaService.updateNode>[1] }) =>
      ZamakanaService.updateNode(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['zamakana-node', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['zamakana-nodes'] });
      queryClient.invalidateQueries({ queryKey: ['zamakana-graph'] });
    },
  });
};

export const useDeleteNode = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => ZamakanaService.deleteNode(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zamakana-nodes'] });
      queryClient.invalidateQueries({ queryKey: ['zamakana-graph'] });
    },
  });
};