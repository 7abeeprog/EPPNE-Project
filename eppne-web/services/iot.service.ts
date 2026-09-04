// services/iot.service.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

type SmartAssetCreate = components['schemas']['SmartAssetCreate'];
type SmartAssetResponse = components['schemas']['SmartAssetResponse'];
type SmartAssetUpdate = components['schemas']['SmartAssetUpdate'];
type UtilityGridCreate = components['schemas']['UtilityGridCreate'];
type UtilityGridResponse = components['schemas']['UtilityGridResponse'];
type UtilityReadingCreate = components['schemas']['UtilityReadingCreate'];
type UtilityReadingResponse = components['schemas']['UtilityReadingResponse'];
type CarbonSettlementRequest = components['schemas']['CarbonSettlementRequest'];
// api-types.ts لسه ما اتولّدش من openapi.json بعد إضافة CarbonSettlementResponse
// (توليد api-types.ts خطوة يدوية منفصلة، راجع PROGRESS_LOG.md - مشكلة drift موثقة).
type CarbonSettlementResponse = {
  status: string;
  message?: string | null;
  total_credits_settled?: number | null;
  monetary_value_added_mrusdt?: number | null;
  readings_processed?: number | null;
};
type MaintenanceLogCreate = components['schemas']['MaintenanceLogCreate'];
type MaintenanceLogResponse = components['schemas']['MaintenanceLogResponse'];

export const IoTService = {
  // ==========================================
  // 1. الأصول (Assets)
  // ==========================================
  /**
   * إنشاء أصل ذكي جديد
   * POST /iot/assets
   */
  createAsset: async (data: SmartAssetCreate): Promise<SmartAssetResponse> => {
    try {
      const { data: result } = await apiClient.post<SmartAssetResponse>("/iot/assets", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الأصل الذكي");
    }
  },

  /**
   * جلب قائمة أصولي الذكية
   * GET /iot/assets
   */
  listMyAssets: async (params?: { skip?: number; limit?: number }): Promise<SmartAssetResponse[]> => {
    try {
      const { data } = await apiClient.get<SmartAssetResponse[]>("/iot/assets", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الأصول الذكية");
    }
  },

  /**
   * جلب تفاصيل أصل ذكي محدد
   * GET /iot/assets/{asset_id}
   */
  getAsset: async (assetId: number): Promise<SmartAssetResponse> => {
    try {
      const id = Number(assetId);
      if (isNaN(id)) throw new Error("معرف الأصل غير صحيح");
      const { data } = await apiClient.get<SmartAssetResponse>(`/iot/assets/${id}`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل الأصل");
    }
  },

  /**
   * تحديث أصل ذكي
   * PATCH /iot/assets/{asset_id}
   */
  updateAsset: async (assetId: number, data: SmartAssetUpdate): Promise<SmartAssetResponse> => {
    try {
      const id = Number(assetId);
      if (isNaN(id)) throw new Error("معرف الأصل غير صحيح");
      const { data: result } = await apiClient.patch<SmartAssetResponse>(`/iot/assets/${id}`, data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث الأصل");
    }
  },

  // ==========================================
  // 2. الشبكات (Grids)
  // ==========================================
  /**
   * إنشاء شبكة مرافق جديدة
   * POST /iot/grids
   */
  createGrid: async (data: UtilityGridCreate): Promise<UtilityGridResponse> => {
    try {
      const { data: result } = await apiClient.post<UtilityGridResponse>("/iot/grids", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الشبكة");
    }
  },

  /**
   * جلب قائمة الشبكات
   * GET /iot/grids
   */
  listGrids: async (params?: { grid_type?: string | null; skip?: number; limit?: number }): Promise<UtilityGridResponse[]> => {
    try {
      const { data } = await apiClient.get<UtilityGridResponse[]>("/iot/grids", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الشبكات");
    }
  },

  // ==========================================
  // 3. القراءات (Readings)
  // ==========================================
  /**
   * استقبال قراءة من جهاز IoT
   * POST /iot/readings
   * يُفضل تمرير `idempotency_key` في query لمنع تكرار الإرسال
   */
  ingestReading: async (data: UtilityReadingCreate, idempotencyKey?: string): Promise<Record<string, any>> => {
    try {
      const key = idempotencyKey || generateIdempotencyKey();
      const { data: result } = await apiClient.post<Record<string, any>>("/iot/readings", data, {
        params: { idempotency_key: key },
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إرسال القراءة");
    }
  },

  /**
   * جلب القراءات
   * GET /iot/readings
   */
  getReadings: async (params?: { asset_id?: number | null; grid_id?: number | null; limit?: number }): Promise<UtilityReadingResponse[]> => {
    try {
      const { data } = await apiClient.get<UtilityReadingResponse[]>("/iot/readings", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب القراءات");
    }
  },

  // ==========================================
  // 4. الكربون (Carbon)
  // ==========================================
  /**
   * تسوية الكربون
   * POST /iot/carbon/settle
   */
  settleCarbon: async (data: CarbonSettlementRequest): Promise<CarbonSettlementResponse> => {
    try {
      const { data: result } = await apiClient.post<CarbonSettlementResponse>("/iot/carbon/settle", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تسوية الكربون");
    }
  },

  // ==========================================
  // 5. الصيانة (Maintenance)
  // ==========================================
  /**
   * تسجيل طلب صيانة
   * POST /iot/maintenance
   */
  reportMaintenance: async (data: MaintenanceLogCreate): Promise<MaintenanceLogResponse> => {
    try {
      const { data: result } = await apiClient.post<MaintenanceLogResponse>("/iot/maintenance", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تسجيل طلب الصيانة");
    }
  },

  /**
   * حل طلب صيانة (تسجيل الإنجاز)
   * POST /iot/maintenance/{log_id}/resolve
   */
  resolveMaintenance: async (logId: number): Promise<MaintenanceLogResponse> => {
    try {
      const id = Number(logId);
      if (isNaN(id)) throw new Error("معرف طلب الصيانة غير صحيح");
      const { data: result } = await apiClient.post<MaintenanceLogResponse>(`/iot/maintenance/${id}/resolve`, undefined, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل حل طلب الصيانة");
    }
  },
};