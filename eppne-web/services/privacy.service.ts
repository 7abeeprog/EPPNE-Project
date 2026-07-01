// services/privacy.service.ts
import { apiClient } from "@/lib/api-client";
import {
    PrivacySettings,
    ErasureRequest,
    PaginatedResponse,
    UpdatePrivacySettingsPayload,
    CreateErasureRequestPayload,
} from "@/types/privacy";
import { handleError } from "@/lib/error-handler";

export const PrivacyService = {
    // ==========================================
    // 1. إعدادات الخصوصية (Privacy Settings)
    // ==========================================

    /**
     * جلب إعدادات الخصوصية للمستخدم الحالي
     */
    getPrivacySettings: async (): Promise<PrivacySettings> => {
        try {
            const { data } = await apiClient.get<PrivacySettings>('/privacy/settings');
            return data;
        } catch (error) {
            throw handleError(error, 'فشل جلب إعدادات الخصوصية');
        }
    },

    /**
     * تحديث إعدادات الخصوصية للمستخدم الحالي
     */
    updatePrivacySettings: async (
        payload: UpdatePrivacySettingsPayload
    ): Promise<PrivacySettings> => {
        try {
            const { data } = await apiClient.put<PrivacySettings>('/privacy/settings', payload);
            return data;
        } catch (error) {
            throw handleError(error, 'فشل تحديث إعدادات الخصوصية');
        }
    },

    // ==========================================
    // 2. طلبات محو البيانات (Erasure Requests)
    // ==========================================

    /**
     * جلب طلبات محو البيانات الخاصة بالمستخدم (مع Pagination)
     */
    getErasureRequests: async (
        skip: number = 0,
        limit: number = 20,
        status?: string
    ): Promise<PaginatedResponse<ErasureRequest>> => {
        try {
            const { data } = await apiClient.get<PaginatedResponse<ErasureRequest>>('/privacy/erasure/requests', {
                params: { skip, limit, status },
            });
            return data;
        } catch (error) {
            throw handleError(error, 'فشل جلب طلبات المحو');
        }
    },

    /**
     * إنشاء طلب محو بيانات جديد
     */
    createErasureRequest: async (
        payload: CreateErasureRequestPayload
    ): Promise<ErasureRequest> => {
        try {
            const { data } = await apiClient.post<ErasureRequest>('/privacy/erasure/request', payload);
            return data;
        } catch (error) {
            throw handleError(error, 'فشل إنشاء طلب المحو');
        }
    },

    // ==========================================
    // 3. إدارة المشرفين (Admin Only)
    // ==========================================

    /**
     * جلب طلبات المحو المعلقة (للمشرفين فقط)
     */
    getPendingErasureRequests: async (
        skip: number = 0,
        limit: number = 50
    ): Promise<PaginatedResponse<ErasureRequest>> => {
        try {
            const { data } = await apiClient.get<PaginatedResponse<ErasureRequest>>('/privacy/admin/erasure/pending', {
                params: { skip, limit },
            });
            return data;
        } catch (error) {
            throw handleError(error, 'فشل جلب الطلبات المعلقة');
        }
    },

    /**
     * معالجة طلب محو بيانات (قبول/رفض) – للمشرفين فقط
     * @param requestId معرف الطلب المراد معالجته
     * @param approve قرار المشرف: صحيح (قبول) أو خطأ (رفض)
     * @param notes سجل التدقيق: ملاحظات المشرف على القرار
     */
    processErasureRequest: async (
        requestId: number,
        approve: boolean,
        notes?: string
    ): Promise<{ status: string; receipt_tx?: string; message: string }> => {
        try {
            const { data } = await apiClient.post<{ status: string; receipt_tx?: string; message: string }>(
                `/privacy/admin/erasure/${requestId}/process`,
                null,
                {
                    params: { approve, notes },
                }
            );
            return data;
        } catch (error) {
            throw handleError(error, 'فشل معالجة الطلب');
        }
    },

    // ==========================================
    // 4. سجلات الموافقات (Consent Logs)
    // ==========================================

    /**
     * تسجيل موافقة المستخدم على معالجة البيانات
     */
    logConsent: async (consent_type: string, granted: boolean): Promise<void> => {
        try {
            await apiClient.post('/privacy/consent/log', null, {
                params: { consent_type, granted },
            });
        } catch (error) {
            throw handleError(error, 'فشل تسجيل الموافقة');
        }
    },
};