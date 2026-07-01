// store/commandStore.ts
import { create } from 'zustand';
import type { Brand, SystemAlert } from '@/types/command';

interface CommandState {
  selectedBrand: Brand | null;
  selectedBrandId: number | null;
  alerts: SystemAlert[];
  unreadAlerts: number;
  setSelectedBrand: (brand: Brand | null) => void;
  setSelectedBrandId: (id: number | null) => void;
  setAlerts: (alerts: SystemAlert[]) => void;
  addAlert: (alert: SystemAlert) => void;
  removeAlert: (alertId: number) => void;
  markAlertRead: (alertId: number) => void;
}

export const useCommandStore = create<CommandState>((set) => ({
  selectedBrand: null,
  selectedBrandId: null,
  alerts: [],
  unreadAlerts: 0,
  setSelectedBrand: (brand) => set({ selectedBrand: brand, selectedBrandId: brand?.id || null }),
  setSelectedBrandId: (id) => set({ selectedBrandId: id }),
  setAlerts: (alerts) => set({ alerts, unreadAlerts: alerts.filter(a => !a.is_resolved).length }),
  addAlert: (alert) =>
    set((state) => ({
      alerts: [alert, ...state.alerts],
      unreadAlerts: state.unreadAlerts + 1,
    })),
  removeAlert: (alertId) =>
    set((state) => ({
      alerts: state.alerts.filter((a) => a.id !== alertId),
      unreadAlerts: state.alerts.filter((a) => a.id !== alertId && !a.is_resolved).length,
    })),
  markAlertRead: (alertId) =>
    set((state) => ({
      alerts: state.alerts.map((a) =>
        a.id === alertId ? { ...a, is_resolved: true } : a
      ),
      unreadAlerts: state.alerts.filter((a) => a.id !== alertId && !a.is_resolved).length,
    })),
}));