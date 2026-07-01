// store/employmentStore.ts
import { create } from 'zustand';
import type { JobListing, JobApplication, EmploymentContract } from '@/types/employment';

interface EmploymentStore {
  // الحالة
  selectedJob: JobListing | null;
  selectedApplication: JobApplication | null;
  activeContract: EmploymentContract | null;
  isCheckingIn: boolean;
  isLoading: boolean;
  
  // الإجراءات
  setSelectedJob: (job: JobListing | null) => void;
  setSelectedApplication: (app: JobApplication | null) => void;
  setActiveContract: (contract: EmploymentContract | null) => void;
  setIsCheckingIn: (status: boolean) => void;
  setIsLoading: (status: boolean) => void;
  clear: () => void;
}

export const useEmploymentStore = create<EmploymentStore>((set) => ({
  selectedJob: null,
  selectedApplication: null,
  activeContract: null,
  isCheckingIn: false,
  isLoading: false,

  setSelectedJob: (job) => set({ selectedJob: job }),
  setSelectedApplication: (app) => set({ selectedApplication: app }),
  setActiveContract: (contract) => set({ activeContract: contract }),
  setIsCheckingIn: (status) => set({ isCheckingIn: status }),
  setIsLoading: (status) => set({ isLoading: status }),
  clear: () =>
    set({
      selectedJob: null,
      selectedApplication: null,
      activeContract: null,
      isCheckingIn: false,
    }),
}));