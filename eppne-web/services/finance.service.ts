// services/finance.service.ts
import apiClient from '@/lib/api-client';
import { handleError } from '@/lib/error-handler';
import {
  WalletBalance,
  TransferRequest,
  TransferResponse,
  SwapRequest,
  SwapResponse,
  Transaction,
  PaginatedResponse,
  ExchangeRates,
  MintRequest,
  SystemState,
} from '@/types/finance';

// واجهات إضافية من الملف الأصلي الثاني
export interface ExchangeRatesUpdate {
  rates: Record<string, number>;
}

export interface MaxSupplyUpdate {
  max_supply: Record<string, number>;
}

export interface CryptoModeToggle {
  mode: 'FULL_CRYPTO' | 'POINTS_ONLY';
}

export const financeService = {
  // ==========================================
  // 1. المحفظة والأرصدة
  // ==========================================
  getBalances: async (): Promise<WalletBalance> => {
    try {
      const { data } = await apiClient.get('/api/finance/balances');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب رصيد المحفظة');
    }
  },

  // ==========================================
  // 2. التحويل (مع Idempotency Key)
  // ==========================================
  transferFunds: async (payload: TransferRequest): Promise<TransferResponse> => {
    try {
      const { data } = await apiClient.post('/api/finance/transfer', payload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل إجراء التحويل');
    }
  },

  // ==========================================
  // 3. الصرافة
  // ==========================================
  swapCurrencies: async (payload: SwapRequest): Promise<SwapResponse> => {
    try {
      const { data } = await apiClient.post('/api/finance/swap', payload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل إجراء الصرافة');
    }
  },

  // ==========================================
  // 4. سجل المعاملات (مع Pagination)
  // ==========================================
  getHistory: async (
    params?: { skip?: number; limit?: number }
  ): Promise<PaginatedResponse<Transaction>> => {
    try {
      const { data } = await apiClient.get('/api/finance/history', {
        params: params || { skip: 0, limit: 20 },
      });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب سجل المعاملات');
    }
  },

  // ==========================================
  // 5. إدارة النظام (للمشرفين)
  // ==========================================
  getCryptoMode: async (): Promise<{ crypto_mode: string }> => {
    try {
      const { data } = await apiClient.get('/api/finance/admin/crypto-mode');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب وضع العملات');
    }
  },

  setCryptoMode: async (mode: string): Promise<void> => {
    try {
      await apiClient.post('/api/finance/admin/crypto-mode', { mode });
    } catch (error) {
      throw handleError(error, 'فشل تحديث وضع العملات');
    }
  },

  setExchangeRates: async (rates: ExchangeRates): Promise<void> => {
    try {
      await apiClient.post('/api/finance/admin/exchange-rates', { rates });
    } catch (error) {
      throw handleError(error, 'فشل تحديث أسعار الصرف');
    }
  },

  // إضافة من الملف الأصلي الثاني
  setMaxSupply: async (data: MaxSupplyUpdate): Promise<void> => {
    try {
      await apiClient.post('/api/finance/admin/max-supply', data);
    } catch (error) {
      throw handleError(error, 'فشل تحديث الحد الأقصى للعرض');
    }
  },

  mintFunds: async (payload: MintRequest): Promise<void> => {
    try {
      await apiClient.post('/api/finance/admin/mint', payload, {
        headers: { 'Idempotency-Key': crypto.randomUUID() },
      });
    } catch (error) {
      throw handleError(error, 'فشل طباعة العملات');
    }
  },

  getSystemState: async (): Promise<SystemState> => {
    try {
      const { data } = await apiClient.get('/api/finance/admin/state');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب حالة النظام');
    }
  },
};