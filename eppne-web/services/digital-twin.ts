// services/digital-twin.ts
import api from '@/lib/axios';
import type {
  DigitalTwinConfig,
  TimeCapsule,
  DigitalWill,
  LifeMilestone,
  Beneficiary,
  PreBirthRecord,
  DeathOracle,
  TwinAccessLevel,
  TwinCapability,
  MilestoneType,
} from '@/types/digital-twin';

// ============================================================
// 1. إعدادات التوأم الرقمي (Config)
// ============================================================

export const getTwinConfig = () =>
  api.get<DigitalTwinConfig>('/digital-twin/config');

export const updateTwinConfig = (data: Partial<DigitalTwinConfig>) =>
  api.put<DigitalTwinConfig>('/digital-twin/config', data);

// ============================================================
// 2. التفاعل مع التوأم الرقمي (مع دعم Idempotency والإحالة)
// ============================================================

export const interactWithTwin = (
  ownerId: number,
  data: { interaction_type: string; duration_minutes: number },
  idempotencyKey?: string,
  affiliateCode?: string  // 🔥 جديد: كود الإحالة
) =>
  api.post(`/digital-twin/interact/${ownerId}`, data, {
    headers: {
      ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}),
      ...(affiliateCode ? { 'Affiliate-Code': affiliateCode } : {}),  // 🔥 جديد
    },
  });

// ============================================================
// 3. خزائن الزمن (Time Capsule)
// ============================================================

export const createTimeCapsule = (
  data: {
    encrypted_payload_hash: string;
    video_will_ipfs?: string;
    heartbeat_interval_days?: number;
    encrypted_credentials?: Record<string, any>;
  },
  beneficiaries: Beneficiary[]
) =>
  api.post<TimeCapsule>('/digital-twin/time-capsule', { ...data, beneficiaries });

export const getTimeCapsule = () =>
  api.get<TimeCapsule>('/digital-twin/time-capsule');

export const sendHeartbeat = () =>
  api.post<{ message: string; last_heartbeat: string }>('/digital-twin/time-capsule/heartbeat');

// ============================================================
// 4. الوصية الرقمية (Digital Will)
// ============================================================

export const createDigitalWill = (data: {
  will_content_ipfs: string;
  legal_witness_tx?: string;
}) => api.post<DigitalWill>('/digital-twin/will', data);

// ============================================================
// 5. أوراكل الموت (Death Oracle)
// ============================================================

export const reportDeath = (data: { reporter_user_id: number; evidence_ipfs_hash: string }) =>
  api.post<{ status: string; message: string }>('/digital-twin/death-oracle/report-death', data);

export const confirmDeath = (deceasedId: number, confirmers: number[]) =>
  api.post<{ status: string; release_tx: string }>(
    `/digital-twin/death-oracle/confirm-death/${deceasedId}`,
    { confirmers }
  );

// ============================================================
// 6. محطات الحياة (Milestones)
// ============================================================

export const getMilestones = () =>
  api.get<LifeMilestone[]>('/digital-twin/milestones');

export const addMilestone = (data: {
  milestone_type: MilestoneType;
  title: string;
  description?: string;
  evidence_ipfs_hash?: string;
  occurrence_date: string;
}) => api.post<LifeMilestone>('/digital-twin/milestones', data);

// ============================================================
// 7. الحجز قبل الولادة (Pre-Birth)
// ============================================================

export const reservePreBirthIdentity = (data: {
  parent_1_id: number;
  parent_2_id?: number;
  reserved_sovereign_id: string;
  trust_fund_wallet?: string;
  expected_arrival_date?: string;
  genetic_profile_hash?: string;
}) => api.post<PreBirthRecord>('/digital-twin/pre-birth', data);