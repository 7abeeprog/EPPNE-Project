// store/enterprise-store.ts
import { create } from 'zustand';

interface EnterpriseUIState {
  selectedEntityId: number | null;
  selectedCohortId: number | null;
  setSelectedEntityId: (id: number | null) => void;
  setSelectedCohortId: (id: number | null) => void;
}

export const useEnterpriseUIStore = create<EnterpriseUIState>((set) => ({
  selectedEntityId: null,
  selectedCohortId: null,
  setSelectedEntityId: (id) => set({ selectedEntityId: id, selectedCohortId: null }),
  setSelectedCohortId: (id) => set({ selectedCohortId: id }),
}));