// store/academy-ui-store.ts
import { create } from "zustand";

interface AcademyUIState {
  // ==========================================
  // 1. حالة التنقل والاختيار
  // ==========================================
  selectedCourseId: number | null;
  setSelectedCourseId: (id: number | null) => void;

  // ==========================================
  // 2. حالة الشجرة التنظيمية (توسيع/طي العقد)
  // ==========================================
  expandedNodes: Record<number, boolean>;
  toggleNode: (nodeId: number) => void;
  collapseAll: () => void;

  // ==========================================
  // 3. حالة البحث والتصفية
  // ==========================================
  searchQuery: string;
  setSearchQuery: (query: string) => void;

  // ==========================================
  // 4. حالة التحميل المحلي (للأزرار الفردية)
  // ==========================================
  isSubmitting: boolean;
  setSubmitting: (status: boolean) => void;

  // ==========================================
  // 5. إعادة ضبط الحالة (عند الخروج)
  // ==========================================
  reset: () => void;
}

export const useAcademyUIStore = create<AcademyUIState>((set) => ({
  // القيم الابتدائية
  selectedCourseId: null,
  expandedNodes: {},
  searchQuery: "",
  isSubmitting: false,

  // ==========================================
  // الدوال
  // ==========================================
  setSelectedCourseId: (id) => set({ selectedCourseId: id }),

  toggleNode: (nodeId) =>
    set((state) => ({
      expandedNodes: {
        ...state.expandedNodes,
        [nodeId]: !state.expandedNodes[nodeId],
      },
    })),

  collapseAll: () => set({ expandedNodes: {} }),

  setSearchQuery: (query) => set({ searchQuery: query }),

  setSubmitting: (status) => set({ isSubmitting: status }),

  reset: () =>
    set({
      selectedCourseId: null,
      expandedNodes: {},
      searchQuery: "",
      isSubmitting: false,
    }),
}));