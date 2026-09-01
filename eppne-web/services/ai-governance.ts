// services/ai-governance.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import type { QuotaFormData, RateLimitFormData } from "@/types/ai-governance";

type AgentQuotaResponse = components['schemas']['AgentQuotaResponse'];
type AgentRateLimitResponse = components['schemas']['AgentRateLimitResponse'];
type AgentUsageSummary = components['schemas']['AgentUsageSummary'];
type AgentAuditLogResponse = components['schemas']['AgentAuditLogResponse'];

export const getAgentQuotas = async (agentId: number, headers?: { 'X-Tenant-ID'?: number }) => {
  try {
    const { data } = await apiClient.get<AgentQuotaResponse[]>(`/ai-governance/agents/${agentId}/quotas`, {
      headers,
      withCredentials: true,
    });
    return { data };
  } catch (error) {
    throw handleError(error, "فشل جلب حصص الوكيل");
  }
};

export const setAgentQuota = async (agentId: number, data: QuotaFormData, headers?: { 'X-Tenant-ID'?: number }) => {
  try {
    const { data: result } = await apiClient.post<AgentQuotaResponse>(
      `/ai-governance/agents/${agentId}/quotas`,
      data,
      { headers, withCredentials: true }
    );
    return result;
  } catch (error) {
    throw handleError(error, "فشل تعيين حصة الوكيل");
  }
};

export const getAgentRateLimits = async (agentId: number, headers?: { 'X-Tenant-ID'?: number }) => {
  try {
    const { data } = await apiClient.get<AgentRateLimitResponse | null>(`/ai-governance/agents/${agentId}/rate-limit`, {
      headers,
      withCredentials: true,
    });
    return { data };
  } catch (error) {
    throw handleError(error, "فشل جلب حدود المعدل للوكيل");
  }
};

export const updateAgentRateLimits = async (agentId: number, data: RateLimitFormData, headers?: { 'X-Tenant-ID'?: number }) => {
  try {
    const { data: result } = await apiClient.put<AgentRateLimitResponse>(
      `/ai-governance/agents/${agentId}/rate-limit`,
      data,
      { headers, withCredentials: true }
    );
    return result;
  } catch (error) {
    throw handleError(error, "فشل تحديث حدود المعدل للوكيل");
  }
};

export const getAgentUsageSummary = async (
  agentId: number,
  params?: { period?: string },
  headers?: { 'X-Tenant-ID'?: number }
) => {
  try {
    const { data } = await apiClient.get<AgentUsageSummary>(`/ai-governance/agents/${agentId}/usage-summary`, {
      params,
      headers,
      withCredentials: true,
    });
    return { data };
  } catch (error) {
    throw handleError(error, "فشل جلب ملخص استخدام الوكيل");
  }
};

export const getAgentAuditLogs = async (
  agentId: number,
  params?: { skip?: number; limit?: number },
  headers?: { 'X-Tenant-ID'?: number }
) => {
  try {
    const { data } = await apiClient.get<AgentAuditLogResponse[]>(`/ai-governance/agents/${agentId}/audit-logs`, {
      params,
      headers,
      withCredentials: true,
    });
    return { data };
  } catch (error) {
    throw handleError(error, "فشل جلب سجلات تدقيق الوكيل");
  }
};
