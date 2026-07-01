// store/brand-builder-store.ts
import { create } from "zustand";
import { persist } from "zustand/middleware";

// --- الأنواع الأساسية (ثابتة وآمنة) ---
export interface Component {
  id: string;
  type: string;
  props: Record<string, any>; // تبقى any لأن الـ Props تختلف حسب نوع المكون
}

export interface Section {
  id: string;
  name: string;
  layout: string;
  props?: Record<string, any>;
  components: Component[];
}

export interface PageStructure {
  sections: Section[];
}

// --- ✅ الواجهة الآن نظيفة تماماً وخالية من 'any' الخطير ---
interface BrandBuilderState {
  pageStructure: PageStructure | null; // ✅ تم الإرجاع إلى النوع الصحيح
  isLoading: boolean;
  error: string | null;
  selectedComponentId: string | null;

  // دوال جلب البيانات من الخادم
  fetchPageStructure: (entityId: number) => Promise<void>;
  savePageStructure: (entityId: number, structure: PageStructure) => Promise<void>; // ✅ تم إصلاح النوع هنا أيضاً

  // دوال التحرير المحلية
  initStructure: (structure: PageStructure) => void;
  addSection: (section: Section) => void;
  removeSection: (sectionId: string) => void;
  updateSectionLayout: (sectionId: string, layout: string) => void;
  updateSectionProps: (sectionId: string, props: Record<string, any>) => void;
  addComponentToSection: (sectionId: string, component: Component, index?: number) => void;
  removeComponent: (sectionId: string, componentId: string) => void;
  updateComponentProps: (sectionId: string, componentId: string, props: Record<string, any>) => void;
  moveComponent: (fromSectionId: string, toSectionId: string, componentId: string, newIndex: number) => void;
  setSelectedComponent: (componentId: string | null) => void;
  reorderSections: (sections: Section[]) => void;

  // دالة إعادة ضبط الحالة
  reset: () => void;
}

// --- متغيرات خارجية لإدارة الطلبات ومنع التكرار (Deduplication) ---
let abortController: AbortController | null = null;
const pendingRequests = new Map<string, Promise<void>>();

export const useBrandBuilderStore = create<BrandBuilderState>()(
  persist(
    (set, get) => ({
      // الحالة الابتدائية
      pageStructure: null,
      isLoading: false,
      error: null,
      selectedComponentId: null,

      // ---------- دوال جلب البيانات ----------
      fetchPageStructure: async (entityId: number) => {
        const requestKey = `fetch-${entityId}`;
        if (pendingRequests.has(requestKey)) {
          return pendingRequests.get(requestKey)!;
        }

        const promise = (async () => {
          if (abortController) {
            abortController.abort();
          }
          abortController = new AbortController();
          const signal = abortController.signal;

          set({ isLoading: true, error: null });

          try {
            const response = await fetch(`/api/brand-structure/${entityId}`, {
              signal,
              headers: { 'Content-Type': 'application/json' },
              cache: 'no-store',
            });

            if (!response.ok) {
              throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data: PageStructure = await response.json();

            // ✅ التحقق من صحة البيانات باستخدام النوع الحقيقي
            if (!data || typeof data !== 'object' || !Array.isArray(data.sections)) {
              throw new Error('Invalid structure format received from server');
            }

            set({
              pageStructure: data,
              isLoading: false,
              error: null,
            });
          } catch (error: any) {
            if (error.name === 'AbortError') {
              return;
            }
            set({
              isLoading: false,
              error: error.message || 'Failed to load page structure',
            });
            console.error('[BrandBuilder] fetch error:', error);
          } finally {
            pendingRequests.delete(requestKey);
          }
        })();

        pendingRequests.set(requestKey, promise);
        return promise;
      },

      // ✅ الآن تستقبل هيكل من النوع الصحيح تماماً
      savePageStructure: async (entityId: number, structure: PageStructure) => {
        set({ isLoading: true, error: null });

        try {
          // تحقق أمان إضافي (رغم أن TypeScript يضمنه)
          if (!structure || typeof structure !== 'object' || !Array.isArray(structure.sections)) {
            throw new Error('Invalid structure to save');
          }

          const response = await fetch(`/api/brand-structure/${entityId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(structure),
          });

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }

          const updated: PageStructure = await response.json();
          set({
            pageStructure: updated,
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          set({
            isLoading: false,
            error: error.message || 'Failed to save structure',
          });
          console.error('[BrandBuilder] save error:', error);
          throw error;
        }
      },

      // ---------- دوال التحرير المحلية (مع دعم كامل للأنواع) ----------
      initStructure: (structure: PageStructure) => {
        set({ pageStructure: structure, error: null });
      },

      addSection: (section: Section) => {
        const structure = get().pageStructure;
        if (structure) {
          set({
            pageStructure: {
              ...structure,
              sections: [...structure.sections, section],
            },
          });
        }
      },

      removeSection: (sectionId: string) => {
        const structure = get().pageStructure;
        if (structure) {
          set({
            pageStructure: {
              ...structure,
              sections: structure.sections.filter((s) => s.id !== sectionId),
            },
          });
        }
      },

      updateSectionLayout: (sectionId: string, layout: string) => {
        const structure = get().pageStructure;
        if (structure) {
          set({
            pageStructure: {
              ...structure,
              sections: structure.sections.map((s) =>
                s.id === sectionId ? { ...s, layout } : s
              ),
            },
          });
        }
      },

      updateSectionProps: (sectionId: string, props: Record<string, any>) => {
        const structure = get().pageStructure;
        if (structure) {
          set({
            pageStructure: {
              ...structure,
              sections: structure.sections.map((s) =>
                s.id === sectionId ? { ...s, props: { ...s.props, ...props } } : s
              ),
            },
          });
        }
      },

      addComponentToSection: (sectionId: string, component: Component, index?: number) => {
        const structure = get().pageStructure;
        if (structure) {
          const targetSection = structure.sections.find((s) => s.id === sectionId);
          if (targetSection) {
            const newComponents = [...targetSection.components];
            const insertIndex = index !== undefined ? index : newComponents.length;
            newComponents.splice(insertIndex, 0, component);
            set({
              pageStructure: {
                ...structure,
                sections: structure.sections.map((s) =>
                  s.id === sectionId ? { ...s, components: newComponents } : s
                ),
              },
            });
          }
        }
      },

      removeComponent: (sectionId: string, componentId: string) => {
        const structure = get().pageStructure;
        if (structure) {
          set({
            pageStructure: {
              ...structure,
              sections: structure.sections.map((s) =>
                s.id === sectionId
                  ? { ...s, components: s.components.filter((c) => c.id !== componentId) }
                  : s
              ),
            },
          });
        }
      },

      updateComponentProps: (sectionId: string, componentId: string, props: Record<string, any>) => {
        const structure = get().pageStructure;
        if (structure) {
          set({
            pageStructure: {
              ...structure,
              sections: structure.sections.map((s) =>
                s.id === sectionId
                  ? {
                      ...s,
                      components: s.components.map((c) =>
                        c.id === componentId ? { ...c, props: { ...c.props, ...props } } : c
                      ),
                    }
                  : s
              ),
            },
          });
        }
      },

      moveComponent: (fromSectionId: string, toSectionId: string, componentId: string, newIndex: number) => {
        const structure = get().pageStructure;
        if (structure) {
          const fromSection = structure.sections.find((s) => s.id === fromSectionId);
          const toSection = structure.sections.find((s) => s.id === toSectionId);
          if (fromSection && toSection) {
            const component = fromSection.components.find((c) => c.id === componentId);
            if (component) {
              const newFromComponents = fromSection.components.filter((c) => c.id !== componentId);
              const newToComponents = [...toSection.components];
              newToComponents.splice(newIndex, 0, component);
              set({
                pageStructure: {
                  ...structure,
                  sections: structure.sections.map((s) => {
                    if (s.id === fromSectionId) return { ...s, components: newFromComponents };
                    if (s.id === toSectionId) return { ...s, components: newToComponents };
                    return s;
                  }),
                },
              });
            }
          }
        }
      },

      setSelectedComponent: (componentId: string | null) => set({ selectedComponentId: componentId }),

      reorderSections: (sections: Section[]) => {
        const structure = get().pageStructure;
        if (structure) {
          set({ pageStructure: { ...structure, sections } });
        }
      },

      reset: () => {
        if (abortController) {
          abortController.abort();
          abortController = null;
        }
        pendingRequests.clear();
        set({
          pageStructure: null,
          isLoading: false,
          error: null,
          selectedComponentId: null,
        });
      },
    }),
    {
      name: "brand-builder-storage",
      partialize: (state) => ({
        pageStructure: state.pageStructure,
        selectedComponentId: state.selectedComponentId,
      }),
    }
  )
);