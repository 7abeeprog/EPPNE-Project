// types/ai-governance.ts
export type UsagePeriod = 'DAILY' | 'WEEKLY' | 'MONTHLY' | 'YEARLY';
export type LimitType = 'REQUEST_COUNT' | 'TOKEN_COUNT' | 'COST_MRUSDT' | 'CONCURRENT';

export interface AgentQuota {
  id: number;
  agent_id: number;
  limit_type: LimitType;
  period: UsagePeriod;
  limit_value: number;
  current_usage: number;
  reset_at: string;
  created_at: string;
  updated_at: string;
}

export interface AgentRateLimit {
  agent_id: number;
  requests_per_minute: number;
  requests_per_hour: number;
  concurrent_limit: number;
  created_at: string;
  updated_at: string;
}

export interface AgentUsageSummary {
  agent_id: number;
  total_requests: number;
  total_tokens: number;
  total_cost_mrusdt: number;
  avg_response_time_ms: number;
  period: string;
}

export interface AgentUsageLog {
  id: number;
  agent_id: number;
  user_id?: number;
  action_type: string;
  request_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_mrusdt: number;
  response_time_ms?: number;
  status: 'SUCCESS' | 'FAILED' | 'QUOTA_EXCEEDED';
  error_message?: string;
  created_at: string;
}

export interface AgentAuditLog {
  id: number;
  agent_id: number;
  admin_user_id: number;
  action: 'CREATE' | 'UPDATE' | 'SUSPEND' | 'ACTIVATE' | 'CHANGE_QUOTA' | 'CHANGE_RATE_LIMIT';
  old_value?: Record<string, any>;
  new_value?: Record<string, any>;
  ip_address?: string;
  created_at: string;
}

// ========== UI Types ==========
export interface QuotaFormData {
  limit_type: LimitType;
  period: UsagePeriod;
  limit_value: number;
}

export interface RateLimitFormData {
  requests_per_minute: number;
  requests_per_hour: number;
  concurrent_limit: number;
}

export interface QuotaUsage {
  quota: AgentQuota;
  usage_percentage: number;
  is_exceeded: boolean;
  is_warning: boolean; // > 80%
}

export interface AgentGovernanceSummary {
  agent_id: number;
  agent_name: string;
  quotas: QuotaUsage[];
  rate_limits: AgentRateLimit;
  usage_summary: AgentUsageSummary;
}