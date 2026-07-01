// services/insurance.ts
import api from '@/lib/axios';
import type {
  InsurancePolicy,
  InsuranceSubscription,
  InsuranceClaim,
  PensionRecord,
  EmployeeInsuranceProfile,
  PolicyType,
  PremiumCycle,
  ClaimStatus,
  PensionStatus,
} from '@/types/insurance';

// ========== Policies ==========
export const getPolicies = (params?: { policy_type?: PolicyType; is_active?: boolean; skip?: number; limit?: number }) =>
  api.get<InsurancePolicy[]>('/insurance/policies', { params });

export const getPolicy = (id: number) => api.get<InsurancePolicy>(`/insurance/policies/${id}`);

export const createPolicy = (data: {
  issuer_entity_id: number;
  name: string;
  policy_type: PolicyType;
  description?: string;
  base_premium_mrusdt: number;
  premium_cycle?: PremiumCycle;
  max_coverage_limit_mrusdt: number;
  terms_and_conditions?: Record<string, any>;
  smart_contract_address?: string;
}) => api.post<InsurancePolicy>('/insurance/policies', data);

// ========== Subscriptions ==========
export const getMySubscriptions = (params?: { status?: string; skip?: number; limit?: number }) =>
  api.get<InsuranceSubscription[]>('/insurance/subscriptions/me', { params });

export const getSubscription = (id: number) => api.get<InsuranceSubscription>(`/insurance/subscriptions/${id}`);

export const subscribe = (
  data: {
    policy_id: number;
    subscriber_user_id?: number;
    fleet_id?: number;
    land_asset_id?: number;
    project_id?: number;
    bio_asset_id?: number;
    shipment_id?: number;
    employment_contract_id?: number;
    beneficiaries_json?: Record<string, any>;
    start_date: string;
    end_date?: string;
  },
  idempotencyKey?: string
) =>
  api.post<InsuranceSubscription>('/insurance/subscriptions', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const renewSubscription = (subscriptionId: number) =>
  api.post<InsuranceSubscription>(`/insurance/subscriptions/${subscriptionId}/renew`);

// ========== Claims ==========
export const getMyClaims = (params?: { status?: ClaimStatus }) =>
  api.get<InsuranceClaim[]>('/insurance/claims/me', { params });

export const getClaim = (id: number) => api.get<InsuranceClaim>(`/insurance/claims/${id}`);

export const submitClaim = (
  data: {
    subscription_id: number;
    incident_date: string;
    incident_description: string;
    evidence_urls?: string[];
    claimed_amount_mrusdt: number;
  },
  idempotencyKey?: string
) =>
  api.post<InsuranceClaim>('/insurance/claims', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const reviewClaim = (
  claimId: number,
  data: { approve: boolean; approved_amount?: number; notes?: string },
  idempotencyKey?: string
) =>
  api.put<InsuranceClaim>(`/insurance/claims/${claimId}/review`, data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

// ========== Pensions ==========
export const getMyPensions = () => api.get<PensionRecord[]>('/insurance/pensions/me');

// ========== Employee Profile ==========
export const getMyEmployeeProfile = () => api.get<EmployeeInsuranceProfile>('/insurance/employee-profiles/me');

export const createEmployeeProfile = (data: {
  user_id: number;
  government_insurance_number: string;
  employee_share_percentage: number;
  employer_share_percentage: number;
}) => api.post<EmployeeInsuranceProfile>('/insurance/employee-profiles', data);