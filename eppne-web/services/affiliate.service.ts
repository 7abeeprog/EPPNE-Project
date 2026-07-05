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
import { generateIdempotencyKey } from "@/lib/utils";

export const FinanceService = {
  /**
   * جلب رصيد المحفظة للمستخدم الحالي
   * @returns {Promise<WalletBalance>} كائن يحتوي على أرصدة العملات
   */
  getWallet: async (): Promise<WalletBalance> => {
    try {
      const { data } = await apiClient.get('/api/finance/balances');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب رصيد المحفظة');
    }
  },

  /**
   * تحويل أموال إلى مستخدم آخر
   * @param {TransferRequest} payload - بيانات التحويل (مع أو بدون idempotency_key)
   * @returns {Promise<TransferResponse>} تفاصيل التحويل
   */
  transfer: async (payload: TransferRequest): Promise<TransferResponse> => {
    try {
      const finalPayload = {
        ...payload,
        idempotency_key: payload.idempotency_key || generateIdempotencyKey(),
      };
      const { data } = await apiClient.post('/api/finance/transfer', finalPayload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل إجراء التحويل');
    }
  },

  /**
   * صرافة عملة إلى أخرى
   * @param {SwapRequest} payload - بيانات الصرافة
   * @returns {Promise<SwapResponse>} تفاصيل الصرافة
   */
  swap: async (payload: SwapRequest): Promise<SwapResponse> => {
    try {
      const finalPayload = {
        ...payload,
        idempotency_key: payload.idempotency_key || generateIdempotencyKey(),
      };
      const { data } = await apiClient.post('/api/finance/swap', finalPayload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل إجراء الصرافة');
    }
  },

  /**
   * جلب سجل المعاملات مع Pagination
   * @param {number} skip - عدد العناصر المتخطية
   * @param {number} limit - عدد العناصر في الصفحة
   * @returns {Promise<PaginatedResponse<Transaction>>} قائمة المعاملات
   */
  getTransactionHistory: async (
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<Transaction>> => {
    try {
      const { data } = await apiClient.get('/api/finance/history', {
        params: { skip, limit },
      });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب سجل المعاملات');
    }
  },

  // ==========================================
  // دوال المشرفين (Admin)
  // ==========================================

  /**
   * جلب وضع العملات الحالي (FULL_CRYPTO أو POINTS_ONLY)
   * @returns {Promise<{ crypto_mode: string }>}
   */
  getCryptoMode: async (): Promise<{ crypto_mode: string }> => {
    try {
      const { data } = await apiClient.get('/api/finance/admin/crypto-mode');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب وضع العملات');
    }
  },

  /**
   * تحديث وضع العملات
   * @param {string} mode - 'FULL_CRYPTO' أو 'POINTS_ONLY'
   */
  setCryptoMode: async (mode: string): Promise<void> => {
    try {
      await apiClient.post('/api/finance/admin/crypto-mode', { mode });
    } catch (error) {
      throw handleError(error, 'فشل تحديث وضع العملات');
    }
  },

  /**
   * تحديث أسعار الصرف بين العملات
   * @param {ExchangeRates} rates - كائن يحتوي على أسعار الصرف
   */
  setExchangeRates: async (rates: ExchangeRates): Promise<void> => {
    try {
      await apiClient.post('/api/finance/admin/exchange-rates', { rates });
    } catch (error) {
      throw handleError(error, 'فشل تحديث أسعار الصرف');
    }
  },

  /**
   * طباعة عملات جديدة (للبنك المركزي فقط)
   * @param {MintRequest} payload - العملة والمبلغ
   */
  mintCurrency: async (payload: MintRequest): Promise<void> => {
    try {
      const finalPayload = {
        ...payload,
        idempotency_key: generateIdempotencyKey(),
      };
      await apiClient.post('/api/finance/admin/mint', finalPayload);
    } catch (error) {
      throw handleError(error, 'فشل طباعة العملات');
    }
  },

  /**
   * تحديث الحد الأقصى للطباعة لكل عملة
   * @param {Record<string, number>} maxSupply - كائن يحتوي على الحدود القصوى
   */
  setMaxSupply: async (maxSupply: Record<string, number>): Promise<void> => {
    try {
      await apiClient.post('/api/finance/admin/max-supply', { max_supply: maxSupply });
    } catch (error) {
      throw handleError(error, 'فشل تحديث الحد الأقصى للطباعة');
    }
  },

  // ==========================================
  // دوال مساعدة للقطاعات الأخرى (Integration Helpers)
  // ==========================================

  /**
   * دفع رسوم كورس (لقطاع التعليم)
   * @param {number} courseId - معرف الكورس
   * @param {number} amount - المبلغ
   * @param {string} currency - العملة (افتراضي MR_USDT)
   */
  payForCourse: async (courseId: number, amount: number, currency: string = 'MR_USDT'): Promise<TransferResponse> => {
    return FinanceService.transfer({
      receiver_email: 'academy@eppne.com', // يجب أن يكون بريد الأكاديمية
      currency,
      amount,
      notes: `دفع رسوم كورس #${courseId}`,
    });
  },

  /**
   * دفع رسوم خدمة (لقطاع السوق)
   * @param {number} serviceId - معرف الخدمة
   * @param {number} amount - المبلغ
   * @param {string} currency - العملة (افتراضي MR_USDT)
   */
  payForService: async (serviceId: number, amount: number, currency: string = 'MR_USDT'): Promise<TransferResponse> => {
    return FinanceService.transfer({
      receiver_email: 'marketplace@eppne.com',
      currency,
      amount,
      notes: `دفع رسوم خدمة #${serviceId}`,
    });
  },

  /**
   * دفع راتب (لقطاع التوظيف)
   * @param {number} employeeId - معرف الموظف
   * @param {number} amount - المبلغ
   * @param {string} currency - العملة (افتراضي MR_USDT)
   */
  paySalary: async (employeeId: number, amount: number, currency: string = 'MR_USDT'): Promise<TransferResponse> => {
    return FinanceService.transfer({
      receiver_email: `employee-${employeeId}@eppne.com`, // يجب أن يكون بريد الموظف
      currency,
      amount,
      notes: `دفع راتب الموظف #${employeeId}`,
    });
  },
};