// store/entity-store.ts
import { create } from "zustand";

interface EntityUIState {
  // 🟢 يمكن استخدام هذه الحالات للتحكم في الواجهة دون المساس بالخادم
  isCreateModalOpen: boolean;
  selectedDocumentId: number | null;
  
  setCreateModalOpen: (isOpen: boolean) => void;
  setSelectedDocumentId: (id: number | null) => void;
}

export const useEntityUIStore = create<EntityUIState>((set) => ({
  isCreateModalOpen: false,
  selectedDocumentId: null,
  
  setCreateModalOpen: (isOpen) => set({ isCreateModalOpen: isOpen }),
  setSelectedDocumentId: (id) => set({ selectedDocumentId: id }),
}));