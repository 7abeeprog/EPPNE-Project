// eppne-web/store/healthStore.ts
import { create } from 'zustand';

interface HealthState {
  status: string;
  setStatus: (status: string) => void;
}

export const useHealthStore = create<HealthState>((set) => ({
  status: 'offline',
  setStatus: (status) => set({ status }),
}));