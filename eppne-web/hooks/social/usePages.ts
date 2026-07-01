// hooks/social/usePages.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getPages, getPage, createPage, followPage, unfollowPage } from '@/services/social';

export const usePages = (params?: { skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['social-pages', params],
    queryFn: () => getPages(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const usePage = (id: number) => {
  return useQuery({
    queryKey: ['social-page', id],
    queryFn: () => getPage(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreatePage = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof createPage>[0]) => createPage(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-pages'] });
    },
  });
};

export const useFollowPage = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (pageId: number) => followPage(pageId),
    onSuccess: (_, pageId) => {
      queryClient.invalidateQueries({ queryKey: ['social-page', pageId] });
      queryClient.invalidateQueries({ queryKey: ['social-pages'] });
    },
  });
};

export const useUnfollowPage = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (pageId: number) => unfollowPage(pageId),
    onSuccess: (_, pageId) => {
      queryClient.invalidateQueries({ queryKey: ['social-page', pageId] });
      queryClient.invalidateQueries({ queryKey: ['social-pages'] });
    },
  });
};