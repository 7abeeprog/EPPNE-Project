// services/digital-twin.service.ts
import { apiClient } from "@/lib/api-client";
import { generateIdempotencyKey } from "@/lib/utils";
import { handleError } from "@/lib/error-handler";

// ==========================================
// إعدادات التوأم الرقمي
// ==========================================
export interface TwinConfig {
  id: number;
  user_id: number;
  agent_id: number | null;
  is_active: boolean;
  global_access_level: 'PRIVATE' | 'FAMILY' | 'PAID_ONLY' | 'PUBLIC';
  interaction_fee_mrusdt: string;
  subscription_monthly_mrusdt: string;
  capabilities: ('CHAT' | 'MEETING' | 'FINANCE' | 'SIGN' | 'LEGACY')[];
  knowledge_boundaries: Record<string, any>;
  max_spending_limit: string;
  settlement_type: string;
  physical_embodiment_status: string;
  created_at: string;
}

export interface TwinConfigCreate {
  global_access_level?: 'PRIVATE' | 'FAMILY' | 'PAID_ONLY' | 'PUBLIC';
  interaction_fee_mrusdt?: number | string;
  subscription_monthly_mrusdt?: number | string;
  capabilities?: ('CHAT' | 'MEETING' | 'FINANCE' | 'SIGN' | 'LEGACY')[];
  knowledge_boundaries?: Record<string, any>;
  max_spending_limit?: number | string;
  settlement_type?: string;
}

// ==========================================
// التفاعل مع التوأم الرقمي
// ==========================================
export interface TwinInteractionCreate {
  interaction_type: string;
  duration_minutes: number;
}

export interface TwinInteractionResponse {
  id: number;
  twin_config_id: number;
  visitor_id: number;
  interaction_type: string;
  duration_minutes: number;
  fee_paid_mrusdt: number;
  payout_tx_hash: string | null;
  created_at: string;
}

// ==========================================
// كبسولة الزمن
// ==========================================
export interface TimeCapsuleCreate {
  encrypted_payload_hash: string;
  video_will_ipfs?: string | null;
  heartbeat_interval_days?: number;
  encrypted_credentials?: Record<string, any> | null;
}

export interface BeneficiaryCreate {
  beneficiary_user_id: number;
  relationship_type?: string | null;
  access_share_percentage?: number;
  heir_wallet_address: string;
}

export interface TimeCapsuleResponse extends TimeCapsuleCreate {
  id: number;
  user_id: number;
  status: string;
  last_heartbeat_at: string;
  created_at: string;
}

// ==========================================
// الوصية الرقمية
// ==========================================
export interface DigitalWillCreate {
  will_content_ipfs: string;
  legal_witness_tx?: string | null;
}

export interface DigitalWillResponse extends DigitalWillCreate {
  id: number;
  user_id: number;
  will_nft_id: string;
  is_executed: boolean;
  executed_at: string | null;
  created_at: string;
}

// ==========================================
// الأحداث الحياتية (Life Milestones)
// ==========================================
export interface LifeMilestoneCreate {
  milestone_type: 'IDENTITY_RESERVATION' | 'BIRTH' | 'GRADUATION' | 'MARRIAGE' | 'PATENT' | 'DECEASE_CONFIRMATION';
  title: string;
  description?: string | null;
  evidence_ipfs_hash?: string | null;
  occurrence_date: string;
}

export interface LifeMilestoneResponse extends LifeMilestoneCreate {
  id: number;
  user_id: number;
  milestone_nft_id: string | null;
  created_at: string;
}

// ==========================================
// خدمة التوأم الرقمي
// ==========================================
export const DigitalTwinService = {
  // ==========================================
  // 1. إعدادات التوأم الرقمي
  // ==========================================

  /**
   * جلب إعدادات التوأم الرقمي للمستخدم الحالي
   */
  getMyTwinConfig: async (): Promise<TwinConfig> => {
    try {
      const { data } = await apiClient.get('/api/digital-twin/config');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب إعدادات التوأم الرقمي');
    }
  },

  /**
   * تحديث إعدادات التوأم الرقمي
   */
  updateTwinConfig: async (payload: TwinConfigCreate): Promise<TwinConfig> => {
    try {
      const { data } = await apiClient.put('/api/digital-twin/config', payload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل تحديث إعدادات التوأم الرقمي');
    }
  },

  // ==========================================
  // 2. التفاعل مع التوأم الرقمي
  // ==========================================

  /**
   * التفاعل مع التوأم الرقمي لمستخدم آخر
   */
  interactWithTwin: async (ownerId: number, payload: TwinInteractionCreate): Promise<TwinInteractionResponse> => {
    try {
      const { data } = await apiClient.post(`/api/digital-twin/interact/${ownerId}`, payload, {
        headers: {
          'Idempotency-Key': generateIdempotencyKey(),
        },
      });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل التفاعل مع التوأم الرقمي');
    }
  },

  // ==========================================
  // 3. كبسولة الزمن
  // ==========================================

  /**
   * إنشاء كبسولة زمنية جديدة
   */
  createTimeCapsule: async (payload: TimeCapsuleCreate, beneficiaries: BeneficiaryCreate[]): Promise<TimeCapsuleResponse> => {
    try {
      const { data } = await apiClient.post('/api/digital-twin/time-capsule', {
        data: payload,
        beneficiaries,
      });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل إنشاء كبسولة الزمن');
    }
  },

  /**
   * جلب كبسولة الزمن الخاصة بي
   */
  getMyTimeCapsule: async (): Promise<TimeCapsuleResponse> => {
    try {
      const { data } = await apiClient.get('/api/digital-twin/time-capsule');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب كبسولة الزمن');
    }
  },

  /**
   * إرسال نبضة قلب (Heartbeat) للحفاظ على نشاط الكبسولة
   */
  sendHeartbeat: async (): Promise<void> => {
    try {
      await apiClient.post('/api/digital-twin/time-capsule/heartbeat');
    } catch (error) {
      throw handleError(error, 'فشل إرسال نبضة القلب');
    }
  },

  // ==========================================
  // 4. الوصية الرقمية
  // ==========================================

  /**
   * إنشاء وصية رقمية
   */
  createDigitalWill: async (payload: DigitalWillCreate): Promise<DigitalWillResponse> => {
    try {
      const { data } = await apiClient.post('/api/digital-twin/will', payload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل إنشاء الوصية الرقمية');
    }
  },

  // ==========================================
  // 5. الأحداث الحياتية
  // ==========================================

  /**
   * إضافة حدث حياتي جديد
   */
  addLifeMilestone: async (payload: LifeMilestoneCreate): Promise<LifeMilestoneResponse> => {
    try {
      const { data } = await apiClient.post('/api/digital-twin/milestones', payload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل إضافة الحدث الحياتي');
    }
  },

  /**
   * جلب الأحداث الحياتية الخاصة بي
   */
  getMyMilestones: async (): Promise<LifeMilestoneResponse[]> => {
    try {
      const { data } = await apiClient.get('/api/digital-twin/milestones');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب الأحداث الحياتية');
    }
  },

  /**
   * حجز هوية ما قبل الولادة (Pre-birth identity)
   */
  reservePreBirthIdentity: async (payload: {
    parent_1_id: number;
    parent_2_id?: number | null;
    reserved_sovereign_id: string;
    trust_fund_wallet?: string | null;
    expected_arrival_date?: string | null;
    genetic_profile_hash?: string | null;
  }): Promise<any> => {
    try {
      const { data } = await apiClient.post('/api/digital-twin/pre-birth', payload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل حجز الهوية ما قبل الولادة');
    }
  },
};