// hooks/insurance/useEmployeeProfile.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMyEmployeeProfile, createEmployeeProfile, updateEmployeeProfile } from '@/services/insurance';

export const useMyEmployeeProfile = () => {
  return useQuery({
    queryKey: ['insurance-employee-profile'],
    queryFn: () => getMyEmployeeProfile().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateEmployeeProfile = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof createEmployeeProfile>[0]) => createEmployeeProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['insurance-employee-profile'] });
    },
  });
};

export const useUpdateEmployeeProfile = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data }: { data: Parameters<typeof updateEmployeeProfile>[0] }) =>
      updateEmployeeProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['insurance-employee-profile'] });
    },
  });
};