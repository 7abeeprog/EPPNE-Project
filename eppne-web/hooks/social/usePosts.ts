// hooks/social/usePosts.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { SocialService } from '@/services/social';

export const useFeed = (params?: { skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['social-feed', params],
    queryFn: () => SocialService.getFeed(params),
    staleTime: 30 * 1000,
    refetchInterval: 60000,
  });
};

export const usePost = (id: number) => {
  return useQuery({
    queryKey: ['social-post', id],
    queryFn: () => SocialService.getPost(id),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreatePost = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof SocialService.createPost>[0]) => SocialService.createPost(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-feed'] });
    },
  });
};

export const useLikePost = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ postId, idempotencyKey }: { postId: number; idempotencyKey?: string }) =>
      SocialService.likePost(postId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['social-post', variables.postId] });
      queryClient.invalidateQueries({ queryKey: ['social-feed'] });
    },
  });
};

export const useSharePost = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (postId: number) => SocialService.sharePost(postId),
    onSuccess: (_, postId) => {
      queryClient.invalidateQueries({ queryKey: ['social-post', postId] });
      queryClient.invalidateQueries({ queryKey: ['social-feed'] });
    },
  });
};