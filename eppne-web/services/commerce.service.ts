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
   * POST /commerce/stores
   */
  createStore: async (data: StoreCreate): Promise<StoreResponse> => {
    try {
      const { data: result } = await apiClient.post<StoreResponse>("/commerce/stores", data, {
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
   * GET /commerce/products
   */
  listProducts: async (params: { store_id: number; skip?: number; limit?: number }): Promise<ProductResponse[]> => {
    try {
      const { data } = await apiClient.get<ProductResponse[]>("/commerce/products", {
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
   * POST /commerce/products
   */
  createProduct: async (data: ProductCreate): Promise<ProductResponse> => {
    try {
      const { data: result } = await apiClient.post<ProductResponse>("/commerce/products", data, {
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
   * POST /commerce/checkout
   */
  checkout: async (data: CheckoutRequest): Promise<OrderResponse> => {
    try {
      const { data: result } = await apiClient.post<OrderResponse>("/commerce/checkout", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إتمام الشراء");
    }
  },

  /**
   * جلب طلباتي
   * GET /commerce/orders/me
   */
  getMyOrders: async (): Promise<OrderResponse[]> => {
    try {
      const { data } = await apiClient.get<OrderResponse[]>("/commerce/orders/me", {
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
   * POST /commerce/affiliate/link
   */
  setAffiliateSponsor: async (sponsorCode: string): Promise<AffiliateTreeResponse> => {
    try {
      const { data: result } = await apiClient.post<AffiliateTreeResponse>(
        "/commerce/affiliate/link",
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
   * GET /commerce/affiliate/commissions
   */
  getMyCommissions: async (): Promise<CommissionResponse[]> => {
    try {
      const { data } = await apiClient.get<CommissionResponse[]>("/commerce/affiliate/commissions", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب العمولات");
    }
  },

  /**
   * تحرير العمولات المستحقة
   * POST /commerce/affiliate/commissions/release
   */
  releaseMyCommissions: async (): Promise<void> => {
    try {
      await apiClient.post("/commerce/affiliate/commissions/release", undefined, {
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
   * POST /commerce/payment-request
   */
  createPaymentRequest: async (data: PaymentRequestCreate): Promise<PaymentRequestResponse> => {
    try {
      const { data: result } = await apiClient.post<PaymentRequestResponse>("/commerce/payment-request", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل طلب الدفع");
    }
  },

  /**
   * تأكيد الدفع عبر الوكيل
   * POST /commerce/payment/agent/confirm
   */
  confirmAgentPayment: async (data: AgentConfirmPayment): Promise<OrderResponse> => {
    try {
      const { data: result } = await apiClient.post<OrderResponse>("/commerce/payment/agent/confirm", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تأكيد الدفع عبر الوكيل");
    }
  },

  /**
   * Webhook من بوابة الفيزا (خارجي، لا يحتاج توكن)
   * POST /commerce/payment/visa/webhook
   */
  visaWebhook: async (payload: any, signature: string): Promise<void> => {
    try {
      await apiClient.post("/commerce/payment/visa/webhook", payload, {
        headers: { signature },
      });
    } catch (error) {
      throw handleError(error, "فشل معالجة Webhook");
    }
  },

  /**
   * جلب حالة الدفع لطلب معين
   * GET /commerce/payment/status/{order_id}
   */
  getPaymentStatus: async (orderId: number): Promise<any> => {
    try {
      const { data } = await apiClient.get(`/commerce/payment/status/${orderId}`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب حالة الدفع");
    }
  },
};