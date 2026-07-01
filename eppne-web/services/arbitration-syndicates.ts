// services/arbitration-syndicates.ts
import api from '@/lib/axios';
import type {
  ArbitrationCase,
  CrowdJury,
  SovereignSyndicate,
  SyndicateMembership,
  ProfessionalLicense,
  SyndicateElection,
  ElectionCandidate,
  ElectionVote,
  DisputeStatus,
  JudgingMode,
  SyndicateType,
  ElectionStatus,
} from '@/types/arbitration-syndicates';

// ========== Arbitration Cases ==========
export const getMyCases = () => api.get<ArbitrationCase[]>('/arbitration-syndicates/cases/me');

export const getCase = (id: number) => api.get<ArbitrationCase>(`/arbitration-syndicates/cases/${id}`);

export const createCase = (
  data: {
    contract_id?: string;
    respondent_id: number;
    dispute_reason: string;
    evidence_hashes?: string[];
    judging_mode?: JudgingMode;
  },
  idempotencyKey?: string
) =>
  api.post<ArbitrationCase>('/arbitration-syndicates/cases', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const castJuryVote = (
  caseId: number,
  data: { vote: boolean; justification?: string },
  idempotencyKey?: string
) =>
  api.post<CrowdJury>(`/arbitration-syndicates/cases/${caseId}/jury-vote`, data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

// ========== Syndicates ==========
export const getSyndicates = () => api.get<SovereignSyndicate[]>('/arbitration-syndicates/syndicates');

export const getSyndicate = (id: number) => api.get<SovereignSyndicate>(`/arbitration-syndicates/syndicates/${id}`);

export const createSyndicate = (data: {
  name: string;
  syndicate_type: SyndicateType;
  description?: string;
  annual_fee_mrusdt?: number;
  dao_contract_address?: string;
  treasury_wallet_address?: string;
  governance_token?: string;
}) => api.post<SovereignSyndicate>('/arbitration-syndicates/syndicates', data);

export const joinSyndicate = (syndicateId: number, idempotencyKey?: string) =>
  api.post<SyndicateMembership>(
    `/arbitration-syndicates/syndicates/${syndicateId}/join`,
    {},
    { headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {} }
  );

// ========== Licenses ==========
export const getMyLicenses = () => api.get<ProfessionalLicense[]>('/arbitration-syndicates/licenses/me');

export const issueLicense = (
  data: {
    syndicate_id: number;
    license_name: string;
    required_certificate_id?: number;
    qualifies_for_job_id?: number;
  },
  idempotencyKey?: string
) =>
  api.post<ProfessionalLicense>('/arbitration-syndicates/licenses', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

// ========== Elections ==========
export const getElections = (params?: { syndicate_id?: number; status?: ElectionStatus }) =>
  api.get<SyndicateElection[]>('/arbitration-syndicates/elections', { params });

export const getElection = (id: number) => api.get<SyndicateElection>(`/arbitration-syndicates/elections/${id}`);

export const createElection = (data: {
  syndicate_id: number;
  title: string;
  election_type: string;
  election_year: number;
  nomination_start: string;
  nomination_end: string;
  voting_start: string;
  voting_end: string;
}) => api.post<SyndicateElection>('/arbitration-syndicates/elections', data);

export const nominateCandidate = (
  electionId: number,
  data: { manifesto: string },
  idempotencyKey?: string
) =>
  api.post<ElectionCandidate>(`/arbitration-syndicates/elections/${electionId}/candidates`, data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const castVote = (
  electionId: number,
  data: { candidate_id: number },
  idempotencyKey?: string
) =>
  api.post<{ message: string; vote_hash: string }>(
    `/arbitration-syndicates/elections/${electionId}/vote`,
    data,
    { headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {} }
  );