// store/agentStore.ts
import { create } from 'zustand';
import { AIAgentsService, AIAgentResponse, ApprovalResponse, AIAgentCreate, ApprovalResolution } from '@/services/ai-agents.service';
import { useNotificationStore } from './notificationStore';

interface AgentState {
  agents: AIAgentResponse[];
  approvals: ApprovalResponse[];
  isLoading: boolean;
  error: string | null;
  fetchAgents: (params?: { role?: string; status?: string }) => Promise<void>;
  createAgent: (payload: AIAgentCreate) => Promise<AIAgentResponse>;
  updateAgentStatus: (agentId: number, status: string) => Promise<void>;
  executeAgentAction: (agentId: number, actionType: string, payload: Record<string, any>) => Promise<any>;
  fetchPendingApprovals: () => Promise<void>;
  resolveApproval: (approvalId: number, resolution: ApprovalResolution) => Promise<void>;
  addApproval: (approval: ApprovalResponse) => void; // للـ WebSocket
}

export const useAgentStore = create<AgentState>((set, get) => ({
  agents: [],
  approvals: [],
  isLoading: false,
  error: null,

  fetchAgents: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const data = await AIAgentsService.listAgents(params);
      set({ agents: data, isLoading: false });
    } catch (error: any) {
      set({ isLoading: false, error: error.message });
    }
  },

  createAgent: async (payload) => {
    set({ isLoading: true, error: null });
    try {
      const newAgent = await AIAgentsService.createAgent(payload);
      set((state) => ({ agents: [newAgent, ...state.agents], isLoading: false }));

      // إشعار للمشرفين
      const notificationStore = useNotificationStore.getState();
      notificationStore.addNotification({
        id: Date.now(),
        user_id: 0, // سيتم استبداله
        title: '🤖 وكيل جديد',
        body: `تم إنشاء وكيل "${payload.name}" بنجاح`,
        data: { link: '/dashboard/ai-agents' },
        is_read: false,
        priority: 'NORMAL',
        created_at: new Date().toISOString(),
      });

      return newAgent;
    } catch (error: any) {
      set({ isLoading: false, error: error.message });
      throw error;
    }
  },

  updateAgentStatus: async (agentId, status) => {
    try {
      const updated = await AIAgentsService.updateAgentStatus(agentId, status as any);
      set((state) => ({
        agents: state.agents.map((a) => (a.id === agentId ? updated : a)),
      }));
    } catch (error: any) {
      set({ error: error.message });
      throw error;
    }
  },

  executeAgentAction: async (agentId, actionType, payload) => {
    set({ isLoading: true });
    try {
      const result = await AIAgentsService.executeAgentAction(agentId, actionType, payload);
      set({ isLoading: false });
      return result;
    } catch (error: any) {
      set({ isLoading: false, error: error.message });
      throw error;
    }
  },

  fetchPendingApprovals: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await AIAgentsService.getPendingApprovals();
      set({ approvals: data, isLoading: false });
    } catch (error: any) {
      set({ isLoading: false, error: error.message });
    }
  },

  resolveApproval: async (approvalId, resolution) => {
    try {
      await AIAgentsService.resolveApproval(approvalId, resolution);
      // إزالة الموافقة من القائمة المعلقة
      set((state) => ({
        approvals: state.approvals.filter((a) => a.id !== approvalId),
      }));

      // إشعار
      const notificationStore = useNotificationStore.getState();
      notificationStore.addNotification({
        id: Date.now(),
        user_id: 0,
        title: '✅ تم حل الموافقة',
        body: `تم ${resolution.status === 'APPROVED' ? 'الموافقة على' : 'رفض'} الإجراء #${approvalId}`,
        data: { link: '/dashboard/ai/approvals' },
        is_read: false,
        priority: 'NORMAL',
        created_at: new Date().toISOString(),
      });
    } catch (error: any) {
      set({ error: error.message });
      throw error;
    }
  },

  addApproval: (approval) => {
    set((state) => ({
      approvals: [approval, ...state.approvals],
    }));
  },
}));