// hooks/social/useMatchSuggestions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMatchProfile, updateMatchProfile, getMatchSuggestions } from '@/services/social';

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
    staleTime: 2 * 60 * 1000,
  });
};