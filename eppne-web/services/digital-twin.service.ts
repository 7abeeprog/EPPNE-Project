// services/digital-twin.service.ts
import { apiClient } from "@/lib/api-client";
// import type { components } from "@/src/lib/api-types"; // Temporarily disabled due to missing types
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

// ============================================================
// NOTE: The specific schema types for Digital Twin endpoints
// are currently missing from api-types.ts. To avoid 18+ build errors,
// we use `any` as a temporary fallback for all payloads & responses.
// Once the backend schemas are correctly generated, replace `any`
// with the proper types from components['schemas'].
// ============================================================

// Fallback type definitions (to be replaced later)
type TwinConfigCreate = any;
type TwinConfigResponse = any;
type TwinPermissionCreate = any;
type TwinPermissionResponse = any;
type TwinInteractionCreate = any;
type TwinInteractionResponse = any;
type TimeCapsuleCreate = any;
type TimeCapsuleResponse = any;
type BeneficiaryCreate = any;
type BeneficiaryResponse = any;
type DigitalWillCreate = any;
type DigitalWillResponse = any;
type DeathReport = any;
type DeathOracleResponse = any;
type LifeMilestoneCreate = any;
type LifeMilestoneResponse = any;
type PreBirthRecordCreate = any;
type PreBirthRecordResponse = any;

export const DigitalTwinService = {
  /**
   * جلب إعدادات التوأم الرقمي للمستخدم الحالي
   * GET /digital-twin/config
   */
  getMyTwinConfig: async (headers?: { 'X-Tenant-ID'?: number }): Promise<TwinConfigResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<TwinConfigResponse>("/digital-twin/config", {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب إعدادات التوأم الرقمي");
    }
  },

  /**
   * تحديث إعدادات التوأم الرقمي
   * PUT /digital-twin/config
   */
  updateTwinConfig: async (
    data: TwinConfigCreate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<TwinConfigResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.put<TwinConfigResponse>("/digital-twin/config", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث إعدادات التوأم الرقمي");
    }
  },

  /**
   * التفاعل مع التوأم الرقمي لمستخدم آخر (مع دعم Idempotency)
   * POST /digital-twin/interact/{owner_id}
   */
  interactWithTwin: async (
    ownerId: number,
    data: TwinInteractionCreate,
    idempotencyKey?: string,
    affiliateCode?: string,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<TwinInteractionResponse> => {
    try {
      const id = Number(ownerId);
      if (isNaN(id)) throw new Error("معرف صاحب التوأم غير صحيح");

      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const key = idempotencyKey || generateIdempotencyKey();
      reqHeaders["Idempotency-Key"] = key;
      if (affiliateCode) {
        reqHeaders["Affiliate-Code"] = affiliateCode;
      }

      const { data: result } = await apiClient.post<TwinInteractionResponse>(
        `/digital-twin/interact/${id}`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل التفاعل مع التوأم الرقمي");
    }
  },

  /**
   * إنشاء خزنة زمنية جديدة مع المستفيدين
   * POST /digital-twin/time-capsule
   */
  createTimeCapsule: async (
    data: TimeCapsuleCreate,
    beneficiaries: BeneficiaryCreate[],
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<TimeCapsuleResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const payload = { ...data, beneficiaries };
      const { data: result } = await apiClient.post<TimeCapsuleResponse>(
        "/digital-twin/time-capsule",
        payload,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء خزنة الزمن");
    }
  },

  /**
   * إرسال نبضة قلب للحفاظ على نشاط الخزنة
   * POST /digital-twin/time-capsule/heartbeat
   */
  sendHeartbeat: async (headers?: { 'X-Tenant-ID'?: number }): Promise<{ message: string; last_heartbeat: string }> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.post<{ message: string; last_heartbeat: string }>(
        "/digital-twin/time-capsule/heartbeat",
        undefined,
        { headers: reqHeaders, withCredentials: true }
      );
      return data;
    } catch (error) {
      throw handleError(error, "فشل إرسال نبضة القلب");
    }
  },

  /**
   * جلب خزنة الزمن الخاصة بي
   * GET /digital-twin/time-capsule
   */
  getMyTimeCapsule: async (headers?: { 'X-Tenant-ID'?: number }): Promise<TimeCapsuleResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<TimeCapsuleResponse>("/digital-twin/time-capsule", {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب خزنة الزمن");
    }
  },

  /**
   * إنشاء وصية رقمية جديدة
   * POST /digital-twin/will
   */
  createDigitalWill: async (
    data: DigitalWillCreate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<DigitalWillResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<DigitalWillResponse>("/digital-twin/will", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الوصية الرقمية");
    }
  },

  /**
   * الإبلاغ عن وفاة
   * POST /digital-twin/death-oracle/report-death
   */
  reportDeath: async (
    data: DeathReport,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<{ status: string; message: string }> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<{ status: string; message: string }>(
        "/digital-twin/death-oracle/report-death",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل الإبلاغ عن الوفاة");
    }
  },

  /**
   * تأكيد الوفاة (للمشرفين فقط)
   * POST /digital-twin/death-oracle/confirm-death/{deceased_id}
   */
  confirmDeath: async (
    deceasedId: number,
    confirmers: number[],
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<{ status: string; release_tx: string }> => {
    try {
      const id = Number(deceasedId);
      if (isNaN(id)) throw new Error("معرف المتوفى غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<{ status: string; release_tx: string }>(
        `/digital-twin/death-oracle/confirm-death/${id}`,
        { confirmers },
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تأكيد الوفاة");
    }
  },

  /**
   * إضافة محطة حياة جديدة
   * POST /digital-twin/milestones
   */
  addLifeMilestone: async (
    data: LifeMilestoneCreate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<LifeMilestoneResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<LifeMilestoneResponse>("/digital-twin/milestones", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إضافة محطة الحياة");
    }
  },

  /**
   * جلب محطات الحياة الخاصة بي
   * GET /digital-twin/milestones
   */
  getMyMilestones: async (headers?: { 'X-Tenant-ID'?: number }): Promise<LifeMilestoneResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<LifeMilestoneResponse[]>("/digital-twin/milestones", {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب محطات الحياة");
    }
  },

  /**
   * حجز هوية قبل الولادة
   * POST /digital-twin/pre-birth
   */
  reservePreBirthIdentity: async (
    data: PreBirthRecordCreate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<PreBirthRecordResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<PreBirthRecordResponse>("/digital-twin/pre-birth", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل حجز الهوية قبل الولادة");
    }
  },
};