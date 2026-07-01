// hooks/privacy/useErasureRequests.ts
import { useQuery, useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PrivacyService } from "@/services/privacy.service";
import { ErasureStatus } from "@/types/privacy";

export const ERASURE_REQUESTS_QUERY_KEY = ['privacy', 'erasure-requests'];

/**
 * 1. جلب طلبات المستخدم (Pagination)
 */
export const useErasureRequests = (skip: number = 0, limit: number = 20, status?: ErasureStatus) => {
    return useQuery({
        queryKey: [...ERASURE_REQUESTS_QUERY_KEY, 'list', skip, limit, status],
        queryFn: () => PrivacyService.getErasureRequests(skip, limit, status as any), // تمرير status بشكل آمن
        staleTime: 60 * 1000,
        // Polling ذكي للطلبات المعلقة فقط
        refetchInterval: (query) => {
            const data = query.state.data;
            if (!data) return false;
            const hasPending = data.data.some(req => req.status === 'PENDING' || req.status === 'PROCESSING');
            return hasPending ? 5000 : false;
        },
    });
};

/**
 * 2. إنشاء طلب محو جديد
 */
export const useCreateErasureRequest = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: PrivacyService.createErasureRequest,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ERASURE_REQUESTS_QUERY_KEY }),
    });
};

/**
 * 3. جلب الطلبات المعلقة (للمشرفين)
 */
export const usePendingErasureRequests = (skip: number = 0, limit: number = 50) => {
    return useQuery({
        queryKey: [...ERASURE_REQUESTS_QUERY_KEY, 'pending', skip, limit],
        queryFn: () => PrivacyService.getPendingErasureRequests(skip, limit),
        refetchInterval: 5000, // تحديث مستمر للمشرفين
    });
};

/**
 * 4. معالجة طلب المحو (للمشرفين)
 */
export const useProcessErasureRequest = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ requestId, approve, notes }: { requestId: number; approve: boolean; notes?: string }) =>
            PrivacyService.processErasureRequest(requestId, approve, notes),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ERASURE_REQUESTS_QUERY_KEY }),
    });
};

/**
 * 5. النسخة المحدثة للـ Infinite Scroll
 */
export const useInfiniteErasureRequests = (limit: number = 20, status?: ErasureStatus) => {
    return useInfiniteQuery({
        queryKey: [...ERASURE_REQUESTS_QUERY_KEY, 'infinite', status],
        // تم إزالة المعامل الثالث (status) من هنا ليتوافق مع توقيع الدالة في الخدمة
        queryFn: ({ pageParam = 0 }) => PrivacyService.getErasureRequests(pageParam as number, limit),
        initialPageParam: 0,
        getNextPageParam: (lastPage, allPages) => {
            const totalFetched = allPages.reduce((acc, page) => acc + page.data.length, 0);
            return totalFetched < lastPage.total ? totalFetched : undefined;
        },
    });
};