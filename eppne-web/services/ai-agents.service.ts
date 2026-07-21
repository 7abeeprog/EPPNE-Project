// services/ai-agents.service.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

type AIAgentCreate = components['schemas']['AIAgentCreate'];
type AIAgentResponse = components['schemas']['AIAgentResponse'];
type AgentStatusUpdate = components['schemas']['AgentStatusUpdate'];
type AgentStatusResponse = components['schemas']['AgentStatusResponse'];
type ApprovalResponse = components['schemas']['ApprovalResponse'];
type ApprovalResolution = components['schemas']['ApprovalResolution'];

export const AIAgentsService = {
  /**
   * جلب قائمة الوكلاء مع إمكانية التصفية
   * GET /ai/agents
   * تدعم X-Tenant-ID في الهيدر
   */
  listAgents: async (
    params?: {
      role?: string | null;
      status?: string | null;
      skip?: number;
      limit?: number;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<AIAgentResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<AIAgentResponse[]>("/ai/agents", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب قائمة الوكلاء");
    }
  },

  /**
   * إنشاء وكيل جديد
   * POST /ai/agents
   * تدعم X-Tenant-ID
   */
  createAgent: async (
    payload: AIAgentCreate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<AIAgentResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.post<AIAgentResponse>("/ai/agents", payload, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الوكيل");
    }
  },

  /**
   * جلب تفاصيل وكيل محدد
   * GET /ai/agents/{agent_id}
   * تدعم X-Tenant-ID
   */
  getAgent: async (agentId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<AIAgentResponse> => {
    try {
      const id = Number(agentId);
      if (isNaN(id)) throw new Error("معرف الوكيل غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<AIAgentResponse>(`/ai/agents/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل الوكيل");
    }
  },

  /**
   * حذف وكيل (حذف منطقي افتراضيًا)
   * DELETE /ai/agents/{agent_id}
   * تدعم X-Tenant-ID
   */
  deleteAgent: async (
    agentId: number,
    soft: boolean = true,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<void> => {
    try {
      const id = Number(agentId);
      if (isNaN(id)) throw new Error("معرف الوكيل غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      await apiClient.delete(`/ai/agents/${id}`, {
        params: { soft },
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل حذف الوكيل");
    }
  },

  /**
   * تحديث حالة الوكيل (تشغيل/إيقاف/تعليق)
   * PATCH /ai/agents/{agent_id}/status
   * تدعم X-Tenant-ID
   */
  updateAgentStatus: async (
    agentId: number,
    data: AgentStatusUpdate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<AIAgentResponse> => {
    try {
      const id = Number(agentId);
      if (isNaN(id)) throw new Error("معرف الوكيل غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.patch<AIAgentResponse>(
        `/ai/agents/${id}/status`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث حالة الوكيل");
    }
  },

  /**
   * جلب الحالة التفصيلية للوكيل (للشاشات)
   * GET /ai/agents/{agent_id}/status
   * تدعم X-Tenant-ID
   */
  getAgentStatus: async (agentId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<AgentStatusResponse> => {
    try {
      const id = Number(agentId);
      if (isNaN(id)) throw new Error("معرف الوكيل غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<AgentStatusResponse>(`/ai/agents/${id}/status`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب حالة الوكيل");
    }
  },

  /**
   * تنفيذ إجراء بواسطة الوكيل (مع دعم Idempotency)
   * POST /ai/agents/{agent_id}/execute
   */
  executeAgentAction: async (
    agentId: number,
    actionType: string,
    payload: Record<string, unknown>,
    idempotencyKey?: string,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<unknown> => {
    try {
      const id = Number(agentId);
      if (isNaN(id)) throw new Error("معرف الوكيل غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const key = idempotencyKey || generateIdempotencyKey();
      reqHeaders["Idempotency-Key"] = key;

      const { data } = await apiClient.post<unknown>(
        `/ai/agents/${id}/execute`,
        payload,
        {
          params: { action_type: actionType },
          headers: reqHeaders,
          withCredentials: true,
        }
      );
      return data;
    } catch (error) {
      throw handleError(error, "فشل تنفيذ الإجراء");
    }
  },

  /**
   * جلب تحليلات الوكيل (الإحصائيات)
   * GET /ai/agents/{agent_id}/analytics
   * تدعم X-Tenant-ID
   */
  getAgentAnalytics: async (
    agentId: number,
    days: number = 30,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<unknown> => {
    try {
      const id = Number(agentId);
      if (isNaN(id)) throw new Error("معرف الوكيل غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<unknown>(`/ai/agents/${id}/analytics`, {
        params: { days },
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تحليلات الوكيل");
    }
  },

  /**
   * جلب الموافقات المعلقة فقط
   * GET /ai/approvals/pending
   * تدعم X-Tenant-ID
   */
  getPendingApprovals: async (headers?: { 'X-Tenant-ID'?: number }): Promise<ApprovalResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<ApprovalResponse[]>("/ai/approvals/pending", {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الموافقات المعلقة");
    }
  },

  /**
   * جلب قائمة الموافقات مع فلترة
   * GET /ai/approvals
   * تدعم X-Tenant-ID
   */
  listApprovals: async (
    params?: {
      agent_id?: number | null;
      status?: string | null;
      skip?: number;
      limit?: number;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<ApprovalResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<ApprovalResponse[]>("/ai/approvals", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب قائمة الموافقات");
    }
  },

  /**
   * جلب تفاصيل موافقة محددة
   * GET /ai/approvals/{approval_id}
   * تدعم X-Tenant-ID
   */
  getApproval: async (approvalId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<ApprovalResponse> => {
    try {
      const id = Number(approvalId);
      if (isNaN(id)) throw new Error("معرف الموافقة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<ApprovalResponse>(`/ai/approvals/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل الموافقة");
    }
  },

  /**
   * حل الموافقة (موافقة أو رفض)
   * POST /ai/approvals/{approval_id}/resolve
   * تدعم X-Tenant-ID
   */
  resolveApproval: async (
    approvalId: number,
    resolution: ApprovalResolution,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<void> => {
    try {
      const id = Number(approvalId);
      if (isNaN(id)) throw new Error("معرف الموافقة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      await apiClient.post(`/ai/approvals/${id}/resolve`, resolution, {
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل حل الموافقة");
    }
  },

  /**
   * جلب إحصائيات استخدام الذكاء الاصطناعي للمستأجر الحالي
   * GET /ai/usage
   * تدعم X-Tenant-ID
   */
  getAIUsage: async (headers?: { 'X-Tenant-ID'?: number }): Promise<unknown> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<unknown>("/ai/usage", {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب إحصائيات استخدام الذكاء الاصطناعي");
    }
  },
};