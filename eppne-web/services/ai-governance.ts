// services/ai-governance.ts
import api from '@/lib/axios';
import type {
  AgentQuota,
  AgentRateLimit,
  AgentUsageSummary,
  AgentUsageLog,
  AgentAuditLog,
  QuotaFormData,
  RateLimitFormData,
} from '@/types/ai-governance';

// ========== Quotas ==========
export const getAgentQuotas = (agentId: number) =>
  api.get<AgentQuota[]>(`/ai-governance/agents/${agentId}/quotas`);

export const setAgentQuota = (agentId: number, data: QuotaFormData) =>
  api.post<AgentQuota>(`/ai-governance/agents/${agentId}/quotas`, data);

// ========== Rate Limits ==========
export const getAgentRateLimits = (agentId: number) =>
  api.get<AgentRateLimit>(`/ai-governance/agents/${agentId}/rate-limit`);

export const updateAgentRateLimits = (agentId: number, data: RateLimitFormData) =>
  api.put<AgentRateLimit>(`/ai-governance/agents/${agentId}/rate-limit`, data);

// ========== Usage Summary ==========
export const getAgentUsageSummary = (agentId: number, period?: string) =>
  api.get<AgentUsageSummary>(`/ai-governance/agents/${agentId}/usage-summary`, {
    params: { period },
  });

export const getAgentUsageLogs = (agentId: number, params?: { skip?: number; limit?: number }) =>
  api.get<AgentUsageLog[]>(`/ai-governance/agents/${agentId}/usage-logs`, { params });

// ========== Audit Logs ==========
export const getAgentAuditLogs = (agentId: number, params?: { skip?: number; limit?: number }) =>
  api.get<AgentAuditLog[]>(`/ai-governance/agents/${agentId}/audit-logs`, { params });