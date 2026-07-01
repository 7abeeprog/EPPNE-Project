// store/manufacturingStore.ts
import { create } from 'zustand';
import type { ManufacturingFacility, ProductionLine, ProductionBatch, PredictiveMaintenanceLog } from '@/types/manufacturing';

interface ManufacturingState {
  selectedFacility: ManufacturingFacility | null;
  selectedLine: ProductionLine | null;
  activeBatches: ProductionBatch[];
  pendingMaintenance: PredictiveMaintenanceLog[];
  setSelectedFacility: (facility: ManufacturingFacility | null) => void;
  setSelectedLine: (line: ProductionLine | null) => void;
  setActiveBatches: (batches: ProductionBatch[]) => void;
  addActiveBatch: (batch: ProductionBatch) => void;
  setPendingMaintenance: (logs: PredictiveMaintenanceLog[]) => void;
}

export const useManufacturingStore = create<ManufacturingState>((set) => ({
  selectedFacility: null,
  selectedLine: null,
  activeBatches: [],
  pendingMaintenance: [],
  setSelectedFacility: (facility) => set({ selectedFacility: facility }),
  setSelectedLine: (line) => set({ selectedLine: line }),
  setActiveBatches: (batches) => set({ activeBatches: batches }),
  addActiveBatch: (batch) => set((state) => ({ activeBatches: [batch, ...state.activeBatches] })),
  setPendingMaintenance: (logs) => set({ pendingMaintenance: logs }),
}));