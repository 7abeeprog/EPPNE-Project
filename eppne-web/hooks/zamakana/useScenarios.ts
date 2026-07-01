// hooks/zamakana/useScenarios.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getScenarios,
  getScenario,
  createScenario,
  analyzeScenario,
  addFeedback,
  confirmScenario,
} from '@/services/zamakana';

export const useScenarios = (params?: { status?: string; skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['zamakana-scenarios', params],
    queryFn: () => getScenarios(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useScenario = (id: number) => {
  return useQuery({
    queryKey: ['zamakana-scenario', id],
    queryFn: () => getScenario(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateScenario = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof createScenario>[0]) => createScenario(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zamakana-scenarios'] });
    },
  });
};

export const useAnalyzeScenario = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ scenarioId, idempotencyKey }: { scenarioId: number; idempotencyKey?: string }) =>
      analyzeScenario(scenarioId, idempotencyKey),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['zamakana-scenario', variables.scenarioId] });
      queryClient.invalidateQueries({ queryKey: ['zamakana-scenarios'] });
    },
  });
};

export const useAddFeedback = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof addFeedback>[0]) => addFeedback(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['zamakana-scenario', variables.scenario_id] });
    },
  });
};

export const useConfirmScenario = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (scenarioId: number) => confirmScenario(scenarioId),
    onSuccess: (_, scenarioId) => {
      queryClient.invalidateQueries({ queryKey: ['zamakana-scenario', scenarioId] });
      queryClient.invalidateQueries({ queryKey: ['zamakana-scenarios'] });
    },
  });
};