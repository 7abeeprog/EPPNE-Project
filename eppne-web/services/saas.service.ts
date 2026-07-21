// services/saas.service.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";

type ServiceCatalogResponse = components['schemas']['ServiceCatalogResponse'];
type ServiceCatalogCreate = components['schemas']['ServiceCatalogCreate'];
type ServicePlanResponse = components['schemas']['ServicePlanResponse'];
type ServicePlanCreate = components['schemas']['ServicePlanCreate'];
type TenantSubscriptionResponse = components['schemas']['TenantSubscriptionResponse'];
type PaginatedResponse_TenantSubscriptionResponse_ = components['schemas']['PaginatedResponse_TenantSubscriptionResponse_'];
type InvoiceResponse = components['schemas']['InvoiceResponse'];
type PaginatedResponse_InvoiceResponse_ = components['schemas']['PaginatedResponse_InvoiceResponse_'];
type ServiceAccessStatus = components['schemas']['ServiceAccessStatus'];
type CheckAccessResponse = components['schemas']['CheckAccessResponse'];

export const SaaSService = {
  // ==========================================
  // 1. الخدمات (Services)
  // ==========================================
  /**
   * جلب جميع الخدمات المتاحة (للمشرفين فقط)
   * GET /saas/saas/services
   */
  listServices: async (): Promise<ServiceCatalogResponse[]> => {
    try {
      const { data } = await apiClient.get<ServiceCatalogResponse[]>("/saas/saas/services", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الخدمات");
    }
  },

  /**
   * إنشاء خدمة جديدة (للمشرفين فقط)
   * POST /saas/saas/services
   */
  createService: async (data: ServiceCatalogCreate): Promise<ServiceCatalogResponse> => {
    try {
      const { data: result } = await apiClient.post<ServiceCatalogResponse>("/saas/saas/services", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الخدمة");
    }
  },

  /**
   * جلب تفاصيل خدمة محددة
   * GET /saas/saas/services/{service_id}
   */
  getService: async (serviceId: number): Promise<ServiceCatalogResponse> => {
    try {
      const id = Number(serviceId);
      if (isNaN(id)) throw new Error("معرف الخدمة غير صحيح");
      const { data } = await apiClient.get<ServiceCatalogResponse>(`/saas/saas/services/${id}`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل الخدمة");
    }
  },

  /**
   * جلب خطط خدمة معينة
   * GET /saas/saas/services/{service_id}/plans
   */
  listServicePlans: async (serviceId: number): Promise<ServicePlanResponse[]> => {
    try {
      const id = Number(serviceId);
      if (isNaN(id)) throw new Error("معرف الخدمة غير صحيح");
      const { data } = await apiClient.get<ServicePlanResponse[]>(`/saas/saas/services/${id}/plans`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب خطط الخدمة");
    }
  },

  // ==========================================
  // 2. خطط التسعير (Plans)
  // ==========================================
  /**
   * إنشاء خطة تسعير جديدة (للمشرفين فقط)
   * POST /saas/saas/plans
   */
  createPlan: async (data: ServicePlanCreate): Promise<ServicePlanResponse> => {
    try {
      const { data: result } = await apiClient.post<ServicePlanResponse>("/saas/saas/plans", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء خطة التسعير");
    }
  },

  // ==========================================
  // 3. الاشتراكات (Subscriptions)
  // ==========================================
  /**
   * جلب اشتراكاتي (مع Pagination)
   * GET /saas/saas/subscriptions
   */
  getMySubscriptions: async (params?: { skip?: number; limit?: number }): Promise<PaginatedResponse_TenantSubscriptionResponse_> => {
    try {
      const { data } = await apiClient.get<PaginatedResponse_TenantSubscriptionResponse_>(
        "/saas/saas/subscriptions",
        { params, withCredentials: true }
      );
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب اشتراكاتي");
    }
  },

  /**
   * الاشتراك في خطة جديدة
   * POST /saas/saas/subscriptions/{plan_id}
   */
  subscribeToPlan: async (planId: number): Promise<TenantSubscriptionResponse> => {
    try {
      const id = Number(planId);
      if (isNaN(id)) throw new Error("معرف الخطة غير صحيح");
      const { data: result } = await apiClient.post<TenantSubscriptionResponse>(
        `/saas/saas/subscriptions/${id}`,
        undefined,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل الاشتراك في الخطة");
    }
  },

  /**
   * إلغاء الاشتراك (إيقاف التجديد التلقائي)
   * PUT /saas/saas/subscriptions/{subscription_id}/cancel
   */
  cancelSubscription: async (subscriptionId: number): Promise<TenantSubscriptionResponse> => {
    try {
      const id = Number(subscriptionId);
      if (isNaN(id)) throw new Error("معرف الاشتراك غير صحيح");
      const { data: result } = await apiClient.put<TenantSubscriptionResponse>(
        `/saas/saas/subscriptions/${id}/cancel`,
        undefined,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إلغاء الاشتراك");
    }
  },

  /**
   * جلب حالة الاشتراك
   * GET /saas/saas/subscriptions/{subscription_id}/status
   */
  getSubscriptionStatus: async (subscriptionId: number): Promise<any> => {
    try {
      const id = Number(subscriptionId);
      if (isNaN(id)) throw new Error("معرف الاشتراك غير صحيح");
      const { data } = await apiClient.get<any>(`/saas/saas/subscriptions/${id}/status`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب حالة الاشتراك");
    }
  },

  // ==========================================
  // 4. حالة الوصول للخدمات (Access)
  // ==========================================
  /**
   * عرض جميع الخدمات مع حالة الوصول للمستأجر الحالي
   * GET /saas/saas/access
   */
  getServicesAccess: async (): Promise<ServiceAccessStatus[]> => {
    try {
      const { data } = await apiClient.get<ServiceAccessStatus[]>("/saas/saas/access", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب حالة الوصول للخدمات");
    }
  },

  /**
   * التحقق من صلاحية خدمة محددة
   * GET /saas/saas/access/{service_code}
   */
  checkServiceAccess: async (serviceCode: string): Promise<CheckAccessResponse> => {
    try {
      const { data } = await apiClient.get<CheckAccessResponse>(`/saas/saas/access/${serviceCode}`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل التحقق من صلاحية الخدمة");
    }
  },

  // ==========================================
  // 5. الفواتير (Invoices)
  // ==========================================
  /**
   * جلب فواتيري (مع Pagination)
   * GET /saas/saas/invoices
   */
  getMyInvoices: async (
    params?: { skip?: number; limit?: number; status?: string | null }
  ): Promise<PaginatedResponse_InvoiceResponse_> => {
    try {
      const { data } = await apiClient.get<PaginatedResponse_InvoiceResponse_>("/saas/saas/invoices", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب فواتيري");
    }
  },

  /**
   * جلب تفاصيل فاتورة محددة
   * GET /saas/saas/invoices/{invoice_id}
   */
  getInvoice: async (invoiceId: number): Promise<InvoiceResponse> => {
    try {
      const id = Number(invoiceId);
      if (isNaN(id)) throw new Error("معرف الفاتورة غير صحيح");
      const { data } = await apiClient.get<InvoiceResponse>(`/saas/saas/invoices/${id}`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل الفاتورة");
    }
  },

  /**
   * دفع فاتورة مستحقة باستخدام المحفظة السيادية
   * POST /saas/saas/invoices/{invoice_id}/pay
   */
  payInvoice: async (invoiceId: number): Promise<InvoiceResponse> => {
    try {
      const id = Number(invoiceId);
      if (isNaN(id)) throw new Error("معرف الفاتورة غير صحيح");
      const { data: result } = await apiClient.post<InvoiceResponse>(`/saas/saas/invoices/${id}/pay`, undefined, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل دفع الفاتورة");
    }
  },

  // ==========================================
  // 6. رايات الميزات (Feature Flags) - للمشرفين
  // ==========================================
  /**
   * جلب جميع رايات الميزات للمستأجر (للمشرفين فقط)
   * GET /saas/saas/feature-flags
   */
  listFeatureFlags: async (): Promise<any> => {
    try {
      const { data } = await apiClient.get<any>("/saas/saas/feature-flags", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب رايات الميزات");
    }
  },

  /**
   * تفعيل/تعطيل ميزة محددة (للمشرفين فقط)
   * POST /saas/saas/feature-flags/{service_code}/{feature_key}
   */
  toggleFeatureFlag: async (serviceCode: string, featureKey: string, enabled: boolean): Promise<void> => {
    try {
      await apiClient.post(`/saas/saas/feature-flags/${serviceCode}/${featureKey}`, undefined, {
        params: { enabled },
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل تحديث حالة الميزة");
    }
  },

  // ==========================================
  // 7. إدارة المشرفين (Admin)
  // ==========================================
  /**
   * جلب اشتراكات مستأجر محدد (للمشرفين فقط)
   * GET /saas/saas/admin/tenant/{tenant_id}/subscriptions
   */
  getTenantSubscriptionsAdmin: async (tenantId: number): Promise<any> => {
    try {
      const id = Number(tenantId);
      if (isNaN(id)) throw new Error("معرف المستأجر غير صحيح");
      const { data } = await apiClient.get<any>(`/saas/saas/admin/tenant/${id}/subscriptions`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب اشتراكات المستأجر");
    }
  },

  /**
   * لوحة تحكم SaaS (للمشرفين فقط)
   * GET /saas/saas/admin/dashboard
   */
  getSaaSDashboard: async (): Promise<any> => {
    try {
      const { data } = await apiClient.get<any>("/saas/saas/admin/dashboard", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب لوحة تحكم SaaS");
    }
  },

  /**
   * تشغيل تجديد الاشتراكات التلقائية يدوياً (للمشرفين فقط)
   * POST /saas/saas/admin/trigger-renewals
   */
  triggerRenewals: async (): Promise<void> => {
    try {
      await apiClient.post("/saas/saas/admin/trigger-renewals", undefined, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل تشغيل تجديد الاشتراكات");
    }
  },
};