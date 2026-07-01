// store/iot-store.ts
import { create } from 'zustand';

interface IoTUIState {
  activeTab: 'dashboard' | 'assets' | 'carbon' | 'readings' | 'maintenance';
  selectedAssetId: number | null;
  filterAssetClass: string | null;
  isCreateModalOpen: boolean;
  
  setActiveTab: (tab: IoTUIState['activeTab']) => void;
  setSelectedAssetId: (id: number | null) => void;
  setFilterAssetClass: (cls: string | null) => void;
  toggleCreateModal: (open?: boolean) => void;
}

export const useIoTStore = create<IoTUIState>((set) => ({
  activeTab: 'dashboard',
  selectedAssetId: null,
  filterAssetClass: null,
  isCreateModalOpen: false,

  setActiveTab: (tab) => set({ activeTab: tab }),
  setSelectedAssetId: (id) => set({ selectedAssetId: id }),
  setFilterAssetClass: (cls) => set({ filterAssetClass: cls }),
  toggleCreateModal: (open) => set((state) => ({ isCreateModalOpen: open !== undefined ? open : !state.isCreateModalOpen })),
}));