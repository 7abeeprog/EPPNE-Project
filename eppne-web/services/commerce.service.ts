// services/commerce.service.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";

type StoreCreate = components['schemas']['StoreCreate'];
type StoreResponse = components['schemas']['StoreResponse'];
type ProductCreate = components['schemas']['ProductCreate'];
type ProductResponse = components['schemas']['ProductResponse'];
type CheckoutRequest = components['schemas']['CheckoutRequest'];
type OrderResponse = components['schemas']['OrderResponse'];
type PaymentRequestCreate = components['schemas']['PaymentRequestCreate'];
type PaymentRequestResponse = components['schemas']['PaymentRequestResponse'];
type AgentConfirmPayment = components['schemas']['AgentConfirmPayment'];
type AffiliateTreeResponse = components['schemas']['AffiliateTreeResponse'];
type CommissionResponse = components['schemas']['CommissionResponse'];

export const CommerceService = {
  // ==========================================
  // 1. المتاجر (Stores)
  // ==========================================
  /**
   * إنشاء متجر جديد
   * POST /commerce/commerce/stores
   */
  createStore: async (data: StoreCreate): Promise<StoreResponse> => {
    try {
      const { data: result } = await apiClient.post<StoreResponse>("/commerce/commerce/stores", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المتجر");
    }
  },

  // ==========================================
  // 2. المنتجات (Products)
  // ==========================================
  /**
   * جلب قائمة المنتجات
   * GET /commerce/commerce/products
   */
  listProducts: async (params: { store_id: number; skip?: number; limit?: number }): Promise<ProductResponse[]> => {
    try {
      const { data } = await apiClient.get<ProductResponse[]>("/commerce/commerce/products", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المنتجات");
    }
  },

  /**
   * إنشاء منتج جديد
   * POST /commerce/commerce/products
   */
  createProduct: async (data: ProductCreate): Promise<ProductResponse> => {
    try {
      const { data: result } = await apiClient.post<ProductResponse>("/commerce/commerce/products", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المنتج");
    }
  },

  // ==========================================
  // 3. الطلبات (Orders)
  // ==========================================
  /**
   * إتمام عملية الشراء (Checkout)
   * POST /commerce/commerce/checkout
   */
  checkout: async (data: CheckoutRequest): Promise<OrderResponse> => {
    try {
      const { data: result } = await apiClient.post<OrderResponse>("/commerce/commerce/checkout", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إتمام الشراء");
    }
  },

  /**
   * جلب طلباتي
   * GET /commerce/commerce/orders/me
   */
  getMyOrders: async (): Promise<OrderResponse[]> => {
    try {
      const { data } = await apiClient.get<OrderResponse[]>("/commerce/commerce/orders/me", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الطلبات");
    }
  },

  // ==========================================
  // 4. نظام الإحالات (Affiliate)
  // ==========================================
  /**
   * تعيين الراعي (Sponsor)
   * POST /commerce/commerce/affiliate/link
   */
  setAffiliateSponsor: async (sponsorCode: string): Promise<AffiliateTreeResponse> => {
    try {
      const { data: result } = await apiClient.post<AffiliateTreeResponse>(
        "/commerce/commerce/affiliate/link",
        undefined,
        {
          params: { sponsor_code: sponsorCode },
          withCredentials: true,
        }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تعيين الراعي");
    }
  },

  /**
   * جلب عمولاتي
   * GET /commerce/commerce/affiliate/commissions
   */
  getMyCommissions: async (): Promise<CommissionResponse[]> => {
    try {
      const { data } = await apiClient.get<CommissionResponse[]>("/commerce/commerce/affiliate/commissions", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب العمولات");
    }
  },

  /**
   * تحرير العمولات المستحقة
   * POST /commerce/commerce/affiliate/commissions/release
   */
  releaseMyCommissions: async (): Promise<void> => {
    try {
      await apiClient.post("/commerce/commerce/affiliate/commissions/release", undefined, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل تحرير العمولات");
    }
  },

  // ==========================================
  // 5. الدفع (Payment)
  // ==========================================
  /**
   * إنشاء طلب دفع
   * POST /commerce/commerce/payment-request
   */
  createPaymentRequest: async (data: PaymentRequestCreate): Promise<PaymentRequestResponse> => {
    try {
      const { data: result } = await apiClient.post<PaymentRequestResponse>("/commerce/commerce/payment-request", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل طلب الدفع");
    }
  },

  /**
   * تأكيد الدفع عبر الوكيل
   * POST /commerce/commerce/payment/agent/confirm
   */
  confirmAgentPayment: async (data: AgentConfirmPayment): Promise<OrderResponse> => {
    try {
      const { data: result } = await apiClient.post<OrderResponse>("/commerce/commerce/payment/agent/confirm", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تأكيد الدفع عبر الوكيل");
    }
  },

  /**
   * Webhook من بوابة الفيزا (خارجي، لا يحتاج توكن)
   * POST /commerce/commerce/payment/visa/webhook
   */
  visaWebhook: async (payload: any, signature: string): Promise<void> => {
    try {
      await apiClient.post("/commerce/commerce/payment/visa/webhook", payload, {
        headers: { signature },
      });
    } catch (error) {
      throw handleError(error, "فشل معالجة Webhook");
    }
  },

  /**
   * جلب حالة الدفع لطلب معين
   * GET /commerce/commerce/payment/status/{order_id}
   */
  getPaymentStatus: async (orderId: number): Promise<any> => {
    try {
      const { data } = await apiClient.get(`/commerce/commerce/payment/status/${orderId}`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب حالة الدفع");
    }
  },
};