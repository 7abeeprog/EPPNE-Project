// hooks/social/usePosts.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getFeed, getPost, createPost, likePost, sharePost } from '@/services/social';

export const useFeed = (params?: { skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['social-feed', params],
    queryFn: () => getFeed(params).then((res) => res.data),
    staleTime: 30 * 1000,
    refetchInterval: 60000,
  });
};

export const usePost = (id: number) => {
  return useQuery({
    queryKey: ['social-post', id],
    queryFn: () => getPost(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreatePost = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof createPost>[0]) => createPost(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-feed'] });
    },
  });
};

export const useLikePost = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ postId, idempotencyKey }: { postId: number; idempotencyKey?: string }) =>
      likePost(postId, idempotencyKey),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['social-post', variables.postId] });
      queryClient.invalidateQueries({ queryKey: ['social-feed'] });
    },
  });
};

export const useSharePost = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (postId: number) => sharePost(postId),
    onSuccess: (_, postId) => {
      queryClient.invalidateQueries({ queryKey: ['social-post', postId] });
      queryClient.invalidateQueries({ queryKey: ['social-feed'] });
    },
  });
};