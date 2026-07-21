// services/finance.service.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";

type WalletBalanceResponse = components['schemas']['WalletBalanceResponse'];
type TransferRequest = components['schemas']['TransferRequest'];
type TransferResponse = components['schemas']['TransferResponse'];
type SwapRequest = components['schemas']['SwapRequest'];
type SwapResponse = components['schemas']['SwapResponse'];
type PaginatedTransactionResponse = components['schemas']['PaginatedTransactionResponse'];
type MintRequest = components['schemas']['MintRequest'];
type MaxSupplyUpdate = components['schemas']['MaxSupplyUpdate'];
type ExchangeRatesUpdate = components['schemas']['ExchangeRatesUpdate'];
type CryptoModeToggle = components['schemas']['CryptoModeToggle'];

export const FinanceService = {
  // ==========================================
  // 1. المحفظة والأرصدة
  // ==========================================
  getBalances: async (): Promise<WalletBalanceResponse> => {
    try {
      const { data } = await apiClient.get<WalletBalanceResponse>("/finance/balances", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب رصيد المحفظة");
    }
  },

  // ==========================================
  // 2. التحويل
  // ==========================================
  transferFunds: async (data: TransferRequest): Promise<TransferResponse> => {
    try {
      const { data: result } = await apiClient.post<TransferResponse>("/finance/transfer", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إجراء التحويل");
    }
  },

  // ==========================================
  // 3. الصرافة
  // ==========================================
  swapCurrencies: async (data: SwapRequest): Promise<SwapResponse> => {
    try {
      const { data: result } = await apiClient.post<SwapResponse>("/finance/swap", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إجراء الصرافة");
    }
  },

  // ==========================================
  // 4. سجل المعاملات
  // ==========================================
  getHistory: async (params?: {
    skip?: number;
    limit?: number;
    start_date?: string;
    end_date?: string;
    currency?: string;
    tx_type?: string;
  }): Promise<PaginatedTransactionResponse> => {
    try {
      const { data } = await apiClient.get<PaginatedTransactionResponse>("/finance/history", {
        params: params || { skip: 0, limit: 20 },
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب سجل المعاملات");
    }
  },

  // ==========================================
  // 5. إدارة النظام
  // ==========================================
  getCryptoMode: async (): Promise<any> => {
    try {
      const { data } = await apiClient.get("/finance/admin/crypto-mode");
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب وضع العملات");
    }
  },

  setCryptoMode: async (data: CryptoModeToggle): Promise<void> => {
    try {
      await apiClient.post("/finance/admin/crypto-mode", data, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل تحديث وضع العملات");
    }
  },

  setExchangeRates: async (data: ExchangeRatesUpdate): Promise<void> => {
    try {
      await apiClient.post("/finance/admin/exchange-rates", data, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل تحديث أسعار الصرف");
    }
  },

  mintFunds: async (data: MintRequest): Promise<void> => {
    try {
      await apiClient.post("/finance/admin/mint", data, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل طباعة العملات");
    }
  },

  setMaxSupply: async (data: MaxSupplyUpdate): Promise<void> => {
    try {
      await apiClient.post("/finance/admin/max-supply", data, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل تحديث الحد الأقصى للعرض");
    }
  },
};