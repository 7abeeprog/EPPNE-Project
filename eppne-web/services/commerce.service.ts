// services/commerce.service.ts
import { apiClient } from "@/lib/api-client";
import {
  Product,
  ProductVariant,
  Order,
  CheckoutRequest,
  CheckoutResponse,
  Address,
  PaymentRequest,
  Commission,
  AffiliateTree,
  PaginatedResponse,
  WalletBalance,
} from "@/types/commerce";
import { handleError } from "@/lib/error-handler";

export const CommerceService = {
  // ==========================================
  // 1. المنتجات
  // ==========================================
  getProducts: async (
    storeId: number,
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<Product>> => {
    try {
      const { data } = await apiClient.get('/commerce/products', {
        params: { store_id: storeId, skip, limit },
      });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب المنتجات');
    }
  },

  getProduct: async (productId: number): Promise<Product> => {
    try {
      const { data } = await apiClient.get(`/commerce/products/${productId}`);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب المنتج');
    }
  },

  // ==========================================
  // 2. الطلبات
  // ==========================================
  checkout: async (payload: CheckoutRequest): Promise<CheckoutResponse> => {
    try {
      const { data } = await apiClient.post('/commerce/checkout', payload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل إتمام الشراء');
    }
  },

  getOrders: async (
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<Order>> => {
    try {
      const { data } = await apiClient.get('/commerce/orders/me', {
        params: { skip, limit },
      });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب الطلبات');
    }
  },

  getOrder: async (orderId: number): Promise<Order> => {
    try {
      const { data } = await apiClient.get(`/commerce/orders/${orderId}`);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب تفاصيل الطلب');
    }
  },

  // ==========================================
  // 3. العناوين
  // ==========================================
  getAddresses: async (): Promise<Address[]> => {
    try {
      const { data } = await apiClient.get('/commerce/addresses');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب العناوين');
    }
  },

  createAddress: async (payload: Omit<Address, 'id' | 'user_id' | 'created_at'>): Promise<Address> => {
    try {
      const { data } = await apiClient.post('/commerce/addresses', payload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل إنشاء العنوان');
    }
  },

  // ==========================================
  // 4. الدفع
  // ==========================================
  createPaymentRequest: async (orderId: number, paymentMethod: string): Promise<PaymentRequest> => {
    try {
      const { data } = await apiClient.post('/commerce/payment-request', {
        order_id: orderId,
        payment_method: paymentMethod,
      });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل طلب الدفع');
    }
  },

  confirmAgentPayment: async (agentCode: string): Promise<Order> => {
    try {
      const { data } = await apiClient.post('/commerce/payment/agent/confirm', {
        agent_code: agentCode,
      });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل تأكيد الدفع عبر الوكيل');
    }
  },

  // ==========================================
  // 5. الإحالة (Affiliate)
  // ==========================================
  getAffiliateTree: async (): Promise<AffiliateTree> => {
    try {
      const { data } = await apiClient.get('/commerce/affiliate/tree');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب شجرة الإحالة');
    }
  },

  getCommissions: async (
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<Commission>> => {
    try {
      const { data } = await apiClient.get('/commerce/affiliate/commissions', {
        params: { skip, limit },
      });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب العمولات');
    }
  },

  releaseCommissions: async (): Promise<void> => {
    try {
      await apiClient.post('/commerce/affiliate/commissions/release');
    } catch (error) {
      throw handleError(error, 'فشل تحرير العمولات');
    }
  },

  setAffiliateSponsor: async (sponsorCode: string): Promise<AffiliateTree> => {
    try {
      const { data } = await apiClient.post('/commerce/affiliate/link', {
        sponsor_code: sponsorCode,
      });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل ربط الداعي');
    }
  },

  // ==========================================
  // 6. المحفظة (للتحقق من الرصيد)
  // ==========================================
  getWallet: async (): Promise<WalletBalance> => {
    try {
      const { data } = await apiClient.get('/finance/balances');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب رصيد المحفظة');
    }
  },
};