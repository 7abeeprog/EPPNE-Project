// store/tourismSportsStore.ts
import { create } from 'zustand';
import type { TourismDestination, TourismProgram, EntertainmentEvent, PlayerTransfer } from '@/types/tourism-sports';

interface TourismSportsState {
  selectedDestination: TourismDestination | null;
  selectedProgram: TourismProgram | null;
  selectedEvent: EntertainmentEvent | null;
  activeTransfers: PlayerTransfer[];
  setSelectedDestination: (dest: TourismDestination | null) => void;
  setSelectedProgram: (prog: TourismProgram | null) => void;
  setSelectedEvent: (event: EntertainmentEvent | null) => void;
  setActiveTransfers: (transfers: PlayerTransfer[]) => void;
}

export const useTourismSportsStore = create<TourismSportsState>((set) => ({
  selectedDestination: null,
  selectedProgram: null,
  selectedEvent: null,
  activeTransfers: [],
  setSelectedDestination: (dest) => set({ selectedDestination: dest }),
  setSelectedProgram: (prog) => set({ selectedProgram: prog }),
  setSelectedEvent: (event) => set({ selectedEvent: event }),
  setActiveTransfers: (transfers) => set({ activeTransfers: transfers }),
}));