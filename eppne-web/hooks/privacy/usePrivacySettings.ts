// hooks/privacy/usePrivacySettings.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PrivacyService } from "@/services/privacy.service";
import { PrivacySettings, UpdatePrivacySettingsPayload } from "@/types/privacy";
import { toast } from "sonner";

export const PRIVACY_SETTINGS_QUERY_KEY = ['privacy', 'settings'];

/**
 * جلب إعدادات الخصوصية للمستخدم الحالي
 */
export const usePrivacySettings = () => {
    return useQuery({
        queryKey: PRIVACY_SETTINGS_QUERY_KEY,
        queryFn: () => PrivacyService.getPrivacySettings(),
        staleTime: 5 * 60 * 1000, // 5 دقائق
        refetchOnWindowFocus: true,
    });
};

/**
 * تحديث إعدادات الخصوصية
 */
export const useUpdatePrivacySettings = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (payload: UpdatePrivacySettingsPayload) =>
            PrivacyService.updatePrivacySettings(payload),
        onSuccess: () => {
            toast.success('تم تحديث إعدادات الخصوصية بنجاح');
            queryClient.invalidateQueries({ queryKey: PRIVACY_SETTINGS_QUERY_KEY });
        },
        onError: (error: any) => {
            toast.error(error.message || 'فشل تحديث إعدادات الخصوصية');
        },
    });
};