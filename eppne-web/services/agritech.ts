// services/agritech.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";

type SmartFarmCreate = components['schemas']['SmartFarmCreate'];
type SmartFarmResponse = components['schemas']['SmartFarmResponse'];
type FarmZoneCreate = components['schemas']['FarmZoneCreate'];
type FarmZoneResponse = components['schemas']['FarmZoneResponse'];
type CropCycleCreate = components['schemas']['CropCycleCreate'];
type CropCycleResponse = components['schemas']['CropCycleResponse'];
type HarvestBatchCreate = components['schemas']['HarvestBatchCreate'];
type HarvestBatchResponse = components['schemas']['HarvestBatchResponse'];
type BioAssetCohortCreate = components['schemas']['BioAssetCohortCreate'];
type BioAssetCohortResponse = components['schemas']['BioAssetCohortResponse'];
type BioProductYieldCreate = components['schemas']['BioProductYieldCreate'];
type BioProductYieldResponse = components['schemas']['BioProductYieldResponse'];
type SupplyChainStageCreate = components['schemas']['SupplyChainStageCreate'];
type SupplyChainStageResponse = components['schemas']['SupplyChainStageResponse'];
type TraceabilityQRResponse = components['schemas']['TraceabilityQRResponse'];
type AgriculturalCertificateCreate = components['schemas']['AgriculturalCertificateCreate'];
type AgriculturalCertificateResponse = components['schemas']['AgriculturalCertificateResponse'];
type SoilSensorReadingCreate = components['schemas']['SoilSensorReadingCreate'];
type SoilSensorReadingResponse = components['schemas']['SoilSensorReadingResponse'];
type WeatherAlertCreate = components['schemas']['WeatherAlertCreate'];
type WeatherAlertResponse = components['schemas']['WeatherAlertResponse'];

export const AgritechService = {
  // ==========================================
  // 1. المزارع (Farms)
  // ==========================================
  /**
   * إنشاء مزرعة جديدة
   * POST /agritech/agritech/farms
   * تدعم X-Tenant-ID في الهيدر
   */
  createFarm: async (data: SmartFarmCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<SmartFarmResponse> => {
    try {
      const { data: result } = await apiClient.post<SmartFarmResponse>("/agritech/agritech/farms", data, {
        headers,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المزرعة");
    }
  },

  /**
   * جلب قائمة المزارع مع تصفية حسب النوع
   * GET /agritech/agritech/farms
   * تدعم X-Tenant-ID في الهيدر
   */
  listFarms: async (
    params?: { farm_type?: string | null; skip?: number; limit?: number },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<SmartFarmResponse[]> => {
    try {
      const { data } = await apiClient.get<SmartFarmResponse[]>("/agritech/agritech/farms", {
        params,
        headers,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المزارع");
    }
  },

  // ==========================================
  // 2. المناطق (Zones)
  // ==========================================
  /**
   * إضافة منطقة داخل مزرعة
   * POST /agritech/agritech/farms/{farm_id}/zones
   */
  addFarmZone: async (farmId: number, data: FarmZoneCreate): Promise<FarmZoneResponse> => {
    try {
      const id = Number(farmId);
      if (isNaN(id)) throw new Error("معرف المزرعة غير صحيح");
      const { data: result } = await apiClient.post<FarmZoneResponse>(`/agritech/agritech/farms/${id}/zones`, data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إضافة المنطقة");
    }
  },

  // ==========================================
  // 3. دورات المحاصيل (Crop Cycles)
  // ==========================================
  /**
   * بدء دورة محصولية جديدة
   * POST /agritech/agritech/zones/{zone_id}/crop-cycles
   */
  startCropCycle: async (zoneId: number, data: CropCycleCreate): Promise<CropCycleResponse> => {
    try {
      const id = Number(zoneId);
      if (isNaN(id)) throw new Error("معرف المنطقة غير صحيح");
      const { data: result } = await apiClient.post<CropCycleResponse>(`/agritech/agritech/zones/${id}/crop-cycles`, data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل بدء الدورة المحصولية");
    }
  },

  // ==========================================
  // 4. الحصاد (Harvest)
  // ==========================================
  /**
   * تسجيل حصاد لدورة محصولية
   * POST /agritech/agritech/crop-cycles/{cycle_id}/harvest
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  registerHarvest: async (
    cycleId: number,
    data: HarvestBatchCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<HarvestBatchResponse> => {
    try {
      const id = Number(cycleId);
      if (isNaN(id)) throw new Error("معرف الدورة غير صحيح");
      const { data: result } = await apiClient.post<HarvestBatchResponse>(
        `/agritech/agritech/crop-cycles/${id}/harvest`,
        data,
        { headers, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تسجيل الحصاد");
    }
  },

  // ==========================================
  // 5. الأصول الحيوية (Bio Assets)
  // ==========================================
  /**
   * إضافة مجموعة حيوية (ماشية، دواجن، إلخ)
   * POST /agritech/agritech/zones/{zone_id}/bio-cohorts
   */
  addBioCohort: async (zoneId: number, data: BioAssetCohortCreate): Promise<BioAssetCohortResponse> => {
    try {
      const id = Number(zoneId);
      if (isNaN(id)) throw new Error("معرف المنطقة غير صحيح");
      const { data: result } = await apiClient.post<BioAssetCohortResponse>(
        `/agritech/agritech/zones/${id}/bio-cohorts`,
        data,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إضافة المجموعة الحيوية");
    }
  },

  /**
   * تسجيل إنتاج حيوي (حليب، بيض، إلخ)
   * POST /agritech/agritech/bio-cohorts/{cohort_id}/yields
   */
  registerBioYield: async (cohortId: number, data: BioProductYieldCreate): Promise<BioProductYieldResponse> => {
    try {
      const id = Number(cohortId);
      if (isNaN(id)) throw new Error("معرف المجموعة غير صحيح");
      const { data: result } = await apiClient.post<BioProductYieldResponse>(
        `/agritech/agritech/bio-cohorts/${id}/yields`,
        data,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تسجيل الإنتاج الحيوي");
    }
  },

  // ==========================================
  // 6. التتبع (Traceability)
  // ==========================================
  /**
   * إضافة مرحلة تتبع لسلسلة الإمداد
   * POST /agritech/agritech/traceability/stage
   */
  addTraceabilityStage: async (data: SupplyChainStageCreate): Promise<SupplyChainStageResponse> => {
    try {
      const { data: result } = await apiClient.post<SupplyChainStageResponse>(
        "/agritech/agritech/traceability/stage",
        data,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إضافة مرحلة التتبع");
    }
  },

  /**
   * جلب مراحل التتبع لكيان معين
   * GET /agritech/agritech/traceability/{traceable_type}/{traceable_id}
   */
  getTraceability: async (traceableType: string, traceableId: number): Promise<SupplyChainStageResponse[]> => {
    try {
      const id = Number(traceableId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      const { data } = await apiClient.get<SupplyChainStageResponse[]>(
        `/agritech/agritech/traceability/${traceableType}/${id}`,
        { withCredentials: true }
      );
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب التتبع");
    }
  },

  /**
   * توليد رمز QR للتتبع
   * POST /agritech/agritech/traceability/qr/{traceable_type}/{traceable_id}
   */
  generateTraceabilityQR: async (traceableType: string, traceableId: number): Promise<TraceabilityQRResponse> => {
    try {
      const id = Number(traceableId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      const { data: result } = await apiClient.post<TraceabilityQRResponse>(
        `/agritech/agritech/traceability/qr/${traceableType}/${id}`,
        undefined,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل توليد رمز QR");
    }
  },

  // ==========================================
  // 7. الشهادات الزراعية (Certificates)
  // ==========================================
  /**
   * إصدار شهادة زراعية
   * POST /agritech/agritech/certificates
   * تدعم X-Tenant-ID
   */
  issueCertificate: async (
    data: AgriculturalCertificateCreate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<AgriculturalCertificateResponse> => {
    try {
      const { data: result } = await apiClient.post<AgriculturalCertificateResponse>(
        "/agritech/agritech/certificates",
        data,
        { headers, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إصدار الشهادة");
    }
  },

  /**
   * جلب شهادات كيان معين
   * GET /agritech/agritech/certificates/{entity_type}/{entity_id}
   */
  getEntityCertificates: async (entityType: string, entityId: number): Promise<AgriculturalCertificateResponse[]> => {
    try {
      const id = Number(entityId);
      if (isNaN(id)) throw new Error("معرف الكيان غير صحيح");
      const { data } = await apiClient.get<AgriculturalCertificateResponse[]>(
        `/agritech/agritech/certificates/${entityType}/${id}`,
        { withCredentials: true }
      );
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الشهادات");
    }
  },

  // ==========================================
  // 8. قراءات التربة (Soil Readings)
  // ==========================================
  /**
   * تسجيل قراءة تربة جديدة
   * POST /agritech/agritech/soil-readings
   * تدعم X-Tenant-ID
   */
  recordSoilReading: async (
    data: SoilSensorReadingCreate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<SoilSensorReadingResponse> => {
    try {
      const { data: result } = await apiClient.post<SoilSensorReadingResponse>(
        "/agritech/agritech/soil-readings",
        data,
        { headers, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تسجيل قراءة التربة");
    }
  },

  /**
   * جلب قراءات التربة لمنطقة معينة
   * GET /agritech/agritech/soil-readings/{zone_id}
   */
  getSoilReadings: async (zoneId: number, limit: number = 100): Promise<SoilSensorReadingResponse[]> => {
    try {
      const id = Number(zoneId);
      if (isNaN(id)) throw new Error("معرف المنطقة غير صحيح");
      const { data } = await apiClient.get<SoilSensorReadingResponse[]>(
        `/agritech/agritech/soil-readings/${id}`,
        { params: { limit }, withCredentials: true }
      );
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب قراءات التربة");
    }
  },

  // ==========================================
  // 9. تنبيهات الطقس (Weather Alerts)
  // ==========================================
  /**
   * إنشاء تنبيه طقس جديد
   * POST /agritech/agritech/weather-alerts
   * تدعم X-Tenant-ID
   */
  createWeatherAlert: async (
    data: WeatherAlertCreate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<WeatherAlertResponse> => {
    try {
      const { data: result } = await apiClient.post<WeatherAlertResponse>(
        "/agritech/agritech/weather-alerts",
        data,
        { headers, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء تنبيه الطقس");
    }
  },

  /**
   * جلب التنبيهات النشطة
   * GET /agritech/agritech/weather-alerts
   * تدعم X-Tenant-ID
   */
  getActiveWeatherAlerts: async (headers?: { 'X-Tenant-ID'?: number }): Promise<WeatherAlertResponse[]> => {
    try {
      const { data } = await apiClient.get<WeatherAlertResponse[]>("/agritech/agritech/weather-alerts", {
        headers,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تنبيهات الطقس");
    }
  },
};