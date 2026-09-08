// hooks/zamakana/useScenarios.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getScenarios,
} from '@/services/zamakana';
import { ZamakanaService } from '@/services/zamakana';

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
    queryFn: () => ZamakanaService.getScenario(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateScenario = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof ZamakanaService.createScenario>[0]) => ZamakanaService.createScenario(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zamakana-scenarios'] });
    },
  });
};

export const useAnalyzeScenario = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ scenarioId, idempotencyKey }: { scenarioId: number; idempotencyKey?: string }) =>
      ZamakanaService.analyzeScenario(scenarioId, idempotencyKey),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['zamakana-scenario', variables.scenarioId] });
      queryClient.invalidateQueries({ queryKey: ['zamakana-scenarios'] });
    },
  });
};

export const useAddFeedback = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof ZamakanaService.addFeedback>[0]) => ZamakanaService.addFeedback(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['zamakana-scenario', variables.scenario_id] });
    },
  });
};

export const useConfirmScenario = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (scenarioId: number) => ZamakanaService.confirmScenario(scenarioId),
    onSuccess: (_, scenarioId) => {
      queryClient.invalidateQueries({ queryKey: ['zamakana-scenario', scenarioId] });
      queryClient.invalidateQueries({ queryKey: ['zamakana-scenarios'] });
    },
  });
};