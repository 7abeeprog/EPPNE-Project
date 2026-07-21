// services/marketplace.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

type MarketplaceServiceCreate = components['schemas']['MarketplaceServiceCreate'];
type MarketplaceServiceResponse = components['schemas']['MarketplaceServiceResponse'];
type ServiceLicensePurchase = components['schemas']['ServiceLicensePurchase'];
type ServiceLicenseResponse = components['schemas']['ServiceLicenseResponse'];
type DeploymentStatusUpdate = components['schemas']['DeploymentStatusUpdate'];
type ServiceAddonCreate = components['schemas']['ServiceAddonCreate'];
type ServiceAddonResponse = components['schemas']['ServiceAddonResponse'];
type CustomizationRequestCreate = components['schemas']['CustomizationRequestCreate'];
type CustomizationRequestResponse = components['schemas']['CustomizationRequestResponse'];

export const MarketplaceService = {
  // ==========================================
  // 1. خدمات السوق (Services)
  // ==========================================
  /**
   * جلب قائمة الخدمات المتاحة
   * GET /marketplace/marketplace/services
   * تدعم X-Tenant-ID
   */
  listServices: async (
    params?: {
      service_type?: string | null;
      featured?: boolean | null;
      skip?: number;
      limit?: number;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<MarketplaceServiceResponse[]> => {
    try {
      const { data } = await apiClient.get<MarketplaceServiceResponse[]>("/marketplace/marketplace/services", {
        params,
        headers,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب خدمات السوق");
    }
  },

  /**
   * إنشاء خدمة جديدة في السوق
   * POST /marketplace/marketplace/services
   * تدعم X-Tenant-ID
   */
  createService: async (data: MarketplaceServiceCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<MarketplaceServiceResponse> => {
    try {
      const { data: result } = await apiClient.post<MarketplaceServiceResponse>(
        "/marketplace/marketplace/services",
        data,
        { headers, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الخدمة");
    }
  },

  /**
   * جلب تفاصيل خدمة محددة
   * GET /marketplace/marketplace/services/{service_id}
   */
  getService: async (serviceId: number): Promise<MarketplaceServiceResponse> => {
    try {
      const id = Number(serviceId);
      if (isNaN(id)) throw new Error("معرف الخدمة غير صحيح");
      const { data } = await apiClient.get<MarketplaceServiceResponse>(`/marketplace/marketplace/services/${id}`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل الخدمة");
    }
  },

  /**
   * نشر خدمة (تفعيلها للجمهور)
   * PUT /marketplace/marketplace/services/{service_id}/publish
   */
  publishService: async (serviceId: number): Promise<void> => {
    try {
      const id = Number(serviceId);
      if (isNaN(id)) throw new Error("معرف الخدمة غير صحيح");
      await apiClient.put(`/marketplace/marketplace/services/${id}/publish`, undefined, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل نشر الخدمة");
    }
  },

  /**
   * إلغاء نشر خدمة (إخفائها)
   * PUT /marketplace/marketplace/services/{service_id}/unpublish
   */
  unpublishService: async (serviceId: number): Promise<void> => {
    try {
      const id = Number(serviceId);
      if (isNaN(id)) throw new Error("معرف الخدمة غير صحيح");
      await apiClient.put(`/marketplace/marketplace/services/${id}/unpublish`, undefined, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل إلغاء نشر الخدمة");
    }
  },

  // ==========================================
  // 2. شراء الخدمات والتراخيص (Licenses)
  // ==========================================
  /**
   * شراء خدمة (الحصول على ترخيص)
   * POST /marketplace/marketplace/purchase
   * تدعم X-Tenant-ID
   */
  purchaseService: async (data: ServiceLicensePurchase, headers?: { 'X-Tenant-ID'?: number }): Promise<ServiceLicenseResponse> => {
    try {
      const { data: result } = await apiClient.post<ServiceLicenseResponse>(
        "/marketplace/marketplace/purchase",
        data,
        { headers, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل شراء الخدمة");
    }
  },

  /**
   * جلب تراخيصي
   * GET /marketplace/marketplace/licenses/me
   */
  getMyLicenses: async (params?: { skip?: number; limit?: number }): Promise<ServiceLicenseResponse[]> => {
    try {
      const { data } = await apiClient.get<ServiceLicenseResponse[]>("/marketplace/marketplace/licenses/me", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تراخيصي");
    }
  },

  /**
   * جلب حالة النشر لترخيص معين
   * GET /marketplace/marketplace/licenses/{license_id}/status
   */
  getDeploymentStatus: async (licenseId: number): Promise<any> => {
    try {
      const id = Number(licenseId);
      if (isNaN(id)) throw new Error("معرف الترخيص غير صحيح");
      const { data } = await apiClient.get<any>(`/marketplace/marketplace/licenses/${id}/status`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب حالة النشر");
    }
  },

  /**
   * تجديد ترخيص
   * POST /marketplace/marketplace/licenses/{license_id}/renew
   */
  renewLicense: async (licenseId: number): Promise<ServiceLicenseResponse> => {
    try {
      const id = Number(licenseId);
      if (isNaN(id)) throw new Error("معرف الترخيص غير صحيح");
      const { data: result } = await apiClient.post<ServiceLicenseResponse>(
        `/marketplace/marketplace/licenses/${id}/renew`,
        undefined,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تجديد الترخيص");
    }
  },

  // ==========================================
  // 3. الإضافات (Add-ons)
  // ==========================================
  /**
   * جلب قائمة الإضافات
   * GET /marketplace/marketplace/addons
   * تدعم X-Tenant-ID
   */
  listAddons: async (params?: { compatible_with?: string | null }, headers?: { 'X-Tenant-ID'?: number }): Promise<ServiceAddonResponse[]> => {
    try {
      const { data } = await apiClient.get<ServiceAddonResponse[]>("/marketplace/marketplace/addons", {
        params,
        headers,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الإضافات");
    }
  },

  /**
   * إنشاء إضافة جديدة
   * POST /marketplace/marketplace/addons
   * تدعم X-Tenant-ID
   */
  createAddon: async (data: ServiceAddonCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<ServiceAddonResponse> => {
    try {
      const { data: result } = await apiClient.post<ServiceAddonResponse>(
        "/marketplace/marketplace/addons",
        data,
        { headers, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الإضافة");
    }
  },

  /**
   * شراء إضافة لترخيص معين
   * POST /marketplace/marketplace/licenses/{license_id}/addons/{addon_id}
   */
  purchaseAddon: async (licenseId: number, addonId: number): Promise<ServiceLicenseResponse> => {
    try {
      const lid = Number(licenseId);
      const aid = Number(addonId);
      if (isNaN(lid) || isNaN(aid)) throw new Error("معرف غير صحيح");
      const { data: result } = await apiClient.post<ServiceLicenseResponse>(
        `/marketplace/marketplace/licenses/${lid}/addons/${aid}`,
        undefined,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل شراء الإضافة");
    }
  },

  // ==========================================
  // 4. طلبات التخصيص (Customization)
  // ==========================================
  /**
   * طلب تخصيص خدمة
   * POST /marketplace/marketplace/licenses/{license_id}/customize
   */
  requestCustomization: async (licenseId: number, data: CustomizationRequestCreate): Promise<CustomizationRequestResponse> => {
    try {
      const id = Number(licenseId);
      if (isNaN(id)) throw new Error("معرف الترخيص غير صحيح");
      const { data: result } = await apiClient.post<CustomizationRequestResponse>(
        `/marketplace/marketplace/licenses/${id}/customize`,
        data,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل طلب التخصيص");
    }
  },

  /**
   * جلب طلبات التخصيص لترخيص معين
   * GET /marketplace/marketplace/licenses/{license_id}/customizations
   */
  getCustomizationRequests: async (licenseId: number): Promise<CustomizationRequestResponse[]> => {
    try {
      const id = Number(licenseId);
      if (isNaN(id)) throw new Error("معرف الترخيص غير صحيح");
      const { data } = await apiClient.get<CustomizationRequestResponse[]>(
        `/marketplace/marketplace/licenses/${id}/customizations`,
        { withCredentials: true }
      );
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب طلبات التخصيص");
    }
  },

  // ==========================================
  // 5. Webhook للنشر (للـ CI/CD)
  // ==========================================
  /**
   * Webhook لتحديث حالة النشر (يُستخدم داخلياً)
   * POST /marketplace/marketplace/webhook/deployment/{license_id}
   * يتطلب x-api-key في الهيدر
   */
  deploymentWebhook: async (licenseId: number, data: DeploymentStatusUpdate, apiKey: string): Promise<void> => {
    try {
      const id = Number(licenseId);
      if (isNaN(id)) throw new Error("معرف الترخيص غير صحيح");
      await apiClient.post(
        `/marketplace/marketplace/webhook/deployment/${id}`,
        data,
        {
          headers: { 'x-api-key': apiKey },
          withCredentials: true,
        }
      );
    } catch (error) {
      throw handleError(error, "فشل تحديث حالة النشر");
    }
  },
};