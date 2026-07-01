// services/finance.service.ts
import { apiClient } from "@/lib/api-client";
import {
  WalletBalance,
  TransferRequest,
  TransferResponse,
  SwapRequest,
  SwapResponse,
  Transaction,
  PaginatedResponse,
  CryptoMode,
  ExchangeRates,
  MintRequest,
  SystemState,
} from "@/types/finance";
import { handleError } from "@/lib/error-handler";

export const FinanceService = {
  // ==========================================
  // 1. المحفظة والأرصدة
  // ==========================================
  getWallet: async (): Promise<WalletBalance> => {
    try {
      const { data } = await apiClient.get('/finance/balances');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب رصيد المحفظة');
    }
  },

  // ==========================================
  // 2. التحويل (مع Idempotency Key)
  // ==========================================
  transfer: async (payload: TransferRequest): Promise<TransferResponse> => {
    try {
      const { data } = await apiClient.post('/finance/transfer', payload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل إجراء التحويل');
    }
  },

  // ==========================================
  // 3. الصرافة
  // ==========================================
  swap: async (payload: SwapRequest): Promise<SwapResponse> => {
    try {
      const { data } = await apiClient.post('/finance/swap', payload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل إجراء الصرافة');
    }
  },

  // ==========================================
  // 4. سجل المعاملات (مع Pagination)
  // ==========================================
  getTransactionHistory: async (
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<Transaction>> => {
    try {
      const { data } = await apiClient.get('/finance/history', {
        params: { skip, limit },
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
      const { data } = await apiClient.get('/finance/admin/crypto-mode');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب وضع العملات');
    }
  },

  setCryptoMode: async (mode: string): Promise<void> => {
    try {
      await apiClient.post('/finance/admin/crypto-mode', { mode });
    } catch (error) {
      throw handleError(error, 'فشل تحديث وضع العملات');
    }
  },

  setExchangeRates: async (rates: ExchangeRates): Promise<void> => {
    try {
      await apiClient.post('/finance/admin/exchange-rates', { rates });
    } catch (error) {
      throw handleError(error, 'فشل تحديث أسعار الصرف');
    }
  },

  getSystemState: async (): Promise<SystemState> => {
    try {
      const { data } = await apiClient.get('/finance/admin/state');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب حالة النظام');
    }
  },

  mintCurrency: async (payload: MintRequest): Promise<void> => {
    try {
      await apiClient.post('/finance/admin/mint', payload);
    } catch (error) {
      throw handleError(error, 'فشل طباعة العملات');
    }
  },
};