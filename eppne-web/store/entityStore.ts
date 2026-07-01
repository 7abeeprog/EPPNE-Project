// store/entityStore.ts
import { create } from 'zustand';
import type { SovereignEntity } from '@/types/sovereign-entities';

interface EntityStore {
  activeEntity: SovereignEntity | null;
  activeEntityId: number | null;
  setActiveEntity: (entity: SovereignEntity) => void;
  clearActiveEntity: () => void;
  // التحقق من التطابق مع المسار
  syncWithRoute: (entityId: number | null, fetchFn: () => Promise<SovereignEntity>) => Promise<void>;
}

export const useEntityStore = create<EntityStore>((set, get) => ({
  activeEntity: null,
  activeEntityId: null,

  setActiveEntity: (entity) => set({ activeEntity: entity, activeEntityId: entity.id }),

  clearActiveEntity: () => set({ activeEntity: null, activeEntityId: null }),

  syncWithRoute: async (entityId, fetchFn) => {
    const { activeEntityId } = get();
    
    // إذا كان نفس الكيان، لا نفعل شيئاً
    if (activeEntityId === entityId && get().activeEntity) {
      return;
    }

    // إذا كان مختلفاً، نمسح القديم ونجلب الجديد
    if (activeEntityId !== entityId) {
      set({ activeEntity: null, activeEntityId: null });
    }

    if (entityId) {
      try {
        const response = await fetchFn();
        set({ activeEntity: response, activeEntityId: response.id });
      } catch (error) {
        set({ activeEntity: null, activeEntityId: null });
        throw error;
      }
    }
  }
}));