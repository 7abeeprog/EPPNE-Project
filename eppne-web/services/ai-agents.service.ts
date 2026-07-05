// services/ai-agents.service.ts
import { apiClient } from "@/lib/api-client";
import { generateIdempotencyKey } from "@/lib/utils";
import { handleError } from "@/lib/error-handler";

// تطابق Schemas من OpenAPI
export interface AIAgentCreate {
  name: string;
  role: 'CEO' | 'SWARM_ORCHESTRATOR' | 'CLIMATE_BROKER' | 'ARBITRATOR' | 'SURVIVAL_CRISIS' | 'PHILANTHROPY' | 'SALES_NEGOTIATOR' | 'DEVOPS_ARCHITECT' | 'IOT_CONTROLLER' | 'HEALTH_BIO' | 'ACCESSIBILITY' | 'EDUCATOR' | 'DIGITAL_TWIN' | 'SUPPORT';
  system_prompt: string;
  base_model?: string;
  can_execute_payments?: boolean;
  can_sign_contracts?: boolean;
  requires_human_approval?: boolean;
  interaction_cost_mrusdt?: number;
}

export interface AIAgentResponse extends AIAgentCreate {
  id: number;
  status: 'IDLE' | 'ACTIVE' | 'LEARNING' | 'SUSPENDED';
  owner_id: number | null;
  tenant_id: number | null;
  agent_wallet_address: string | null;
  created_at: string;
}

export interface AgentStatusUpdate {
  status: 'IDLE' | 'ACTIVE' | 'LEARNING' | 'SUSPENDED';
}

export interface ApprovalResponse {
  id: number;
  agent_id: number;
  human_approver_id: number;
  action_type: string;
  proposed_payload: Record<string, any>;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED';
  human_feedback: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface ApprovalResolution {
  status: 'APPROVED' | 'REJECTED';
  human_feedback?: string | null;
}

export const AIAgentsService = {
  // ==========================================
  // 1. إدارة الوكلاء
  // ==========================================

  /**
   * جلب قائمة الوكلاء
   * @param {Object} params - معاملات التصفية
   * @param {string} params.role - دور الوكيل (اختياري)
   * @param {string} params.status - حالة الوكيل (اختياري)
   * @param {number} params.skip - عدد العناصر المتخطية
   * @param {number} params.limit - عدد العناصر في الصفحة
   */
  listAgents: async (params?: { role?: string; status?: string; skip?: number; limit?: number }): Promise<AIAgentResponse[]> => {
    try {
      const { data } = await apiClient.get('/api/ai/agents', { params });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب قائمة الوكلاء');
    }
  },

  /**
   * إنشاء وكيل جديد
   */
  createAgent: async (payload: AIAgentCreate): Promise<AIAgentResponse> => {
    try {
      const { data } = await apiClient.post('/api/ai/agents', payload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل إنشاء الوكيل');
    }
  },

  /**
   * جلب تفاصيل وكيل
   */
  getAgent: async (agentId: number): Promise<AIAgentResponse> => {
    try {
      const { data } = await apiClient.get(`/api/ai/agents/${agentId}`);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب تفاصيل الوكيل');
    }
  },

  /**
   * تحديث حالة الوكيل
   */
  updateAgentStatus: async (agentId: number, status: AgentStatusUpdate['status']): Promise<AIAgentResponse> => {
    try {
      const { data } = await apiClient.patch(`/api/ai/agents/${agentId}/status`, { status });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل تحديث حالة الوكيل');
    }
  },

  /**
   * تنفيذ إجراء بواسطة الوكيل
   */
  executeAgentAction: async (agentId: number, actionType: string, payload: Record<string, any>): Promise<any> => {
    try {
      const { data } = await apiClient.post(`/api/ai/agents/${agentId}/execute`, payload, {
        params: { action_type: actionType },
        headers: {
          'Idempotency-Key': generateIdempotencyKey(),
        },
      });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل تنفيذ الإجراء');
    }
  },

  /**
   * حذف وكيل (حذف منطقي)
   */
  deleteAgent: async (agentId: number, soft: boolean = true): Promise<void> => {
    try {
      await apiClient.delete(`/api/ai/agents/${agentId}`, { params: { soft } });
    } catch (error) {
      throw handleError(error, 'فشل حذف الوكيل');
    }
  },

  // ==========================================
  // 2. إدارة الموافقات البشرية
  // ==========================================

  /**
   * جلب الموافقات المعلقة
   */
  getPendingApprovals: async (): Promise<ApprovalResponse[]> => {
    try {
      const { data } = await apiClient.get('/api/ai/approvals/pending');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب الموافقات المعلقة');
    }
  },

  /**
   * جلب جميع الموافقات (مع فلترة)
   */
  listApprovals: async (params?: { agent_id?: number; status?: string; skip?: number; limit?: number }): Promise<ApprovalResponse[]> => {
    try {
      const { data } = await apiClient.get('/api/ai/approvals', { params });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب قائمة الموافقات');
    }
  },

  /**
   * جلب تفاصيل موافقة محددة
   */
  getApproval: async (approvalId: number): Promise<ApprovalResponse> => {
    try {
      const { data } = await apiClient.get(`/api/ai/approvals/${approvalId}`);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب تفاصيل الموافقة');
    }
  },

  /**
   * حل الموافقة (موافقة أو رفض)
   */
  resolveApproval: async (approvalId: number, resolution: ApprovalResolution): Promise<void> => {
    try {
      await apiClient.post(`/api/ai/approvals/${approvalId}/resolve`, resolution);
    } catch (error) {
      throw handleError(error, 'فشل حل الموافقة');
    }
  },
};