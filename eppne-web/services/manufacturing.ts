// services/manufacturing.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

type ManufacturingFacilityCreate = components['schemas']['ManufacturingFacilityCreate'];
type ManufacturingFacilityResponse = components['schemas']['ManufacturingFacilityResponse'];
type ProductionLineCreate = components['schemas']['ProductionLineCreate'];
type ProductionLineResponse = components['schemas']['ProductionLineResponse'];
type ProductBlueprintCreate = components['schemas']['ProductBlueprintCreate'];
type ProductBlueprintResponse = components['schemas']['ProductBlueprintResponse'];
type ProductionBatchCreate = components['schemas']['ProductionBatchCreate'];
type ProductionBatchResponse = components['schemas']['ProductionBatchResponse'];
type StartProductionResponse = components['schemas']['StartProductionResponse'];
type RawMaterialBatchCreate = components['schemas']['RawMaterialBatchCreate'];
type RawMaterialBatchResponse = components['schemas']['RawMaterialBatchResponse'];
type MaterialConsumptionCreate = components['schemas']['MaterialConsumptionCreate'];
type ProductDigitalTwinResponse = components['schemas']['ProductDigitalTwinResponse'];
type QualityCertificateCreate = components['schemas']['QualityCertificateCreate'];
type QualityCertificateResponse = components['schemas']['QualityCertificateResponse'];
type PredictiveMaintenanceLogCreate = components['schemas']['PredictiveMaintenanceLogCreate'];
type PredictiveMaintenanceLogResponse = components['schemas']['PredictiveMaintenanceLogResponse'];
type SparePartCreate = components['schemas']['SparePartCreate'];
type SparePartResponse = components['schemas']['SparePartResponse'];
type SparePartRestock = components['schemas']['SparePartRestock'];

export const ManufacturingService = {
  /**
   * إنشاء مرفق تصنيع جديد
   * POST /manufacturing/manufacturing/facilities
   * تدعم X-Tenant-ID
   */
  createFacility: async (data: ManufacturingFacilityCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<ManufacturingFacilityResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<ManufacturingFacilityResponse>(
        "/manufacturing/manufacturing/facilities",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المرفق");
    }
  },

  /**
   * إضافة خط إنتاج داخل مرفق
   * POST /manufacturing/manufacturing/facilities/{facility_id}/lines
   */
  addProductionLine: async (facilityId: number, data: ProductionLineCreate): Promise<ProductionLineResponse> => {
    try {
      const id = Number(facilityId);
      if (isNaN(id)) throw new Error("معرف المرفق غير صحيح");
      const { data: result } = await apiClient.post<ProductionLineResponse>(
        `/manufacturing/manufacturing/facilities/${id}/lines`,
        data,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إضافة خط الإنتاج");
    }
  },

  /**
   * إنشاء مخطط منتج جديد
   * POST /manufacturing/manufacturing/blueprints
   * تدعم X-Tenant-ID
   */
  createBlueprint: async (data: ProductBlueprintCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<ProductBlueprintResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<ProductBlueprintResponse>(
        "/manufacturing/manufacturing/blueprints",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المخطط");
    }
  },

  /**
   * إنشاء دفعة إنتاج جديدة
   * POST /manufacturing/manufacturing/batches
   * تدعم X-Tenant-ID
   */
  createBatch: async (data: ProductionBatchCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<ProductionBatchResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<ProductionBatchResponse>(
        "/manufacturing/manufacturing/batches",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء دفعة الإنتاج");
    }
  },

  /**
   * بدء الإنتاج (تشغيل الدفعة)
   * POST /manufacturing/manufacturing/batches/{batch_id}/start
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  startProduction: async (
    batchId: number,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<StartProductionResponse> => {
    try {
      const id = Number(batchId);
      if (isNaN(id)) throw new Error("معرف الدفعة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<StartProductionResponse>(
        `/manufacturing/manufacturing/batches/${id}/start`,
        undefined,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل بدء الإنتاج");
    }
  },

  /**
   * جلب قائمة المواد الخام
   * GET /manufacturing/manufacturing/raw-materials
   * تدعم X-Tenant-ID
   */
  listRawMaterials: async (params?: { skip?: number; limit?: number }, headers?: { 'X-Tenant-ID'?: number }): Promise<RawMaterialBatchResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<RawMaterialBatchResponse[]>("/manufacturing/manufacturing/raw-materials", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المواد الخام");
    }
  },

  /**
   * تسجيل دفعة مواد خام جديدة
   * POST /manufacturing/manufacturing/raw-materials
   * تدعم X-Tenant-ID
   */
  registerRawMaterial: async (data: RawMaterialBatchCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<RawMaterialBatchResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<RawMaterialBatchResponse>(
        "/manufacturing/manufacturing/raw-materials",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تسجيل المواد الخام");
    }
  },

  /**
   * استهلاك مادة خام في دفعة إنتاج
   * POST /manufacturing/manufacturing/batches/{batch_id}/consume-material
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  consumeRawMaterial: async (
    batchId: number,
    data: MaterialConsumptionCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<void> => {
    try {
      const id = Number(batchId);
      if (isNaN(id)) throw new Error("معرف الدفعة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      await apiClient.post(
        `/manufacturing/manufacturing/batches/${id}/consume-material`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
    } catch (error) {
      throw handleError(error, "فشل استهلاك المادة الخام");
    }
  },

  /**
   * إنشاء توأم رقمي لمنتج
   * POST /manufacturing/manufacturing/product-items/{product_item_id}/digital-twin
   */
  createDigitalTwin: async (
    productItemId: number,
    params: { batch_id: number; production_line_id?: number | null }
  ): Promise<ProductDigitalTwinResponse> => {
    try {
      const id = Number(productItemId);
      if (isNaN(id)) throw new Error("معرف المنتج غير صحيح");
      const { data: result } = await apiClient.post<ProductDigitalTwinResponse>(
        `/manufacturing/manufacturing/product-items/${id}/digital-twin`,
        undefined,
        { params, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء التوأم الرقمي");
    }
  },

  /**
   * جلب التوأم الرقمي لمنتج
   * GET /manufacturing/manufacturing/product-items/{product_item_id}/digital-twin
   */
  getDigitalTwin: async (productItemId: number): Promise<ProductDigitalTwinResponse> => {
    try {
      const id = Number(productItemId);
      if (isNaN(id)) throw new Error("معرف المنتج غير صحيح");
      const { data } = await apiClient.get<ProductDigitalTwinResponse>(
        `/manufacturing/manufacturing/product-items/${id}/digital-twin`,
        { withCredentials: true }
      );
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب التوأم الرقمي");
    }
  },

  /**
   * إصدار شهادة جودة
   * POST /manufacturing/manufacturing/quality-certificates
   * تدعم X-Tenant-ID
   */
  issueQualityCertificate: async (data: QualityCertificateCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<QualityCertificateResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<QualityCertificateResponse>(
        "/manufacturing/manufacturing/quality-certificates",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إصدار شهادة الجودة");
    }
  },

  /**
   * جلب شهادات الجودة لكيان معين
   * GET /manufacturing/manufacturing/quality-certificates/{entity_type}/{entity_id}
   */
  getEntityCertificates: async (entityType: string, entityId: number): Promise<QualityCertificateResponse[]> => {
    try {
      const id = Number(entityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      const { data } = await apiClient.get<QualityCertificateResponse[]>(
        `/manufacturing/manufacturing/quality-certificates/${entityType}/${id}`,
        { withCredentials: true }
      );
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب شهادات الجودة");
    }
  },

  /**
   * تحليل الصيانة التنبؤية
   * POST /manufacturing/manufacturing/predictive-maintenance
   * تدعم X-Tenant-ID
   */
  analyzeMaintenance: async (data: PredictiveMaintenanceLogCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<PredictiveMaintenanceLogResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<PredictiveMaintenanceLogResponse>(
        "/manufacturing/manufacturing/predictive-maintenance",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحليل الصيانة التنبؤية");
    }
  },

  /**
   * جلب طلبات الصيانة المعلقة لخط إنتاج
   * GET /manufacturing/manufacturing/production-lines/{line_id}/pending-maintenance
   */
  getPendingMaintenance: async (lineId: number): Promise<PredictiveMaintenanceLogResponse[]> => {
    try {
      const id = Number(lineId);
      if (isNaN(id)) throw new Error("معرف خط الإنتاج غير صحيح");
      const { data } = await apiClient.get<PredictiveMaintenanceLogResponse[]>(
        `/manufacturing/manufacturing/production-lines/${id}/pending-maintenance`,
        { withCredentials: true }
      );
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب طلبات الصيانة المعلقة");
    }
  },

  /**
   * جدولة صيانة
   * POST /manufacturing/manufacturing/maintenance/{log_id}/schedule
   */
  scheduleMaintenance: async (logId: number, scheduledAt: string): Promise<void> => {
    try {
      const id = Number(logId);
      if (isNaN(id)) throw new Error("معرف طلب الصيانة غير صحيح");
      await apiClient.post(
        `/manufacturing/manufacturing/maintenance/${id}/schedule`,
        undefined,
        { params: { scheduled_at: scheduledAt }, withCredentials: true }
      );
    } catch (error) {
      throw handleError(error, "فشل جدولة الصيانة");
    }
  },

  /**
   * إنشاء قطعة غيار جديدة
   * POST /manufacturing/manufacturing/spare-parts
   * تدعم X-Tenant-ID
   */
  createSparePart: async (data: SparePartCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<SparePartResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<SparePartResponse>(
        "/manufacturing/manufacturing/spare-parts",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء قطعة الغيار");
    }
  },

  /**
   * جلب قائمة قطع الغيار
   * GET /manufacturing/manufacturing/spare-parts
   * تدعم X-Tenant-ID
   */
  listSpareParts: async (params?: { skip?: number; limit?: number }, headers?: { 'X-Tenant-ID'?: number }): Promise<SparePartResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<SparePartResponse[]>("/manufacturing/manufacturing/spare-parts", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب قطع الغيار");
    }
  },

  /**
   * إعادة تخزين قطعة غيار
   * POST /manufacturing/manufacturing/spare-parts/{part_id}/restock
   */
  restockSparePart: async (partId: number, data: SparePartRestock): Promise<SparePartResponse> => {
    try {
      const id = Number(partId);
      if (isNaN(id)) throw new Error("معرف قطعة الغيار غير صحيح");
      const { data: result } = await apiClient.post<SparePartResponse>(
        `/manufacturing/manufacturing/spare-parts/${id}/restock`,
        data,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إعادة تخزين قطعة الغيار");
    }
  },
};