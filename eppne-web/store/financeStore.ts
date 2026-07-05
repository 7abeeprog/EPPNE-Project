// store/financeStore.ts
import { create } from 'zustand';
import { financeService, MintRequest, ExchangeRatesUpdate, MaxSupplyUpdate, CryptoModeToggle } from '@/services/finance.service';
import { useNotificationStore } from './notificationStore';

interface FinanceState {
  balances: Record<string, number> | null;
  exchangeRates: Record<string, number> | null;
  cryptoMode: 'FULL_CRYPTO' | 'POINTS_ONLY' | null;
  isLoading: boolean;
  error: string | null;
  
  // دوال المستخدم
  fetchBalances: () => Promise<void>;
  transferFunds: (data: any) => Promise<any>;
  swapCurrencies: (data: any) => Promise<any>;
  fetchHistory: (params?: any) => Promise<any>;
  
  // دوال المشرف
  mintFunds: (data: MintRequest) => Promise<void>;
  setExchangeRates: (data: ExchangeRatesUpdate) => Promise<void>;
  setMaxSupply: (data: MaxSupplyUpdate) => Promise<void>;
  fetchCryptoMode: () => Promise<void>;
  setCryptoMode: (data: CryptoModeToggle) => Promise<void>;
}

export const useFinanceStore = create<FinanceState>((set, get) => ({
  balances: null,
  exchangeRates: null,
  cryptoMode: null,
  isLoading: false,
  error: null,

  // --- دوال المستخدم ---
  fetchBalances: async () => {
    set({ isLoading: true });
    try {
      const data = await financeService.getBalances();
      set({ balances: data.balances, isLoading: false });
    } catch (error: any) {
      set({ isLoading: false, error: error.message });
    }
  },

  transferFunds: async (data) => {
    set({ isLoading: true });
    try {
      const response = await financeService.transferFunds(data);
      set({ isLoading: false });
      // تحديث الرصيد بعد التحويل
      await get().fetchBalances();
      return response;
    } catch (error: any) {
      set({ isLoading: false, error: error.message });
      throw error;
    }
  },

  swapCurrencies: async (data) => {
    set({ isLoading: true });
    try {
      const response = await financeService.swapCurrencies(data);
      set({ isLoading: false });
      await get().fetchBalances();
      return response;
    } catch (error: any) {
      set({ isLoading: false, error: error.message });
      throw error;
    }
  },

  fetchHistory: async (params) => {
    set({ isLoading: true });
    try {
      const data = await financeService.getHistory(params);
      set({ isLoading: false });
      return data;
    } catch (error: any) {
      set({ isLoading: false, error: error.message });
      throw error;
    }
  },

  // --- دوال المشرف (Super Admin) ---
  mintFunds: async (data: MintRequest) => {
    set({ isLoading: true, error: null });
    try {
      await financeService.mintFunds(data);
      set({ isLoading: false });
      
      // 🔔 إرسال إشعار للمشرفين
      const notificationStore = useNotificationStore.getState();
      notificationStore.addNotification({
        id: Date.now(),
        user_id: 0, // سيتم استبداله من الخادم
        title: '💰 تم طباعة عملات جديدة',
        body: `تم طباعة ${data.amount} من ${data.currency} بنجاح.`,
        data: { link: '/dashboard/finance/admin' },
        is_read: false,
        priority: 'HIGH',
        created_at: new Date().toISOString(),
      });
      
      // تحديث الرصيد
      await get().fetchBalances();
    } catch (error: any) {
      set({ isLoading: false, error: error.message });
      throw error;
    }
  },

  setExchangeRates: async (data: ExchangeRatesUpdate) => {
    set({ isLoading: true, error: null });
    try {
      await financeService.setExchangeRates(data);
      set({ exchangeRates: data.rates, isLoading: false });
      
      // 🔔 إشعار بتحديث الأسعار
      const notificationStore = useNotificationStore.getState();
      notificationStore.addNotification({
        id: Date.now(),
        user_id: 0,
        title: '📊 تحديث أسعار الصرف',
        body: 'تم تحديث أسعار الصرف بنجاح.',
        data: { link: '/dashboard/finance/admin' },
        is_read: false,
        priority: 'NORMAL',
        created_at: new Date().toISOString(),
      });
    } catch (error: any) {
      set({ isLoading: false, error: error.message });
      throw error;
    }
  },

  setMaxSupply: async (data: MaxSupplyUpdate) => {
    set({ isLoading: true, error: null });
    try {
      await financeService.setMaxSupply(data);
      set({ isLoading: false });
      
      const notificationStore = useNotificationStore.getState();
      notificationStore.addNotification({
        id: Date.now(),
        user_id: 0,
        title: '🔢 تحديد الحد الأقصى للطباعة',
        body: 'تم تحديث الحد الأقصى للطباعة لكل عملة.',
        data: { link: '/dashboard/finance/admin' },
        is_read: false,
        priority: 'NORMAL',
        created_at: new Date().toISOString(),
      });
    } catch (error: any) {
      set({ isLoading: false, error: error.message });
      throw error;
    }
  },

  fetchCryptoMode: async () => {
    try {
      const data = await financeService.getCryptoMode();
      set({ cryptoMode: data.mode });
    } catch (error) {
      console.error('Failed to fetch crypto mode', error);
    }
  },

  setCryptoMode: async (data: CryptoModeToggle) => {
    set({ isLoading: true });
    try {
      await financeService.setCryptoMode(data);
      set({ cryptoMode: data.mode, isLoading: false });
      
      const notificationStore = useNotificationStore.getState();
      notificationStore.addNotification({
        id: Date.now(),
        user_id: 0,
        title: '🔄 تبديل وضع العملات المشفرة',
        body: `تم تبديل الوضع إلى: ${data.mode}`,
        data: { link: '/dashboard/finance/admin' },
        is_read: false,
        priority: 'HIGH',
        created_at: new Date().toISOString(),
      });
    } catch (error: any) {
      set({ isLoading: false, error: error.message });
      throw error;
    }
  },
}));