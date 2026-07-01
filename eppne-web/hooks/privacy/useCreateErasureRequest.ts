// hooks/privacy/useCreateErasureRequest.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { PrivacyService } from "@/services/privacy.service";
import { CreateErasureRequestPayload } from "@/types/privacy";
import { toast } from "sonner";
import { ERASURE_REQUESTS_QUERY_KEY } from "./useErasureRequests";

export const useCreateErasureRequest = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (payload: CreateErasureRequestPayload) =>
            PrivacyService.createErasureRequest(payload),
        onSuccess: () => {
            toast.success('تم إنشاء طلب محو البيانات بنجاح');
            queryClient.invalidateQueries({ queryKey: ERASURE_REQUESTS_QUERY_KEY });
        },
        onError: (error: any) => {
            toast.error(error.message || 'فشل إنشاء طلب محو البيانات');
        },
    });
};