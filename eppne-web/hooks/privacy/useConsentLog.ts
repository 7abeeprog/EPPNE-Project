// hooks/privacy/useConsentLog.ts
import { useMutation } from "@tanstack/react-query";
import { PrivacyService } from "@/services/privacy.service";
import { toast } from "sonner";

export const useConsentLog = () => {
    return useMutation({
        mutationFn: ({
            consent_type,
            granted,
        }: {
            consent_type: string;
            granted: boolean;
        }) => PrivacyService.logConsent(consent_type, granted),
        onSuccess: () => {
            toast.success('تم تسجيل الموافقة بنجاح');
        },
        onError: (error: any) => {
            toast.error(error.message || 'فشل تسجيل الموافقة');
        },
    });
};