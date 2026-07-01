// store/tendersAuctionsStore.ts
import { create } from 'zustand';
import type { SovereignTender, SovereignAuction } from '@/types/tenders-auctions';

interface TendersAuctionsState {
  selectedTender: SovereignTender | null;
  selectedAuction: SovereignAuction | null;
  setSelectedTender: (tender: SovereignTender | null) => void;
  setSelectedAuction: (auction: SovereignAuction | null) => void;
}

export const useTendersAuctionsStore = create<TendersAuctionsState>((set) => ({
  selectedTender: null,
  selectedAuction: null,
  setSelectedTender: (tender) => set({ selectedTender: tender }),
  setSelectedAuction: (auction) => set({ selectedAuction: auction }),
}));