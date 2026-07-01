// store/automationStore.ts
import { create } from 'zustand';

interface AutomationUIState {
  // حالة التنفيذات النشطة (للتحديث الفوري)
  activeExecutionId: number | null;
  setActiveExecutionId: (id: number | null) => void;
  
  // الأسرار (للعرض)
  secrets: { name: string; id: number }[];
  setSecrets: (secrets: { name: string; id: number }[]) => void;
  
  // الـ WebSocket للتنفيذات
  isWsConnected: boolean;
  setWsConnected: (status: boolean) => void;
}

export const useAutomationStore = create<AutomationUIState>((set) => ({
  activeExecutionId: null,
  setActiveExecutionId: (id) => set({ activeExecutionId: id }),
  secrets: [],
  setSecrets: (secrets) => set({ secrets }),
  isWsConnected: false,
  setWsConnected: (status) => set({ isWsConnected: status }),
}));