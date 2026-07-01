// store/arbitrationSyndicatesStore.ts
import { create } from 'zustand';
import type { ArbitrationCase, SovereignSyndicate, SyndicateElection } from '@/types/arbitration-syndicates';

interface ArbitrationSyndicatesState {
  selectedCase: ArbitrationCase | null;
  selectedSyndicate: SovereignSyndicate | null;
  selectedElection: SyndicateElection | null;
  setSelectedCase: (caseItem: ArbitrationCase | null) => void;
  setSelectedSyndicate: (syndicate: SovereignSyndicate | null) => void;
  setSelectedElection: (election: SyndicateElection | null) => void;
}

export const useArbitrationSyndicatesStore = create<ArbitrationSyndicatesState>((set) => ({
  selectedCase: null,
  selectedSyndicate: null,
  selectedElection: null,
  setSelectedCase: (caseItem) => set({ selectedCase: caseItem }),
  setSelectedSyndicate: (syndicate) => set({ selectedSyndicate: syndicate }),
  setSelectedElection: (election) => set({ selectedElection: election }),
}));