// services/ai-agents.ts
import api from '@/lib/axios';
import type {
  AIAgent,
  AgentApproval,
  AgentApprovalQueue,
  AITaskLog,
  AgentFormData,
  AgentRole,
  AgentStatus,
  AgentAnalytics,
  AgentStatusResponse,
} from '@/types/ai-agents';

// ============================================================
// 1. إدارة الوكلاء (Agents)
// ============================================================

export const getAgents = (params?: {
  role?: AgentRole;
  status?: AgentStatus;
  skip?: number;
  limit?: number;
}) => api.get<AIAgent[]>('/ai/agents', { params });

export const getAgent = (agentId: number) =>
  api.get<AIAgent>(`/ai/agents/${agentId}`);

export const createAgent = (data: AgentFormData) =>
  api.post<AIAgent>('/ai/agents', data);

export const updateAgentStatus = (agentId: number, data: { status: AgentStatus }) =>
  api.patch<AIAgent>(`/ai/agents/${agentId}/status`, data);

export const deleteAgent = (agentId: number, soft: boolean = true) =>
  api.delete(`/ai/agents/${agentId}?soft=${soft}`);

// ============================================================
// 2. تنفيذ الإجراءات (مع Idempotency)
// ============================================================

export const executeAgentAction = (
  agentId: number,
  actionType: string,
  payload: Record<string, any>,
  idempotencyKey?: string
) =>
  api.post(
    `/ai/agents/${agentId}/execute`,
    { action_type: actionType, payload },
    {
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
    }
  );

// ============================================================
// 3. الموافقات البشرية (Human Approvals)
// ============================================================

export const getPendingApprovals = () =>
  api.get<AgentApprovalQueue[]>('/ai/approvals/pending');

export const getApprovals = (params?: {
  agent_id?: number;
  status?: 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED';
  skip?: number;
  limit?: number;
}) => api.get<AgentApprovalQueue[]>('/ai/approvals', { params });

export const getApproval = (approvalId: number) =>
  api.get<AgentApprovalQueue>(`/ai/approvals/${approvalId}`);

export const resolveApproval = (
  approvalId: number,
  data: {
    status: 'APPROVED' | 'REJECTED' | 'CANCELLED';
    human_feedback?: string;
  }
) => api.post(`/ai/approvals/${approvalId}/resolve`, data);

// ============================================================
// 4. سجلات المهام (Task Logs)
// ============================================================

export const getAgentTaskLogs = (
  agentId: number,
  params?: { skip?: number; limit?: number; task_type?: string }
) => api.get<AITaskLog[]>(`/ai/agents/${agentId}/logs`, { params });

export const getTaskLogs = (params?: {
  agent_id?: number;
  user_id?: number;
  task_type?: string;
  skip?: number;
  limit?: number;
}) => api.get<AITaskLog[]>('/ai/logs', { params });

// ============================================================
// 5. التحليلات والإحصائيات
// ============================================================

export const getAgentAnalytics = (agentId: number, days: number = 30) =>
  api.get<AgentAnalytics>(`/ai/agents/${agentId}/analytics`, { params: { days } });

export const getAgentStatus = (agentId: number) =>
  api.get<AgentStatusResponse>(`/ai/agents/${agentId}/status`);

// ============================================================
// 6. دوال إضافية (للراحة)
// ============================================================

export const getMyAgents = (params?: {
  role?: AgentRole;
  status?: AgentStatus;
  skip?: number;
  limit?: number;
}) => api.get<AIAgent[]>('/ai/agents/my', { params });