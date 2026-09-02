// hooks/command/useAlerts.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CommandService } from '@/services/command';

export const useSystemAlerts = (params?: { severity?: string; is_resolved?: boolean; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['command-alerts', params],
    queryFn: () => CommandService.listAlerts({ severity: params?.severity as any, limit: params?.limit }),
    refetchInterval: 15000,
    staleTime: 5000,
  });
};

export const useResolveAlert = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (alertId: number) => CommandService.resolveAlert(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['command-alerts'] });
    },
  });
};

export const useDismissAlert = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (alertId: number) => dismissAlert(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['command-alerts'] });
    },
  });
};