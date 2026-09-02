// hooks/insurance/useEmployeeProfile.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { InsuranceService } from '@/services/insurance';

export const useMyEmployeeProfile = () => {
  return useQuery({
    queryKey: ['insurance-employee-profile'],
    queryFn: () => InsuranceService.getMyEmployeeProfile(),
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateEmployeeProfile = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof InsuranceService.createEmployeeProfile>[0]) => InsuranceService.createEmployeeProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['insurance-employee-profile'] });
    },
  });
};

export const useUpdateEmployeeProfile = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data }: { data: Parameters<typeof InsuranceService.updateEmployeeProfile>[0] }) =>
      InsuranceService.updateEmployeeProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['insurance-employee-profile'] });
    },
  });
};