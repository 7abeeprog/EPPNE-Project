// hooks/insurance/usePolicies.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getPolicies, getPolicy, createPolicy, updatePolicy, deletePolicy } from '@/services/insurance';

export const usePolicies = (params?: { policy_type?: string; is_active?: boolean; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['insurance-policies', params],
    queryFn: () => getPolicies(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const usePolicy = (id: number) => {
  return useQuery({
    queryKey: ['insurance-policy', id],
    queryFn: () => getPolicy(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreatePolicy = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof createPolicy>[0]) => createPolicy(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['insurance-policies'] });
    },
  });
};

export const useUpdatePolicy = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updatePolicy>[1] }) =>
      updatePolicy(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['insurance-policy', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['insurance-policies'] });
    },
  });
};

export const useDeletePolicy = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deletePolicy(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['insurance-policies'] });
    },
  });
};