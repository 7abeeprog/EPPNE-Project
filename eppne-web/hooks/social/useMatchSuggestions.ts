// hooks/social/useMatchSuggestions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
    staleTime: 2 * 60 * 1000,
  });
};