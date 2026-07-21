// services/sovereign-entities.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

type SovereignEntityCreate = components['schemas']['SovereignEntityCreate'];
type SovereignEntityResponse = components['schemas']['SovereignEntityResponse'];
type SovereignEntityType = components['schemas']['SovereignEntityType'];
type KYBStatus = components['schemas']['KYBStatus'];
type EntityPageCreate = components['schemas']['EntityPageCreate'];
type EntityRepresentativeCreate = components['schemas']['EntityRepresentativeCreate'];
type EntityRepresentativeResponse = components['schemas']['EntityRepresentativeResponse'];
type KYBDocumentUpload = components['schemas']['KYBDocumentUpload'];
type KYBUpdateStatus = components['schemas']['KYBUpdateStatus'];
type PageTemplateCreate = components['schemas']['PageTemplateCreate'];
type PageTemplateResponse = components['schemas']['PageTemplateResponse'];
type PageComponentResponse = components['schemas']['PageComponentResponse'];
type EntityDepositRequest = components['schemas']['EntityDepositRequest'];
type EntityTransferRequest = components['schemas']['EntityTransferRequest'];

export const SovereignEntitiesService = {
  /**
   * جلب قائمة الكيانات مع التصفية
   * GET /sovereign-entities/
   * تدعم X-Tenant-ID
   */
  listEntities: async (
    params?: {
      entity_type?: SovereignEntityType | null;
      kyb_status?: KYBStatus | null;
      skip?: number;
      limit?: number;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<SovereignEntityResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<SovereignEntityResponse[]>("/sovereign-entities/", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الكيانات السيادية");
    }
  },

  /**
   * إنشاء كيان سيادي جديد
   * POST /sovereign-entities/
   * تدعم X-Tenant-ID
   */
  createEntity: async (data: SovereignEntityCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<SovereignEntityResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<SovereignEntityResponse>("/sovereign-entities/", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الكيان السيادي");
    }
  },

  /**
   * جلب كياناتي
   * GET /sovereign-entities/me
   */
  getMyEntities: async (): Promise<SovereignEntityResponse[]> => {
    try {
      const { data } = await apiClient.get<SovereignEntityResponse[]>("/sovereign-entities/me", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب كياناتي");
    }
  },

  /**
   * جلب تفاصيل كيان محدد
   * GET /sovereign-entities/{entity_id}
   */
  getEntity: async (entityId: number): Promise<SovereignEntityResponse> => {
    try {
      const id = Number(entityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      const { data } = await apiClient.get<SovereignEntityResponse>(`/sovereign-entities/${id}`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل الكيان");
    }
  },

  /**
   * حذف كيان (حذف منطقي افتراضيًا)
   * DELETE /sovereign-entities/{entity_id}
   */
  deleteEntity: async (entityId: number, soft: boolean = true): Promise<void> => {
    try {
      const id = Number(entityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      await apiClient.delete(`/sovereign-entities/${id}`, {
        params: { soft },
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل حذف الكيان");
    }
  },

  /**
   * جلب صفحة الكيان
   * GET /sovereign-entities/{entity_id}/page
   */
  getEntityPage: async (entityId: number): Promise<any> => {
    try {
      const id = Number(entityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      const { data } = await apiClient.get<any>(`/sovereign-entities/${id}/page`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب صفحة الكيان");
    }
  },

  /**
   * تحديث صفحة الكيان
   * PUT /sovereign-entities/{entity_id}/page
   */
  updateEntityPage: async (entityId: number, data: EntityPageCreate): Promise<void> => {
    try {
      const id = Number(entityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      await apiClient.put(`/sovereign-entities/${id}/page`, data, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل تحديث صفحة الكيان");
    }
  },

  /**
   * نشر صفحة الكيان (جعله عامًا)
   * POST /sovereign-entities/{entity_id}/page/publish
   */
  publishEntityPage: async (entityId: number): Promise<void> => {
    try {
      const id = Number(entityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      await apiClient.post(`/sovereign-entities/${id}/page/publish`, undefined, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل نشر صفحة الكيان");
    }
  },

  /**
   * جلب صفحة الكيان العامة (بدون مصادقة)
   * GET /sovereign-entities/public/{slug}
   */
  getPublicEntityPage: async (slug: string): Promise<any> => {
    try {
      const { data } = await apiClient.get<any>(`/sovereign-entities/public/${slug}`);
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب صفحة الكيان العامة");
    }
  },

  /**
   * جلب ممثلي الكيان
   * GET /sovereign-entities/{entity_id}/representatives
   */
  getRepresentatives: async (entityId: number): Promise<EntityRepresentativeResponse[]> => {
    try {
      const id = Number(entityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      const { data } = await apiClient.get<EntityRepresentativeResponse[]>(
        `/sovereign-entities/${id}/representatives`,
        { withCredentials: true }
      );
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب ممثلي الكيان");
    }
  },

  /**
   * إضافة ممثل جديد للكيان
   * POST /sovereign-entities/{entity_id}/representatives
   */
  addRepresentative: async (entityId: number, data: EntityRepresentativeCreate): Promise<EntityRepresentativeResponse> => {
    try {
      const id = Number(entityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      const { data: result } = await apiClient.post<EntityRepresentativeResponse>(
        `/sovereign-entities/${id}/representatives`,
        data,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إضافة الممثل");
    }
  },

  /**
   * إزالة ممثل من الكيان
   * DELETE /sovereign-entities/{entity_id}/representatives/{user_id}
   */
  removeRepresentative: async (entityId: number, userId: number): Promise<void> => {
    try {
      const eid = Number(entityId);
      const uid = Number(userId);
      if (isNaN(eid) || isNaN(uid)) throw new Error("معرف غير صحيح");
      await apiClient.delete(`/sovereign-entities/${eid}/representatives/${uid}`, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل إزالة الممثل");
    }
  },

  /**
   * رفع مستند KYB
   * POST /sovereign-entities/{entity_id}/kyb/documents
   */
  uploadKYBDocument: async (entityId: number, data: KYBDocumentUpload): Promise<Record<string, any>> => {
    try {
      const id = Number(entityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      const { data: result } = await apiClient.post<Record<string, any>>(
        `/sovereign-entities/${id}/kyb/documents`,
        data,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل رفع مستند KYB");
    }
  },

  /**
   * جلب مستندات KYB للكيان
   * GET /sovereign-entities/{entity_id}/kyb/documents
   */
  getKYBDocuments: async (entityId: number): Promise<any> => {
    try {
      const id = Number(entityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      const { data } = await apiClient.get<any>(`/sovereign-entities/${id}/kyb/documents`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب مستندات KYB");
    }
  },

  /**
   * مراجعة حالة KYB (للمشرفين)
   * PUT /sovereign-entities/{entity_id}/kyb/status
   */
  reviewKYB: async (entityId: number, data: KYBUpdateStatus): Promise<SovereignEntityResponse> => {
    try {
      const id = Number(entityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      const { data: result } = await apiClient.put<SovereignEntityResponse>(
        `/sovereign-entities/${id}/kyb/status`,
        data,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل مراجعة KYB");
    }
  },

  /**
   * جلب رصيد الكيان
   * GET /sovereign-entities/{entity_id}/balance
   */
  getEntityBalance: async (entityId: number): Promise<any> => {
    try {
      const id = Number(entityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      const { data } = await apiClient.get<any>(`/sovereign-entities/${id}/balance`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب رصيد الكيان");
    }
  },

  /**
   * تحويل من محفظة الكيان إلى عنوان خارجي
   * POST /sovereign-entities/{entity_id}/transfer
   * تدعم Idempotency-Key
   */
  transferFromEntity: async (
    entityId: number,
    data: EntityTransferRequest,
    headers?: { 'Idempotency-Key'?: string | null }
  ): Promise<void> => {
    try {
      const id = Number(entityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      const reqHeaders: Record<string, string> = {};
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      await apiClient.post(`/sovereign-entities/${id}/transfer`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل التحويل من الكيان");
    }
  },

  /**
   * إيداع في محفظة الكيان
   * POST /sovereign-entities/{entity_id}/deposit
   * تدعم Idempotency-Key
   */
  depositToEntity: async (
    entityId: number,
    data: EntityDepositRequest,
    headers?: { 'Idempotency-Key'?: string | null }
  ): Promise<Record<string, any>> => {
    try {
      const id = Number(entityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      const reqHeaders: Record<string, string> = {};
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<Record<string, any>>(
        `/sovereign-entities/${id}/deposit`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل الإيداع في الكيان");
    }
  },

  /**
   * جلب قوالب الصفحات
   * GET /sovereign-entities/templates
   * تدعم X-Tenant-ID
   */
  listTemplates: async (headers?: { 'X-Tenant-ID'?: number }): Promise<PageTemplateResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<PageTemplateResponse[]>("/sovereign-entities/templates", {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب قوالب الصفحات");
    }
  },

  /**
   * إنشاء قالب صفحة جديد
   * POST /sovereign-entities/templates
   * تدعم X-Tenant-ID
   */
  createPageTemplate: async (data: PageTemplateCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<PageTemplateResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<PageTemplateResponse>("/sovereign-entities/templates", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء قالب الصفحة");
    }
  },

  /**
   * جلب مكونات الصفحات المتاحة
   * GET /sovereign-entities/components
   * تدعم X-Tenant-ID
   */
  listComponents: async (headers?: { 'X-Tenant-ID'?: number }): Promise<PageComponentResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<PageComponentResponse[]>("/sovereign-entities/components", {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب مكونات الصفحات");
    }
  },

  /**
   * جلب شجرة الكيان (العلاقات بين الكيانات)
   * GET /sovereign-entities/{entity_id}/tree
   */
  getEntityTree: async (entityId: number): Promise<any> => {
    try {
      const id = Number(entityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      const { data } = await apiClient.get<any>(`/sovereign-entities/${id}/tree`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب شجرة الكيان");
    }
  },
};