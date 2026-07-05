// store/digitalTwinStore.ts
import { create } from 'zustand';
import { DigitalTwinService, TwinConfig, TimeCapsuleResponse, LifeMilestoneResponse } from '@/services/digital-twin.service';
import { useNotificationStore } from './notificationStore';

interface DigitalTwinState {
  config: TwinConfig | null;
  timeCapsule: TimeCapsuleResponse | null;
  milestones: LifeMilestoneResponse[];
  isLoading: boolean;
  error: string | null;
  fetchConfig: () => Promise<void>;
  updateConfig: (payload: any) => Promise<void>;
  fetchTimeCapsule: () => Promise<void>;
  createTimeCapsule: (data: any, beneficiaries: any[]) => Promise<void>;
  sendHeartbeat: () => Promise<void>;
  fetchMilestones: () => Promise<void>;
  addMilestone: (payload: any) => Promise<void>;
  clearError: () => void;
}

export const useDigitalTwinStore = create<DigitalTwinState>((set, get) => ({
  config: null,
  timeCapsule: null,
  milestones: [],
  isLoading: false,
  error: null,

  fetchConfig: async () => {
    set({ isLoading: true, error: null });
    try {
      const config = await DigitalTwinService.getMyTwinConfig();
      set({ config, isLoading: false });
    } catch (error: any) {
      set({ isLoading: false, error: error.message });
    }
  },

  updateConfig: async (payload) => {
    set({ isLoading: true, error: null });
    try {
      const config = await DigitalTwinService.updateTwinConfig(payload);
      set({ config, isLoading: false });

      const notificationStore = useNotificationStore.getState();
      notificationStore.addNotification({
        id: Date.now(),
        user_id: 0,
        title: '🔄 تم تحديث التوأم الرقمي',
        body: 'تم تحديث إعدادات التوأم الرقمي بنجاح',
        data: { link: '/dashboard/digital-twin' },
        is_read: false,
        priority: 'NORMAL',
        created_at: new Date().toISOString(),
      });
    } catch (error: any) {
      set({ isLoading: false, error: error.message });
      throw error;
    }
  },

  fetchTimeCapsule: async () => {
    set({ isLoading: true, error: null });
    try {
      const timeCapsule = await DigitalTwinService.getMyTimeCapsule();
      set({ timeCapsule, isLoading: false });
    } catch (error: any) {
      set({ isLoading: false, error: error.message });
    }
  },

  createTimeCapsule: async (data, beneficiaries) => {
    set({ isLoading: true, error: null });
    try {
      const timeCapsule = await DigitalTwinService.createTimeCapsule(data, beneficiaries);
      set({ timeCapsule, isLoading: false });

      const notificationStore = useNotificationStore.getState();
      notificationStore.addNotification({
        id: Date.now(),
        user_id: 0,
        title: '📦 تم إنشاء كبسولة الزمن',
        body: 'تم حفظ كبسولة الزمن الخاصة بك بنجاح',
        data: { link: '/dashboard/digital-twin/time-capsule' },
        is_read: false,
        priority: 'HIGH',
        created_at: new Date().toISOString(),
      });
    } catch (error: any) {
      set({ isLoading: false, error: error.message });
      throw error;
    }
  },

  sendHeartbeat: async () => {
    try {
      await DigitalTwinService.sendHeartbeat();
      // تحديث وقت آخر نبضة في الكبسولة
      set((state) => ({
        timeCapsule: state.timeCapsule ? {
          ...state.timeCapsule,
          last_heartbeat_at: new Date().toISOString(),
        } : null,
      }));
    } catch (error: any) {
      set({ error: error.message });
      throw error;
    }
  },

  fetchMilestones: async () => {
    set({ isLoading: true, error: null });
    try {
      const milestones = await DigitalTwinService.getMyMilestones();
      set({ milestones, isLoading: false });
    } catch (error: any) {
      set({ isLoading: false, error: error.message });
    }
  },

  addMilestone: async (payload) => {
    set({ isLoading: true, error: null });
    try {
      const milestone = await DigitalTwinService.addLifeMilestone(payload);
      set((state) => ({
        milestones: [...state.milestones, milestone],
        isLoading: false,
      }));
    } catch (error: any) {
      set({ isLoading: false, error: error.message });
      throw error;
    }
  },

  clearError: () => set({ error: null }),
}));