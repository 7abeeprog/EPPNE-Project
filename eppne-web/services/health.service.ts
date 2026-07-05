// services/health.service.ts
import apiClient from '@/lib/api-client';
import { generateIdempotencyKey } from '@/lib/utils';

// تطابق Schemas من OpenAPI
export interface EmergencyDispatchCreate {
  patient_id?: number | null;
  facility_id?: number | null;
  emergency_type: 'MEDICAL_CRITICAL' | 'BIO_HAZARD' | 'ATHLETIC_INJURY' | 'VETERINARY_EMERGENCY' | 'AGRICULTURAL_PLAGUE' | 'ALGAE_BLOOM';
  gps_location: Record<string, number>;
  vital_signs_on_route?: Record<string, any> | null;
}

export interface EmergencyDispatchResponse {
  id: number;
  patient_id?: number | null;
  facility_id?: number | null;
  emergency_type: string;
  gps_location: Record<string, number>;
  vital_signs_on_route?: Record<string, any> | null;
  dispatch_time: string;
  arrival_time?: string | null;
  status: 'PENDING' | 'DISPATCHED' | 'ON_SCENE' | 'IN_TRANSIT' | 'COMPLETED' | 'CANCELLED';
}

export const healthService = {
  // استدعاء الطوارئ
  callEmergency: async (data: EmergencyDispatchCreate): Promise<EmergencyDispatchResponse> => {
    return apiClient.post('/api/health/emergency', data, {
      headers: {
        'Idempotency-Key': generateIdempotencyKey(), // منع التكرار
        'X-Tenant-ID': '1', // أو القيمة الديناميكية من المستأجر
      },
    });
  },

  // جلب حالة بلاغ الطوارئ
  getEmergencyStatus: (dispatchId: number): Promise<EmergencyDispatchResponse> => {
    return apiClient.get(`/api/health/emergency/${dispatchId}`);
  },

  // جلب الملف الطبي للمستخدم (لربطه بالطوارئ)
  getMyMedicalProfile: () => {
    return apiClient.get('/api/health/profile/me');
  },

  // تحديث الملف الطبي (اختياري)
  updateMedicalProfile: (data: any) => {
    return apiClient.put('/api/health/profile/me', data);
  },
};