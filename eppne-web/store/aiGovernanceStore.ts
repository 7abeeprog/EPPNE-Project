// store/aiGovernanceStore.ts
import { create } from 'zustand';
import type { AgentQuota, AgentRateLimit, AgentAuditLog } from '@/types/ai-governance';

interface AIGovernanceState {
  selectedAgentId: number | null;
  quotas: AgentQuota[];
  rateLimits: AgentRateLimit | null;
  auditLogs: AgentAuditLog[];
  isLoading: boolean;
  setSelectedAgentId: (id: number | null) => void;
  setQuotas: (quotas: AgentQuota[]) => void;
  setRateLimits: (limits: AgentRateLimit) => void;
  setAuditLogs: (logs: AgentAuditLog[]) => void;
  addAuditLog: (log: AgentAuditLog) => void;
  clear: () => void;
}

export const useAIGovernanceStore = create<AIGovernanceState>((set) => ({
  selectedAgentId: null,
  quotas: [],
  rateLimits: null,
  auditLogs: [],
  isLoading: false,

  setSelectedAgentId: (id) => set({ selectedAgentId: id }),
  setQuotas: (quotas) => set({ quotas }),
  setRateLimits: (limits) => set({ rateLimits: limits }),
  setAuditLogs: (logs) => set({ auditLogs: logs }),
  addAuditLog: (log) =>
    set((state) => ({ auditLogs: [log, ...state.auditLogs] })),
  clear: () =>
    set({ selectedAgentId: null, quotas: [], rateLimits: null, auditLogs: [] }),
}));