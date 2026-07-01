// store/logisticsStore.ts
import { create } from 'zustand';
import type { Warehouse, InventoryItem, Equipment } from '@/types/logistics';

interface LogisticsState {
  selectedWarehouse: Warehouse | null;
  selectedInventory: InventoryItem | null;
  selectedEquipment: Equipment | null;
  setSelectedWarehouse: (warehouse: Warehouse | null) => void;
  setSelectedInventory: (item: InventoryItem | null) => void;
  setSelectedEquipment: (equipment: Equipment | null) => void;
}

export const useLogisticsStore = create<LogisticsState>((set) => ({
  selectedWarehouse: null,
  selectedInventory: null,
  selectedEquipment: null,
  setSelectedWarehouse: (warehouse) => set({ selectedWarehouse: warehouse }),
  setSelectedInventory: (item) => set({ selectedInventory: item }),
  setSelectedEquipment: (equipment) => set({ selectedEquipment: equipment }),
}));