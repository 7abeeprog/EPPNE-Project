// store/agritechStore.ts
import { create } from 'zustand';
import type { SmartFarm, FarmZone, CropCycle, WeatherAlert, AIRecommendation } from '@/types/agritech';

interface AgritechState {
  selectedFarm: SmartFarm | null;
  selectedZone: FarmZone | null;
  selectedCycle: CropCycle | null;
  activeAlerts: WeatherAlert[];
  aiRecommendations: AIRecommendation[];
  setSelectedFarm: (farm: SmartFarm | null) => void;
  setSelectedZone: (zone: FarmZone | null) => void;
  setSelectedCycle: (cycle: CropCycle | null) => void;
  setActiveAlerts: (alerts: WeatherAlert[]) => void;
  addAlert: (alert: WeatherAlert) => void;
  clearAlerts: () => void;
}

export const useAgritechStore = create<AgritechState>((set) => ({
  selectedFarm: null,
  selectedZone: null,
  selectedCycle: null,
  activeAlerts: [],
  aiRecommendations: [],

  setSelectedFarm: (farm) => set({ selectedFarm: farm }),
  setSelectedZone: (zone) => set({ selectedZone: zone }),
  setSelectedCycle: (cycle) => set({ selectedCycle: cycle }),
  setActiveAlerts: (alerts) => set({ activeAlerts: alerts }),
  addAlert: (alert) => set((state) => ({ activeAlerts: [alert, ...state.activeAlerts] })),
  clearAlerts: () => set({ activeAlerts: [] }),
}));