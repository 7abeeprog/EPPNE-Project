// hooks/use-entities.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";
import { toast } from "sonner";
import { CreateEntityPayload, KYBDocumentUploadPayload } from "@/types/entity";

// 🟢 1. جلب الكيانات الخاصة بالمستخدم
export const useMyEntities = () => {
  const { isAuthenticated } = useAuthStore();

  const { 
    data: entities = [], 
    isLoading, 
    error, 
    refetch 
  } = useQuery({
    queryKey: ['entities', 'my-entities'],
    queryFn: async () => {
      const response = await apiClient.get('/sovereign-entities/me'); 
      return response.data;
    },
    enabled: !!isAuthenticated,
    staleTime: 1000 * 60 * 5,
  });

  return { entities, isLoading, error, refetch };
};

// 🟢 2. جلب تفاصيل الكيان (التي كانت مفقودة لحل الخطأ)
export const useEntityDetails = (entityId: number) => {
  const isIdValid = !!entityId && entityId > 0;

  const { 
    data: entity = null, 
    isLoading: isEntityLoading, 
    error: entityError 
  } = useQuery({
    queryKey: ['entities', 'details', entityId],
    queryFn: async () => {
      const response = await apiClient.get(`/sovereign-entities/${entityId}`);
      return response.data;
    },
    enabled: isIdValid,
    staleTime: 1000 * 60 * 5,
  });

  const { 
    data: representatives = [], 
    isLoading: isRepsLoading, 
    error: repsError 
  } = useQuery({
    queryKey: ['entities', 'representatives', entityId],
    queryFn: async () => {
      const response = await apiClient.get(`/sovereign-entities/${entityId}/representatives`);
      return response.data;
    },
    enabled: isIdValid,
    staleTime: 1000 * 60 * 5,
  });

  const { 
    data: documents = [], 
    isLoading: isDocsLoading, 
    error: docsError 
  } = useQuery({
    queryKey: ['entities', 'documents', entityId],
    queryFn: async () => {
      const response = await apiClient.get(`/sovereign-entities/${entityId}/kyb/documents`);
      return response.data;
    },
    enabled: isIdValid,
    staleTime: 1000 * 60 * 5,
  });

  const isLoading = isEntityLoading || isRepsLoading || isDocsLoading;
  const error = entityError || repsError || docsError;

  return { 
    entity, 
    representatives, 
    documents, 
    isLoading, 
    error 
  };
};

// 🟢 3. محركات العمليات (Mutations)
export const useEntityMutations = (entityId?: number) => {
  const queryClient = useQueryClient();

  const createEntity = useMutation({
    mutationFn: async (payload: CreateEntityPayload) => {
      const cleanPayload = Object.fromEntries(
        Object.entries(payload).map(([k, v]) => [k, v === "" ? null : v])
      );
      const response = await apiClient.post("/sovereign-entities/", cleanPayload);
      return response.data;
    },
    onSuccess: () => {
      toast.success("تم تأسيس الكيان السيادي بنجاح! 🏛️");
      queryClient.invalidateQueries({ queryKey: ['entities', 'my-entities'] });
    },
    onError: (err: any) => {
      const errorMessage = err.response?.data?.detail || "فشل إنشاء الكيان";
      toast.error(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
    }
  });

  const updateEntity = useMutation({
    mutationFn: async (payload: Partial<CreateEntityPayload>) => {
      if (!entityId) throw new Error("Entity ID is required");
      const response = await apiClient.put(`/sovereign-entities/${entityId}`, payload);
      return response.data;
    },
    onSuccess: () => {
      toast.success("تم تحديث البيانات السيادية بنجاح!");
      queryClient.invalidateQueries({ queryKey: ['entities', 'my-entities'] });
      if (entityId) queryClient.invalidateQueries({ queryKey: ['entities', 'details', entityId] });
    },
    onError: () => toast.error("فشل تحديث بيانات الكيان.")
  });

  const uploadDocument = useMutation({
    mutationFn: async (payload: KYBDocumentUploadPayload) => {
      if (!entityId) throw new Error("Entity ID is required");
      const response = await apiClient.post(`/sovereign-entities/${entityId}/kyb/documents`, payload);
      return response.data;
    },
    onSuccess: () => {
      toast.success("تم تشفير ورفع المستند السيادي بنجاح!");
      if (entityId) queryClient.invalidateQueries({ queryKey: ['entities', 'documents', entityId] });
    },
    onError: () => toast.error("فشل رفع المستند.")
  });

  return {
    createEntity,
    updateEntity,
    uploadDocument
  };
};