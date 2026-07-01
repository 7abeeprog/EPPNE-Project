// hooks/use-enterprise.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { AxiosError } from 'axios';

// ==========================================
// 1. تعريف الهياكل الصارمة (Strict Interfaces)
// ==========================================
export interface OrgEntity {
  id: number;
  tenant_id: number;
  parent_id: number | null;
  name: string;
  entity_type: string;
  description?: string;
  is_active: boolean;
}

export interface Cohort {
  id: number;
  org_entity_id: number;
  name: string;
  start_date?: string;
  end_date?: string;
  max_capacity?: number;
}

// ==========================================
// 🛡️ درع معالجة الأخطاء
// ==========================================
const handleApiError = (error: unknown, defaultMessage: string): string => {
  if (error && typeof error === "object" && "isAxiosError" in error) {
    const axiosError = error as AxiosError<{ detail?: string; message?: string }>;
    const detail = axiosError.response?.data?.detail;
    if (typeof detail === "string") return detail;
    return axiosError.response?.data?.message || defaultMessage;
  }
  return defaultMessage;
};

// ==========================================
// 2. مفاتيح الاستعلام السيادية (Query Keys)
// ==========================================
export const enterpriseKeys = {
  all: ['enterprise'] as const,
  entities: (tenantId: number) => [...enterpriseKeys.all, 'entities', tenantId] as const,
  cohorts: (orgEntityId: number) => [...enterpriseKeys.all, 'cohorts', orgEntityId] as const,
};

// ==========================================
// 3. محرك جلب البيانات (TanStack Queries)
// ==========================================
export const useEnterpriseQueries = () => {
  return {
    useEntities: (tenantId: number) => useQuery({
      queryKey: enterpriseKeys.entities(tenantId),
      queryFn: () => apiClient.get(`/academy/entities?tenant_id=${tenantId}`).then(res => res.data as OrgEntity[]),
      enabled: !!tenantId,
      staleTime: 1000 * 60 * 10,
    }),

    useCohorts: (orgEntityId: number) => useQuery({
      queryKey: enterpriseKeys.cohorts(orgEntityId),
      queryFn: () => apiClient.get(`/academy/cohorts?org_entity_id=${orgEntityId}`).then(res => res.data as Cohort[]),
      enabled: !!orgEntityId,
    }),
  };
};

// ==========================================
// 4. محرك العمليات (TanStack Mutations)
// ==========================================
export const useEnterpriseMutations = () => {
  const queryClient = useQueryClient();

  return {
    createCohort: useMutation({
      mutationFn: (data: Partial<Cohort>) => apiClient.post('/academy/cohorts', data).then(res => res.data),
      onSuccess: (_, variables) => {
        toast.success("تم تشكيل الدفعة السيادية بنجاح!");
        if (variables.org_entity_id) {
          queryClient.invalidateQueries({ queryKey: enterpriseKeys.cohorts(variables.org_entity_id) });
        }
      },
      onError: (e) => toast.error(handleApiError(e, "فشل إنشاء الدفعة"))
    })
  };
};