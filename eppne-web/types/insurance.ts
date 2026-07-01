// types/insurance.ts
export type PolicyType = 'MEDICAL' | 'ACCIDENT' | 'LIFE' | 'FLEET' | 'CARGO' | 'PROJECT' | 'EMPLOYEE_BENEFITS';
export type PremiumCycle = 'ONE_TIME' | 'MONTHLY' | 'QUARTERLY' | 'ANNUALLY';
export type ClaimStatus = 'SUBMITTED' | 'UNDER_INVESTIGATION' | 'APPROVED' | 'REJECTED' | 'PAID';
export type PensionStatus = 'ACTIVE' | 'SUSPENDED' | 'TERMINATED';

export interface InsurancePolicy {
  id: number;
  tenant_id: number;
  issuer_entity_id: number;
  name: string;
  policy_type: PolicyType;
  description?: string;
  base_premium_mrusdt: number;
  premium_cycle: PremiumCycle;
  max_coverage_limit_mrusdt: number;
  terms_and_conditions: Record<string, any>;
  is_active: boolean;
  smart_contract_address?: string;
  created_by: number;
  created_at: string;
  updated_at: string;
}

export interface InsuranceSubscription {
  id: number;
  policy_id: number;
  policy?: InsurancePolicy;
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
  status: string;
  policy_nft_id?: string;
  subscription_tx_hash?: string;
  created_at: string;
  updated_at: string;
}

export interface InsuranceClaim {
  id: number;
  subscription_id: number;
  subscription?: InsuranceSubscription;
  claimant_user_id: number;
  claimant_name?: string;
  incident_date: string;
  incident_description: string;
  evidence_urls: string[];
  claimed_amount_mrusdt: number;
  approved_amount_mrusdt: number;
  status: ClaimStatus;
  investigation_notes?: string;
  oracle_verification_hash?: string;
  payout_tx_hash?: string;
  created_at: string;
  updated_at: string;
}

export interface PensionRecord {
  id: number;
  beneficiary_id: number;
  beneficiary_name?: string;
  source_entity_id?: number;
  pension_type: string;
  monthly_amount_mrusdt: number;
  total_disbursed_mrusdt: number;
  start_date: string;
  end_date?: string;
  status: PensionStatus;
  streaming_contract_address?: string;
  last_payout_tx?: string;
  created_at: string;
  updated_at: string;
}

export interface EmployeeInsuranceProfile {
  id: number;
  user_id: number;
  user_name?: string;
  government_insurance_number: string;
  employee_share_percentage: number;
  employer_share_percentage: number;
  total_contributed_mrusdt: number;
  last_contribution_date?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

// ========== UI Types ==========
export interface InsuranceStats {
  total_policies: number;
  active_subscriptions: number;
  total_claims: number;
  pending_claims: number;
  total_pensions: number;
}