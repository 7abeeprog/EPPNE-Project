// store/aiAgentStore.ts
import { create } from 'zustand';
import type { AIAgent, ApprovalRequest } from '@/types/ai-agents';

interface AIAgentStore {
  // حالة الوكلاء
  agents: AIAgent[];
  selectedAgent: AIAgent | null;
  selectedAgentId: number | null;

  // حالة الموافقات
  pendingApprovals: ApprovalRequest[];
  pendingApprovalsCount: number;
  selectedApproval: ApprovalRequest | null;

  // إجراءات الوكلاء
  setAgents: (agents: AIAgent[]) => void;
  setSelectedAgent: (agent: AIAgent | null) => void;
  clearSelectedAgent: () => void;

  // إجراءات الموافقات
  setPendingApprovals: (approvals: ApprovalRequest[]) => void;
  setSelectedApproval: (approval: ApprovalRequest | null) => void;
  addPendingApproval: (approval: ApprovalRequest) => void;
  removePendingApproval: (approvalId: number) => void;
  updateApprovalStatus: (approvalId: number, status: ApprovalRequest['status']) => void;

  // إجراءات مساعدة
  incrementPendingApprovals: () => void;
  decrementPendingApprovals: () => void;
}

export const useAIAgentStore = create<AIAgentStore>((set) => ({
  // الحالة الابتدائية
  agents: [],
  selectedAgent: null,
  selectedAgentId: null,
  pendingApprovals: [],
  pendingApprovalsCount: 0,
  selectedApproval: null,

  // إجراءات الوكلاء
  setAgents: (agents) => set({ agents }),
  
  setSelectedAgent: (agent) =>
    set({
      selectedAgent: agent,
      selectedAgentId: agent?.id ?? null,
    }),
  
  clearSelectedAgent: () =>
    set({
      selectedAgent: null,
      selectedAgentId: null,
    }),

  // إجراءات الموافقات
  setPendingApprovals: (approvals) =>
    set({
      pendingApprovals: approvals,
      pendingApprovalsCount: approvals.length,
    }),

  setSelectedApproval: (approval) => set({ selectedApproval: approval }),

  addPendingApproval: (approval) =>
    set((state) => ({
      pendingApprovals: [approval, ...state.pendingApprovals],
      pendingApprovalsCount: state.pendingApprovalsCount + 1,
    })),

  removePendingApproval: (approvalId) =>
    set((state) => ({
      pendingApprovals: state.pendingApprovals.filter((a) => a.id !== approvalId),
      pendingApprovalsCount: Math.max(0, state.pendingApprovalsCount - 1),
    })),

  updateApprovalStatus: (approvalId, status) =>
    set((state) => {
      const updatedApprovals = state.pendingApprovals.map((a) =>
        a.id === approvalId ? { ...a, status } : a
      );
      const stillPending = updatedApprovals.filter((a) => a.status === 'PENDING');
      return {
        pendingApprovals: stillPending,
        pendingApprovalsCount: stillPending.length,
      };
    }),

  // إجراءات مساعدة
  incrementPendingApprovals: () =>
    set((state) => ({
      pendingApprovalsCount: state.pendingApprovalsCount + 1,
    })),

  decrementPendingApprovals: () =>
    set((state) => ({
      pendingApprovalsCount: Math.max(0, state.pendingApprovalsCount - 1),
    })),
}));