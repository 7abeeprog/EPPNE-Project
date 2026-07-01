// hooks/use-brand-builder.ts
import { useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useBrandBuilderStore, PageStructure } from "@/store/brand-builder-store";
import { toast } from "sonner";

// 🟢 الهيكل الافتراضي السيادي (يُستخدم إذا كان الخادم فارغاً)
const DEFAULT_STRUCTURE: PageStructure = {
  sections: [
    {
      id: "hero-section",
      name: "القسم الرئيسي",
      layout: "full-width",
      props: { bgColor: "transparent", paddingTop: 4, paddingBottom: 4 },
      components: [
        {
          id: crypto.randomUUID(),
          type: "hero",
          props: {
            title: "مرحباً بكم في منصتنا السيادية",
            subtitle: "نحن نقدم حلولاً مبتكرة للمستقبل",
            buttonText: "تواصل معنا",
            buttonLink: "/contact",
            backgroundImage: "",
            paddingTop: 6, paddingBottom: 6, paddingRight: 4, paddingLeft: 4,
            isGlass: true, hasNeon: true, neonColor: "#06b6d4",
            bgColor: "transparent", textColor: "#ffffff", fontWeight: "800", rounded: 24,
          },
        },
      ],
    },
  ],
};

export const useBrandBuilder = (entityId: number) => {
  const queryClient = useQueryClient();
  const initStructure = useBrandBuilderStore((state) => state.initStructure);
  const currentDraft = useBrandBuilderStore((state) => state.pageStructure);

  // 1. جلب الهيكل من الخادم
  const { isLoading: isFetching, error: fetchError } = useQuery({
    queryKey: ['brand-builder', 'page', entityId],
    queryFn: async () => {
      const response = await apiClient.get(`/sovereign-entities/${entityId}/page`);
      const pageData = response.data.page;
      
      // بمجرد وصول البيانات، نقوم بحقنها في المسودة المحلية (Zustand)
      if (pageData?.structure) {
        initStructure(pageData.structure);
      } else {
        initStructure(DEFAULT_STRUCTURE);
      }
      return pageData?.structure || DEFAULT_STRUCTURE;
    },
    enabled: !!entityId,
    staleTime: Infinity, // الكاش لا يفسد أبداً أثناء التعديل لمنع إعادة الكتابة فوق مسودة المستخدم
    refetchOnWindowFocus: false, // نمنع إعادة الجلب التلقائي أثناء بناء الصفحة
  });

  // 2. محرك حفظ الهيكل في الخادم
  const saveMutation = useMutation({
    mutationFn: async (structureToSave: PageStructure) => {
      await apiClient.put(`/sovereign-entities/${entityId}/page`, {
        custom_structure: structureToSave,
      });
    },
    onSuccess: () => {
      toast.success("تم تشفير واعتماد الهيكل البصري بنجاح! 🚀");
      queryClient.invalidateQueries({ queryKey: ['brand-builder', 'page', entityId] });
    },
    onError: (err: any) => {
      toast.error(err.message || "فشل اعتماد الهيكل السيادي.");
    }
  });

  const savePage = () => {
    if (!currentDraft) {
      toast.error("المسودة فارغة، لا يوجد ما يمكن حفظه.");
      return;
    }
    saveMutation.mutate(currentDraft);
  };

  return {
    isFetching,
    isSaving: saveMutation.isPending,
    fetchError,
    savePage,
  };
};