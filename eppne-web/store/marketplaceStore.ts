// store/marketplaceStore.ts
import { create } from 'zustand';
import type { MarketplaceService, ServiceLicense, ServiceAddon } from '@/types/marketplace';

interface MarketplaceStore {
  // الخدمات
  services: MarketplaceService[];
  selectedService: MarketplaceService | null;
  setServices: (services: MarketplaceService[]) => void;
  setSelectedService: (service: MarketplaceService | null) => void;

  // التراخيص
  licenses: ServiceLicense[];
  setLicenses: (licenses: ServiceLicense[]) => void;

  // الإضافات
  addons: ServiceAddon[];
  setAddons: (addons: ServiceAddon[]) => void;

  // حالة الشراء
  isPurchasing: boolean;
  setIsPurchasing: (isPurchasing: boolean) => void;

  clear: () => void;
}

export const useMarketplaceStore = create<MarketplaceStore>((set) => ({
  services: [],
  selectedService: null,
  licenses: [],
  addons: [],
  isPurchasing: false,

  setServices: (services) => set({ services }),
  setSelectedService: (service) => set({ selectedService: service }),
  setLicenses: (licenses) => set({ licenses }),
  setAddons: (addons) => set({ addons }),
  setIsPurchasing: (isPurchasing) => set({ isPurchasing }),

  clear: () =>
    set({
      services: [],
      selectedService: null,
      licenses: [],
      addons: [],
      isPurchasing: false,
    }),
}));