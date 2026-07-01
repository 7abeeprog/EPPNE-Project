// hooks/zamakana/useKnowledgeGraph.ts
import { useQuery } from '@tanstack/react-query';
import { getKnowledgeGraph } from '@/services/zamakana';

export const useKnowledgeGraph = (params?: { node_type?: string; limit?: number }) => {
  return useQuery({
    queryKey: ['zamakana-graph', params],
    queryFn: () => getKnowledgeGraph(params).then((res) => res.data),
    staleTime: 5 * 60 * 1000,
  });
};