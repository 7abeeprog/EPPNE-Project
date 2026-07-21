import { create } from 'zustand';
// تم تعديل الاستيراد واستخدام الكائن مباشرة
import { FinanceService } from '@/services/finance.service';
import { useNotificationStore } from './notificationStore';

type CryptoMode = 'FULL_CRYPTO' | 'POINTS_ONLY';

interface FinanceState {
  wallet: { balances: Record<string, number> } | null;
  exchangeRates: Record<string, number> | null;
  cryptoMode: CryptoMode | null;
  isLoading: boolean;
  error: string | null;
  isWeb3Loading: boolean;

  fetchWallet: () => Promise<void>;
  transferFunds: (data: any) => Promise<any>;
  swapCurrencies: (data: any) => Promise<any>;
  fetchHistory: (params?: any) => Promise<any>;

  mintFunds: (data: any) => Promise<void>;
  setExchangeRates: (data: any) => Promise<void>;
  setMaxSupply: (data: any) => Promise<void>;
  fetchCryptoMode: () => Promise<void>;
  setCryptoMode: (data: any) => Promise<void>;
  setWeb3Loading: (isLoading: boolean) => void;
}

export const useFinanceStore = create<FinanceState>((set, get) => ({
  wallet: null,
  exchangeRates: null,
  cryptoMode: null,
  isLoading: false,
  error: null as string | null, // حل مشكلة TypeScript (Type 'never')
  isWeb3Loading: false,

  fetchWallet: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await FinanceService.getBalances(); // استدعاء مباشر
      set({ wallet: data, isLoading: false });
    } catch (error: any) {
      set({ isLoading: false, error: String(error?.message || error) });
    }
  },

  transferFunds: async (data) => {
    set({ isLoading: true });
    try {
      const response = await FinanceService.transferFunds(data);
      set({ isLoading: false });
      await get().fetchWallet();
      return response;
    } catch (error: any) {
      set({ isLoading: false, error: String(error?.message || error) });
      throw error;
    }
  },

  swapCurrencies: async (data) => {
    set({ isLoading: true });
    try {
      const response = await FinanceService.swapCurrencies(data);
      set({ isLoading: false });
      await get().fetchWallet();
      return response;
    } catch (error: any) {
      set({ isLoading: false, error: String(error?.message || error) });
      throw error;
    }
  },

  fetchHistory: async (params) => {
    set({ isLoading: true });
    try {
      const data = await FinanceService.getHistory(params);
      set({ isLoading: false });
      return data;
    } catch (error: any) {
      set({ isLoading: false, error: String(error?.message || error) });
      throw error;
    }
  },

  mintFunds: async (data: any) => {
    set({ isLoading: true, error: null });
    try {
      await FinanceService.mintFunds(data);
      set({ isLoading: false });

      const notificationStore = useNotificationStore.getState();
      notificationStore.addNotification({
        id: Date.now(),
        user_id: 0,
        title: '💰 تم طباعة عملات جديدة',
        body: `تم طباعة ${data.amount} من ${data.currency} بنجاح.`,
        data: { link: '/dashboard/finance/admin' } as any,
        is_read: false,
        priority: 'HIGH',
        created_at: new Date().toISOString(),
      });

      await get().fetchWallet();
    } catch (error: any) {
      set({ isLoading: false, error: String(error?.message || error) });
      throw error;
    }
  },

  setExchangeRates: async (data: any) => {
    set({ isLoading: true, error: null });
    try {
      await FinanceService.setExchangeRates(data);
      set({ exchangeRates: data.rates, isLoading: false });

      const notificationStore = useNotificationStore.getState();
      notificationStore.addNotification({
        id: Date.now(),
        user_id: 0,
        title: '📊 تحديث أسعار الصرف',
        body: 'تم تحديث أسعار الصرف بنجاح.',
        data: { link: '/dashboard/finance/admin' } as any,
        is_read: false,
        priority: 'NORMAL',
        created_at: new Date().toISOString(),
      });
    } catch (error: any) {
      set({ isLoading: false, error: String(error?.message || error) });
      throw error;
    }
  },

  setMaxSupply: async (data: any) => {
    set({ isLoading: true, error: null });
    try {
      await FinanceService.setMaxSupply(data);
      set({ isLoading: false });

      const notificationStore = useNotificationStore.getState();
      notificationStore.addNotification({
        id: Date.now(),
        user_id: 0,
        title: '🔢 تحديد الحد الأقصى للطباعة',
        body: 'تم تحديث الحد الأقصى للطباعة لكل عملة.',
        data: { link: '/dashboard/finance/admin' } as any,
        is_read: false,
        priority: 'NORMAL',
        created_at: new Date().toISOString(),
      });
    } catch (error: any) {
      set({ isLoading: false, error: String(error?.message || error) });
      throw error;
    }
  },

  fetchCryptoMode: async () => {
    try {
      const data = await FinanceService.getCryptoMode();
      set({ cryptoMode: data.mode });
    } catch (error) {
      console.error('Failed to fetch crypto mode', error);
    }
  },

  setCryptoMode: async (data: any) => {
    set({ isLoading: true });
    try {
      await FinanceService.setCryptoMode(data);
      set({ cryptoMode: data.mode, isLoading: false });

      const notificationStore = useNotificationStore.getState();
      notificationStore.addNotification({
        id: Date.now(),
        user_id: 0,
        title: '🔄 تبديل وضع العملات المشفرة',
        body: `تم تبديل الوضع إلى: ${data.mode}`,
        data: { link: '/dashboard/finance/admin' } as any,
        is_read: false,
        priority: 'HIGH',
        created_at: new Date().toISOString(),
      });
    } catch (error: any) {
      set({ isLoading: false, error: String(error?.message || error) });
      throw error;
    }
  },

  setWeb3Loading: (isLoading) => set({ isWeb3Loading: isLoading }),
}));