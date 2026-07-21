// services/health.service.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

type MedicalProfileCreate = components['schemas']['MedicalProfileCreate'];
type MedicalProfileResponse = components['schemas']['MedicalProfileResponse'];
type BiometricLogCreate = components['schemas']['BiometricLogCreate'];
type BiometricLogResponse = components['schemas']['BiometricLogResponse'];
type AIHealthPrognosisResponse = components['schemas']['AIHealthPrognosisResponse'];
type MedicalAppointmentCreate = components['schemas']['MedicalAppointmentCreate'];
type MedicalAppointmentResponse = components['schemas']['MedicalAppointmentResponse'];
type PrescriptionCreate = components['schemas']['PrescriptionCreate'];
type PrescriptionResponse = components['schemas']['PrescriptionResponse'];
type EmergencyDispatchCreate = components['schemas']['EmergencyDispatchCreate'];
type EmergencyDispatchResponse = components['schemas']['EmergencyDispatchResponse'];
type HealthFacilityCreate = components['schemas']['HealthFacilityCreate'];
type HealthFacilityResponse = components['schemas']['HealthFacilityResponse'];

export const HealthService = {
  /**
   * جلب الملف الطبي للمستخدم الحالي
   * GET /health/health/profile/me
   */
  getMyMedicalProfile: async (): Promise<MedicalProfileResponse> => {
    try {
      const { data } = await apiClient.get<MedicalProfileResponse>("/health/health/profile/me", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الملف الطبي");
    }
  },

  /**
   * تحديث الملف الطبي للمستخدم الحالي
   * PUT /health/health/profile/me
   */
  updateMyMedicalProfile: async (data: MedicalProfileCreate): Promise<MedicalProfileResponse> => {
    try {
      const { data: result } = await apiClient.put<MedicalProfileResponse>("/health/health/profile/me", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث الملف الطبي");
    }
  },

  /**
   * تسجيل بيانات حيوية جديدة
   * POST /health/health/biometric/log
   */
  logBiometricData: async (data: BiometricLogCreate): Promise<Record<string, any>> => {
    try {
      const { data: result } = await apiClient.post<Record<string, any>>("/health/health/biometric/log", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تسجيل البيانات الحيوية");
    }
  },

  /**
   * جلب سجل البيانات الحيوية
   * GET /health/health/biometric/history
   */
  getBiometricHistory: async (params?: { limit?: number }): Promise<BiometricLogResponse[]> => {
    try {
      const { data } = await apiClient.get<BiometricLogResponse[]>("/health/health/biometric/history", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب سجل البيانات الحيوية");
    }
  },

  /**
   * جلب التنبؤات الصحية بالذكاء الاصطناعي
   * GET /health/health/ai/prognosis
   */
  getAIPrognosis: async (): Promise<AIHealthPrognosisResponse[]> => {
    try {
      const { data } = await apiClient.get<AIHealthPrognosisResponse[]>("/health/health/ai/prognosis", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب التنبؤات الصحية");
    }
  },

  /**
   * جلب مواعيدي الطبية
   * GET /health/health/appointments
   */
  getMyAppointments: async (params?: { status_filter?: string | null }): Promise<MedicalAppointmentResponse[]> => {
    try {
      const { data } = await apiClient.get<MedicalAppointmentResponse[]>("/health/health/appointments", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المواعيد الطبية");
    }
  },

  /**
   * حجز موعد طبي (مع دعم Idempotency ومنع التكرار)
   * POST /health/health/appointments
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  bookAppointment: async (
    data: MedicalAppointmentCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<MedicalAppointmentResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<MedicalAppointmentResponse>(
        "/health/health/appointments",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل حجز الموعد الطبي");
    }
  },

  /**
   * إلغاء موعد طبي
   * PATCH /health/health/appointments/{appointment_id}/cancel
   */
  cancelAppointment: async (appointmentId: number): Promise<MedicalAppointmentResponse> => {
    try {
      const id = Number(appointmentId);
      if (isNaN(id)) throw new Error("معرف الموعد غير صحيح");
      const { data: result } = await apiClient.patch<MedicalAppointmentResponse>(
        `/health/health/appointments/${id}/cancel`,
        undefined,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إلغاء الموعد الطبي");
    }
  },

  /**
   * إنشاء وصفة طبية جديدة
   * POST /health/health/prescriptions
   */
  createPrescription: async (data: PrescriptionCreate): Promise<PrescriptionResponse> => {
    try {
      const { data: result } = await apiClient.post<PrescriptionResponse>("/health/health/prescriptions", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الوصفة الطبية");
    }
  },

  /**
   * استدعاء الطوارئ (مع دعم Idempotency ومنع التكرار)
   * POST /health/health/emergency
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  callEmergency: async (
    data: EmergencyDispatchCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<EmergencyDispatchResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<EmergencyDispatchResponse>(
        "/health/health/emergency",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل استدعاء الطوارئ");
    }
  },

  /**
   * جلب حالة بلاغ الطوارئ
   * GET /health/health/emergency/{dispatch_id}
   */
  getEmergencyStatus: async (dispatchId: number): Promise<EmergencyDispatchResponse> => {
    try {
      const id = Number(dispatchId);
      if (isNaN(id)) throw new Error("معرف بلاغ الطوارئ غير صحيح");
      const { data } = await apiClient.get<EmergencyDispatchResponse>(`/health/health/emergency/${id}`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب حالة الطوارئ");
    }
  },

  /**
   * جلب قائمة المرافق الصحية مع التصفية
   * GET /health/health/facilities
   */
  listFacilities: async (params?: {
    category?: string | null;
    skip?: number;
    limit?: number;
  }): Promise<HealthFacilityResponse[]> => {
    try {
      const { data } = await apiClient.get<HealthFacilityResponse[]>("/health/health/facilities", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المرافق الصحية");
    }
  },

  /**
   * إنشاء مرفق صحي جديد
   * POST /health/health/facilities
   */
  createFacility: async (data: HealthFacilityCreate): Promise<HealthFacilityResponse> => {
    try {
      const { data: result } = await apiClient.post<HealthFacilityResponse>("/health/health/facilities", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المرفق الصحي");
    }
  },
};