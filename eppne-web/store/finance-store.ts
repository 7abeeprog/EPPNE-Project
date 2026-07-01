// store/finance-store.ts
import { create } from "zustand";

type CryptoMode = "FULL_CRYPTO" | "POINTS_ONLY";

interface FinanceState {
  cryptoMode: CryptoMode;
  isWeb3Loading: boolean;
  setCryptoMode: (mode: CryptoMode) => void;
  setWeb3Loading: (isLoading: boolean) => void;
}

// 🟢 الـ Store الآن نقي 100%: مخصص لحالات الواجهة (Client State) ولا يحتوي على أي اتصال بالخوادم
export const useFinanceStore = create<FinanceState>((set) => ({
  cryptoMode: "FULL_CRYPTO", // الحالة الافتراضية
  isWeb3Loading: false,

  setCryptoMode: (mode) => set({ cryptoMode: mode }),
  setWeb3Loading: (isLoading) => set({ isWeb3Loading: isLoading }),
}));