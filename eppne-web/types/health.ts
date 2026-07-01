// types/health.ts
export type TargetEntityType = 'HUMAN' | 'ANIMAL' | 'PLANT' | 'ALGAE';
export type FacilityCategory = 'HOSPITAL' | 'CLINIC' | 'LABORATORY' | 'PHARMACY' | 'VETERINARY' | 'AGRICULTURAL_RESEARCH' | 'MARINE_BIOLOGY';
export type ConsultationType = 'IN_PERSON' | 'VIDEO_CALL' | 'AI_DIAGNOSIS';
export type AppointmentStatus = 'SCHEDULED' | 'CONFIRMED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED' | 'NO_SHOW';
export type RiskLevel = 'SAFE' | 'MONITOR' | 'WARNING' | 'CRITICAL';
export type EmergencyType = 'MEDICAL_CRITICAL' | 'BIO_HAZARD' | 'ATHLETIC_INJURY' | 'VETERINARY_EMERGENCY' | 'AGRICULTURAL_PLAGUE' | 'ALGAE_BLOOM';
export type DispatchStatus = 'PENDING' | 'DISPATCHED' | 'ON_SCENE' | 'IN_TRANSIT' | 'COMPLETED' | 'CANCELLED';
export type BiometricSource = 'WEARABLE' | 'OPTICAL_CAMERA' | 'MEDICAL_DEVICE' | 'IOT_SENSOR' | 'DRONE_IMAGERY' | 'SATELLITE';

export interface HealthFacility {
  id: number;
  name: string;
  facility_category: FacilityCategory;
  supported_targets: TargetEntityType[];
  specialties: string[];
  is_active: boolean;
  facility_wallet_address?: string;
}

export interface MedicalProfile {
  id: number;
  target_entity_type: TargetEntityType;
  species?: string;
  breed?: string;
  plant_variety?: string;
  scientific_name?: string;
  blood_type?: string;
  health_score: number;
  athletic_class?: string;
  chronic_diseases: string[];
  allergies: string[];
  current_medications: string[];
  encrypted_ipfs_hash?: string;
  emergency_contact?: string;
  created_at: string;
  updated_at: string;
}

export interface BiometricLog {
  id: number;
  medical_profile_id: number;
  source: BiometricSource;
  device_id?: string;
  aggregated_metrics: Record<string, any>;
  recorded_at: string;
  created_at: string;
}

export interface AIHealthPrognosis {
  id: number;
  risk_level: RiskLevel;
  predicted_condition: string;
  confidence_score: number;
  preventive_recommendations: Record<string, any>;
  is_acknowledged: boolean;
  created_at: string;
}

export interface MedicalAppointment {
  id: number;
  patient_user_id: number;
  doctor_id: number;
  facility_id: number;
  department_id?: number;
  appointment_time: string;
  appointment_type: string;
  status: AppointmentStatus;
  invoice_id?: number;
  payment_tx_hash?: string;
  created_at: string;
}

export interface EmergencyDispatch {
  id: number;
  patient_id?: number;
  facility_id?: number;
  emergency_type: EmergencyType;
  gps_location: { lat: number; lng: number };
  vital_signs_on_route?: Record<string, any>;
  dispatch_time: string;
  arrival_time?: string;
  status: DispatchStatus;
}

export interface Prescription {
  id: number;
  consultation_id: number;
  patient_id: number;
  medications: Array<{ name: string; dosage: string; frequency: string }>;
  doctor_notes?: string;
  pharmacy_store_id?: number;
  commerce_order_id?: number;
  status: 'ISSUED' | 'FILLED' | 'CANCELLED';
  created_at: string;
}

// ========== UI Types ==========
export interface BiometricSummary {
  avg_heart_rate: number;
  blood_oxygen: number;
  stress_level: 'LOW' | 'MEDIUM' | 'HIGH';
  temperature: number;
  last_updated: string;
}

export interface HealthDashboardStats {
  active_profile: boolean;
  total_appointments: number;
  upcoming_appointments: number;
  latest_risk_level: RiskLevel;
  last_biometric: string;
}