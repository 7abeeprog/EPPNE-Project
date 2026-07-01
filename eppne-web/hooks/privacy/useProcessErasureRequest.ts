// hooks/privacy/useProcessErasureRequest.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { PrivacyService } from "@/services/privacy.service";
import { ProcessErasureRequestPayload } from "@/types/privacy";
import { toast } from "sonner";
import { ERASURE_REQUESTS_QUERY_KEY } from "./useErasureRequests";

export const useProcessErasureRequest = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({
            requestId,
            payload,
        }: {
            requestId: number;
            payload: ProcessErasureRequestPayload;
        }) => PrivacyService.processErasureRequest(requestId, payload),
        onSuccess: (data) => {
            toast.success(data.message || 'تمت معالجة الطلب بنجاح');
            queryClient.invalidateQueries({ queryKey: ERASURE_REQUESTS_QUERY_KEY });
        },
        onError: (error: any) => {
            toast.error(error.message || 'فشل معالجة الطلب');
        },
    });
};