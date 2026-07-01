// store/zamakanaStore.ts
import { create } from 'zustand';
import type { ZamakanaNode, PlanetaryCampaign, FutureScenario } from '@/types/zamakana';

interface ZamakanaState {
  selectedNode: ZamakanaNode | null;
  selectedCampaign: PlanetaryCampaign | null;
  selectedScenario: FutureScenario | null;
  setSelectedNode: (node: ZamakanaNode | null) => void;
  setSelectedCampaign: (campaign: PlanetaryCampaign | null) => void;
  setSelectedScenario: (scenario: FutureScenario | null) => void;
}

export const useZamakanaStore = create<ZamakanaState>((set) => ({
  selectedNode: null,
  selectedCampaign: null,
  selectedScenario: null,
  setSelectedNode: (node) => set({ selectedNode: node }),
  setSelectedCampaign: (campaign) => set({ selectedCampaign: campaign }),
  setSelectedScenario: (scenario) => set({ selectedScenario: scenario }),
}));