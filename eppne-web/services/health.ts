// services/health.ts
import api from '@/lib/axios';
import type {
  MedicalProfile,
  BiometricLog,
  AIHealthPrognosis,
  MedicalAppointment,
  EmergencyDispatch,
  Prescription,
  HealthFacility,
  TargetEntityType,
  FacilityCategory,
  EmergencyType,
} from '@/types/health';

// ========== Profile ==========
export const getMyProfile = () => api.get<MedicalProfile>('/health/profile/me');
export const updateMyProfile = (data: Partial<MedicalProfile>) =>
  api.put<MedicalProfile>('/health/profile/me', data);

// ========== Biometric ==========
export const logBiometricData = (data: {
  source: string;
  device_id?: string;
  aggregated_metrics: Record<string, any>;
  recorded_at?: string;
}) => api.post('/health/biometric/log', data);

export const getBiometricHistory = (params?: { limit?: number }) =>
  api.get<BiometricLog[]>('/health/biometric/history', { params });

// ========== AI Prognosis ==========
export const getAIPrognosis = () => api.get<AIHealthPrognosis[]>('/health/ai/prognosis');

// ========== Appointments ==========
export const getMyAppointments = (params?: { status?: string }) =>
  api.get<MedicalAppointment[]>('/health/appointments', { params });

export const bookAppointment = (
  data: {
    doctor_id: number;
    facility_id: number;
    department_id?: number;
    appointment_time: string;
    appointment_type: string;
  },
  idempotencyKey?: string
) =>
  api.post<MedicalAppointment>('/health/appointments', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const cancelAppointment = (appointmentId: number) =>
  api.patch<MedicalAppointment>(`/health/appointments/${appointmentId}/cancel`);

// ========== Emergency ==========
export const callEmergency = (
  data: {
    patient_id?: number;
    facility_id?: number;
    emergency_type: EmergencyType;
    gps_location: { lat: number; lng: number };
    vital_signs_on_route?: Record<string, any>;
  },
  idempotencyKey?: string
) =>
  api.post<EmergencyDispatch>('/health/emergency', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const getEmergencyStatus = (dispatchId: number) =>
  api.get<EmergencyDispatch>(`/health/emergency/${dispatchId}`);

// ========== Facilities ==========
export const getFacilities = (params?: { category?: string; skip?: number; limit?: number }) =>
  api.get<HealthFacility[]>('/health/facilities', { params });