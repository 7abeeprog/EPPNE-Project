// hooks/arbitration-syndicates/useElections.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getElections, getElection, createElection, nominateCandidate, castVote } from '@/services/arbitration-syndicates';

export const useElections = (params?: { syndicate_id?: number; status?: string }) => {
  return useQuery({
    queryKey: ['arbitration-elections', params],
    queryFn: () => getElections(params).then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });
};

export const useElection = (id: number) => {
  return useQuery({
    queryKey: ['arbitration-election', id],
    queryFn: () => getElection(id).then((res) => res.data),
    enabled: !!id,
    staleTime: 2 * 60 * 1000,
  });
};

export const useCreateElection = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof createElection>[0]) => createElection(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['arbitration-elections'] });
    },
  });
};

export const useNominateCandidate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ electionId, data, idempotencyKey }: { electionId: number; data: { manifesto: string }; idempotencyKey?: string }) =>
      nominateCandidate(electionId, data, idempotencyKey),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['arbitration-election', variables.electionId] });
    },
  });
};

export const useCastVote = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ electionId, data, idempotencyKey }: { electionId: number; data: { candidate_id: number }; idempotencyKey?: string }) =>
      castVote(electionId, data, idempotencyKey),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['arbitration-election', variables.electionId] });
    },
  });
};