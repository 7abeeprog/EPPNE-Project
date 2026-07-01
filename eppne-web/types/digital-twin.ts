// types/digital-twin.ts
export type TwinAccessLevel = 'PRIVATE' | 'FAMILY' | 'PAID_ONLY' | 'PUBLIC';
export type TwinCapability = 'CHAT' | 'MEETING' | 'FINANCE' | 'SIGN' | 'LEGACY';
export type LifeStatus = 'ALIVE' | 'DECEASED' | 'PRESUMED_DEAD' | 'LEGACY_MODE';
export type MilestoneType = 
  | 'IDENTITY_RESERVATION' 
  | 'BIRTH' 
  | 'GRADUATION' 
  | 'MARRIAGE' 
  | 'PATENT' 
  | 'DECEASE_CONFIRMATION';

export interface DigitalTwinConfig {
  id: number;
  user_id: number;
  agent_id?: number;
  global_access_level: TwinAccessLevel;
  interaction_fee_mrusdt: number;
  subscription_monthly_mrusdt: number;
  capabilities: TwinCapability[];
  knowledge_boundaries: Record<string, any>;
  max_spending_limit: number;
  is_active: boolean;
  settlement_type: string;
  physical_embodiment_status: string;
  created_at: string;
}

export interface TimeCapsule {
  id: number;
  user_id: number;
  encrypted_payload_hash: string;
  video_will_ipfs?: string;
  heartbeat_interval_days: number;
  last_heartbeat_at: string;
  status: 'ALIVE' | 'DECEASED' | 'UNLOCKED';
  encrypted_credentials?: Record<string, any>;
  created_at: string;
}

export interface DigitalWill {
  id: number;
  user_id: number;
  will_content_ipfs: string;
  will_nft_id: string;
  legal_witness_tx?: string;
  is_executed: boolean;
  executed_at?: string;
  created_at: string;
}

export interface LifeMilestone {
  id: number;
  user_id: number;
  milestone_type: MilestoneType;
  title: string;
  description?: string;
  milestone_nft_id?: string;
  evidence_ipfs_hash?: string;
  occurrence_date: string;
  created_at: string;
}

export interface Beneficiary {
  id: number;
  beneficiary_user_id: number;
  relationship_type?: string;
  access_share_percentage: number;
  heir_wallet_address: string;
}

export interface PreBirthRecord {
  id: number;
  parent_1_id: number;
  parent_2_id?: number;
  reserved_sovereign_id: string;
  trust_fund_wallet?: string;
  expected_arrival_date?: string;
  genetic_profile_hash?: string;
  created_at: string;
}

export interface DeathOracle {
  id: number;
  user_id: number;
  status: 'MONITORING' | 'ALIVE_AND_WELL' | 'DEATH_PENDING' | 'DEATH_CONFIRMED';
  last_confirmed_alive_at: string;
  check_interval_days: number;
  grace_period_days: number;
  official_death_certificate_ipfs?: string;
  release_tx_hash?: string;
}