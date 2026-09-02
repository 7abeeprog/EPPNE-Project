// hooks/tourism-sports/useSportsOrganizations.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getSportsOrganizations } from '@/services/tourism-sports';
import { TourismSportsService } from '@/services/tourism-sports';

export const useSportsOrganizations = (params?: { org_type?: string }) => {
  return useQuery({
    queryKey: ['sports-organizations', params],
    queryFn: () => getSportsOrganizations(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useSportsOrg = (id: number) => {
  return useQuery({
    queryKey: ['sports-organization', id],
    queryFn: () => TourismSportsService.getSportsOrg(id),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateSportsOrg = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof TourismSportsService.createSportsOrg>[0]) => TourismSportsService.createSportsOrg(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sports-organizations'] });
    },
  });
};