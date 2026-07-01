// store/saas-store.ts
import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { ServiceCatalog, ServicePlan, TenantSubscription, Invoice, FeatureFlag } from "@/types/saas";

interface SaasUIState {
  // ✅ حالة الواجهة (UI State)
  selectedServiceId: number | null;
  selectedPlanId: number | null;
  selectedSubscriptionId: number | null;
  isSubscriptionModalOpen: boolean;
  isInvoiceModalOpen: boolean;
  isLoading: boolean;
  error: string | null;

  // ✅ دوال التحديث
  setSelectedServiceId: (id: number | null) => void;
  setSelectedPlanId: (id: number | null) => void;
  setSelectedSubscriptionId: (id: number | null) => void;
  setSubscriptionModalOpen: (open: boolean) => void;
  setInvoiceModalOpen: (open: boolean) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useSaasStore = create<SaasUIState>()(
  devtools(
    (set) => ({
      // الحالة الابتدائية
      selectedServiceId: null,
      selectedPlanId: null,
      selectedSubscriptionId: null,
      isSubscriptionModalOpen: false,
      isInvoiceModalOpen: false,
      isLoading: false,
      error: null,

      // الدوال
      setSelectedServiceId: (id) => set({ selectedServiceId: id }),
      setSelectedPlanId: (id) => set({ selectedPlanId: id }),
      setSelectedSubscriptionId: (id) => set({ selectedSubscriptionId: id }),
      setSubscriptionModalOpen: (open) => set({ isSubscriptionModalOpen: open }),
      setInvoiceModalOpen: (open) => set({ isInvoiceModalOpen: open }),
      setLoading: (loading) => set({ isLoading: loading }),
      setError: (error) => set({ error }),
      reset: () =>
        set({
          selectedServiceId: null,
          selectedPlanId: null,
          selectedSubscriptionId: null,
          isSubscriptionModalOpen: false,
          isInvoiceModalOpen: false,
          isLoading: false,
          error: null,
        }),
    }),
    { name: 'saas-store' }
  )
);