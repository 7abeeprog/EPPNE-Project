// services/saas.service.ts
import { apiClient } from "@/lib/api-client";
import {
  ServiceCatalog,
  ServicePlan,
  TenantSubscription,
  Invoice,
  FeatureFlag,
  ServiceAccessStatus,
  PaginatedResponse,
  SaasDashboardStats,
  SubscribeRequest,
  UpdateSubscriptionRequest,
  CreateInvoiceRequest,
} from "@/types/saas";
import { handleError } from "@/lib/error-handler";

export const SaaSService = {
  // ==========================================
  // 1. لوحة التحكم
  // ==========================================
  getDashboardStats: async (): Promise<SaasDashboardStats> => {
    try {
      const { data } = await apiClient.get('/saas/dashboard/stats');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب إحصائيات لوحة التحكم');
    }
  },

  // ==========================================
  // 2. الخدمات
  // ==========================================
  getServices: async (): Promise<ServiceCatalog[]> => {
    try {
      const { data } = await apiClient.get('/saas/services');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب الخدمات');
    }
  },

  getServiceAccess: async (): Promise<ServiceAccessStatus[]> => {
    try {
      const { data } = await apiClient.get('/saas/service-access');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب صلاحيات الوصول');
    }
  },

  toggleServiceStatus: async (serviceId: number, isActive: boolean): Promise<ServiceCatalog> => {
    try {
      const { data } = await apiClient.put(`/saas/services/${serviceId}`, { is_active: isActive });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل تحديث حالة الخدمة');
    }
  },

  // ==========================================
  // 3. خطط التسعير
  // ==========================================
  getPlans: async (serviceId?: number): Promise<ServicePlan[]> => {
    try {
      const { data } = await apiClient.get('/saas/plans', {
        params: { service_id: serviceId },
      });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب خطط التسعير');
    }
  },

  createPlan: async (payload: Omit<ServicePlan, 'id' | 'created_at' | 'updated_at'>): Promise<ServicePlan> => {
    try {
      const { data } = await apiClient.post('/saas/plans', payload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل إنشاء الخطة');
    }
  },

  updatePlan: async (planId: number, payload: Partial<ServicePlan>): Promise<ServicePlan> => {
    try {
      const { data } = await apiClient.put(`/saas/plans/${planId}`, payload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل تحديث الخطة');
    }
  },

  deletePlan: async (planId: number): Promise<void> => {
    try {
      await apiClient.delete(`/saas/plans/${planId}`);
    } catch (error) {
      throw handleError(error, 'فشل حذف الخطة');
    }
  },

  // ==========================================
  // 4. الاشتراكات
  // ==========================================
  getSubscriptions: async (skip: number = 0, limit: number = 20, status?: string): Promise<PaginatedResponse<TenantSubscription>> => {
    try {
      const { data } = await apiClient.get('/saas/subscriptions', {
        params: { skip, limit, status },
      });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب الاشتراكات');
    }
  },

  subscribe: async (payload: SubscribeRequest): Promise<TenantSubscription> => {
    try {
      const { data } = await apiClient.post('/saas/subscriptions', payload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل الاشتراك');
    }
  },

  updateSubscription: async (subscriptionId: number, payload: UpdateSubscriptionRequest): Promise<TenantSubscription> => {
    try {
      const { data } = await apiClient.put(`/saas/subscriptions/${subscriptionId}`, payload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل تحديث الاشتراك');
    }
  },

  cancelSubscription: async (subscriptionId: number): Promise<void> => {
    try {
      await apiClient.post(`/saas/subscriptions/${subscriptionId}/cancel`);
    } catch (error) {
      throw handleError(error, 'فشل إلغاء الاشتراك');
    }
  },

  renewSubscription: async (subscriptionId: number): Promise<void> => {
    try {
      await apiClient.post(`/saas/subscriptions/${subscriptionId}/renew`);
    } catch (error) {
      throw handleError(error, 'فشل تجديد الاشتراك');
    }
  },

  // ==========================================
  // 5. الفواتير
  // ==========================================
  getInvoices: async (skip: number = 0, limit: number = 20): Promise<PaginatedResponse<Invoice>> => {
    try {
      const { data } = await apiClient.get('/saas/invoices', {
        params: { skip, limit },
      });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب الفواتير');
    }
  },

  createInvoice: async (payload: CreateInvoiceRequest): Promise<Invoice> => {
    try {
      const { data } = await apiClient.post('/saas/invoices', payload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل إنشاء الفاتورة');
    }
  },

  payInvoice: async (invoiceId: number): Promise<Invoice> => {
    try {
      const { data } = await apiClient.post(`/saas/invoices/${invoiceId}/pay`);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل دفع الفاتورة');
    }
  },

  cancelInvoice: async (invoiceId: number): Promise<void> => {
    try {
      await apiClient.post(`/saas/invoices/${invoiceId}/cancel`);
    } catch (error) {
      throw handleError(error, 'فشل إلغاء الفاتورة');
    }
  },

  // ==========================================
  // 6. رايات الميزات
  // ==========================================
  getFeatureFlags: async (serviceCode?: string): Promise<FeatureFlag[]> => {
    try {
      const { data } = await apiClient.get('/saas/feature-flags', {
        params: { service_code: serviceCode },
      });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب رايات الميزات');
    }
  },

  toggleFeatureFlag: async (serviceCode: string, featureKey: string, enabled: boolean): Promise<void> => {
    try {
      await apiClient.post(`/saas/feature-flags/${serviceCode}/${featureKey}`, null, {
        params: { enabled },
      });
    } catch (error) {
      throw handleError(error, 'فشل تحديث الميزة');
    }
  },
};