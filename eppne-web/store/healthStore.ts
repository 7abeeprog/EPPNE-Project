// store/healthStore.ts
import { create } from 'zustand';
import type { MedicalProfile, AIHealthPrognosis, EmergencyDispatch } from '@/types/health';

interface HealthState {
  profile: MedicalProfile | null;
  prognoses: AIHealthPrognosis[];
  activeEmergency: EmergencyDispatch | null;
  isEmergencyActive: boolean;
  setProfile: (profile: MedicalProfile) => void;
  setPrognoses: (prognoses: AIHealthPrognosis[]) => void;
  setActiveEmergency: (dispatch: EmergencyDispatch | null) => void;
  clearEmergency: () => void;
}

export const useHealthStore = create<HealthState>((set) => ({
  profile: null,
  prognoses: [],
  activeEmergency: null,
  isEmergencyActive: false,

  setProfile: (profile) => set({ profile }),
  setPrognoses: (prognoses) => set({ prognoses }),
  setActiveEmergency: (dispatch) =>
    set({ activeEmergency: dispatch, isEmergencyActive: !!dispatch }),
  clearEmergency: () => set({ activeEmergency: null, isEmergencyActive: false }),
}));