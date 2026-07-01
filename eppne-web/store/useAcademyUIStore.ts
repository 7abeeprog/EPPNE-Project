// store/useAcademyUIStore.ts
import { create } from 'zustand';

interface AcademyUIState {
  // 🟢 تتبع حالة العقد (Nodes) المفتوحة والمغلقة في الشجرة التنظيمية (UI Client State)
  expandedNodes: Record<number, boolean>;
  toggleNode: (nodeId: number) => void;
  collapseAll: () => void;
}

export const useAcademyUIStore = create<AcademyUIState>((set) => ({
  expandedNodes: {},
  
  toggleNode: (nodeId) =>
    set((state) => ({
      expandedNodes: {
        ...state.expandedNodes,
        [nodeId]: !state.expandedNodes[nodeId],
      },
    })),
    
  collapseAll: () => set({ expandedNodes: {} }),
}));