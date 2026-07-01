// store/realestateStore.ts
import { create } from 'zustand';
import type { PropertyUnit, AssetTokenization, PropertyOwnership } from '@/types/realestate';

interface RealEstateState {
  selectedUnit: PropertyUnit | null;
  tokenizations: AssetTokenization[];
  ownerships: PropertyOwnership[];
  isLoading: boolean;
  setSelectedUnit: (unit: PropertyUnit | null) => void;
  setTokenizations: (tokenizations: AssetTokenization[]) => void;
  setOwnerships: (ownerships: PropertyOwnership[]) => void;
  addOwnership: (ownership: PropertyOwnership) => void;
  clear: () => void;
}

export const useRealEstateStore = create<RealEstateState>((set) => ({
  selectedUnit: null,
  tokenizations: [],
  ownerships: [],
  isLoading: false,

  setSelectedUnit: (unit) => set({ selectedUnit: unit }),
  setTokenizations: (tokenizations) => set({ tokenizations }),
  setOwnerships: (ownerships) => set({ ownerships }),
  addOwnership: (ownership) =>
    set((state) => ({ ownerships: [ownership, ...state.ownerships] })),
  clear: () => set({ selectedUnit: null, tokenizations: [], ownerships: [] }),
}));