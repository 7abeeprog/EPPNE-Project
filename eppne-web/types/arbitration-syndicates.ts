// types/arbitration-syndicates.ts
export type DisputeStatus = 'OPEN' | 'IN_REVIEW' | 'RESOLVED' | 'APPEALED';
export type JudgingMode = 'AI_ONLY' | 'HUMAN_ONLY' | 'AI_HYBRID';
export type SyndicateType = 'PROFESSIONAL' | 'TRADE' | 'LABOR' | 'COMMUNITY';
export type ElectionStatus = 'UPCOMING' | 'NOMINATION' | 'VOTING' | 'CLOSED' | 'CANCELLED';

export interface ArbitrationCase {
  id: number;
  tenant_id: number;
  contract_id?: string;
  claimant_id: number;
  claimant_name?: string;
  respondent_id: number;
  respondent_name?: string;
  dispute_reason: string;
  evidence_hashes: string[];
  judging_mode: JudgingMode;
  ai_judge_id?: number;
  status: DisputeStatus;
  final_verdict?: string;
  enforcement_tx_hash?: string;
  created_at: string;
  updated_at: string;
  jury_votes?: CrowdJury[];
}

export interface CrowdJury {
  id: number;
  case_id: number;
  juror_id: number;
  juror_name?: string;
  vote: boolean; // true = لصالح المدعي, false = لصالح المدعى عليه
  justification?: string;
  reward_mr7: number;
  created_at: string;
}

export interface SovereignSyndicate {
  id: number;
  tenant_id: number;
  entity_id?: number;
  name: string;
  syndicate_type: SyndicateType;
  description?: string;
  annual_fee_mrusdt: number;
  is_active: boolean;
  dao_contract_address?: string;
  treasury_wallet_address?: string;
  governance_token?: string;
  created_at: string;
  member_count?: number;
  is_member?: boolean;
}

export interface SyndicateMembership {
  id: number;
  syndicate_id: number;
  member_user_id: number;
  member_name?: string;
  membership_number: string;
  join_date: string;
  expiry_date: string;
  status: string;
  membership_sbt_id?: string;
  minting_tx_hash?: string;
  created_at: string;
}

export interface ProfessionalLicense {
  id: number;
  syndicate_id: number;
  syndicate_name?: string;
  user_id: number;
  user_name?: string;
  license_name: string;
  license_number: string;
  required_certificate_id?: number;
  qualifies_for_job_id?: number;
  issue_date: string;
  expiry_date: string;
  status: string;
  license_sbt_id?: string;
  minting_tx_hash?: string;
  created_at: string;
}

export interface SyndicateElection {
  id: number;
  syndicate_id: number;
  syndicate_name?: string;
  title: string;
  election_type: string;
  election_year: number;
  nomination_start: string;
  nomination_end: string;
  voting_start: string;
  voting_end: string;
  status: ElectionStatus;
  smart_contract_address?: string;
  created_at: string;
  candidates?: ElectionCandidate[];
}

export interface ElectionCandidate {
  id: number;
  election_id: number;
  user_id: number;
  user_name?: string;
  manifesto: string;
  status: string;
  created_at: string;
}

export interface ElectionVote {
  id: number;
  election_id: number;
  voter_user_id: number;
  candidate_id: number;
  vote_hash: string;
  blockchain_tx_hash?: string;
  created_at: string;
}

// ========== UI Types ==========
export interface ArbitrationStats {
  total_cases: number;
  open_cases: number;
  resolved_cases: number;
  total_syndicates: number;
  total_licenses: number;
  active_elections: number;
}