// store/insuranceStore.ts
import { create } from 'zustand';
import type { InsurancePolicy, InsuranceSubscription, InsuranceClaim } from '@/types/insurance';

interface InsuranceState {
  selectedPolicy: InsurancePolicy | null;
  selectedSubscription: InsuranceSubscription | null;
  selectedClaim: InsuranceClaim | null;
  setSelectedPolicy: (policy: InsurancePolicy | null) => void;
  setSelectedSubscription: (subscription: InsuranceSubscription | null) => void;
  setSelectedClaim: (claim: InsuranceClaim | null) => void;
}

export const useInsuranceStore = create<InsuranceState>((set) => ({
  selectedPolicy: null,
  selectedSubscription: null,
  selectedClaim: null,
  setSelectedPolicy: (policy) => set({ selectedPolicy: policy }),
  setSelectedSubscription: (subscription) => set({ selectedSubscription: subscription }),
  setSelectedClaim: (claim) => set({ selectedClaim: claim }),
}));