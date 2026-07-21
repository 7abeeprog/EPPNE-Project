// services/privacy.service.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";

type PrivacySettingResponse = components['schemas']['PrivacySettingResponse'];
type PrivacySettingUpdate = components['schemas']['PrivacySettingUpdate'];
type DataErasureRequestCreate = components['schemas']['DataErasureRequestCreate'];
type DataErasureRequestResponse = components['schemas']['DataErasureRequestResponse'];
type PaginatedErasureRequestResponse = components['schemas']['PaginatedErasureRequestResponse'];

export const PrivacyService = {
    // ==========================================
    // 1. إعدادات الخصوصية (Privacy Settings)
    // ==========================================
    /**
     * جلب إعدادات الخصوصية للمستخدم الحالي
     * GET /privacy/privacy/settings
     */
    getPrivacySettings: async (): Promise<PrivacySettingResponse> => {
        try {
            const { data } = await apiClient.get<PrivacySettingResponse>("/privacy/privacy/settings", {
                withCredentials: true,
            });
            return data;
        } catch (error) {
            throw handleError(error, "فشل جلب إعدادات الخصوصية");
        }
    },

    /**
     * تحديث إعدادات الخصوصية للمستخدم الحالي
     * PUT /privacy/privacy/settings
     */
    updatePrivacySettings: async (data: PrivacySettingUpdate): Promise<PrivacySettingResponse> => {
        try {
            const { data: result } = await apiClient.put<PrivacySettingResponse>("/privacy/privacy/settings", data, {
                withCredentials: true,
            });
            return result;
        } catch (error) {
            throw handleError(error, "فشل تحديث إعدادات الخصوصية");
        }
    },

    // ==========================================
    // 2. سجلات الموافقات (Consent Logs)
    // ==========================================
    /**
     * تسجيل موافقة المستخدم على معالجة البيانات
     * POST /privacy/privacy/consent/log
     */
    logConsent: async (type: string, granted: boolean): Promise<void> => {
        try {
            await apiClient.post("/privacy/privacy/consent/log", undefined, {
                params: { type, granted },
                withCredentials: true,
            });
        } catch (error) {
            throw handleError(error, "فشل تسجيل الموافقة");
        }
    },

    // ==========================================
    // 3. طلبات محو البيانات (Erasure Requests)
    // ==========================================
    /**
     * إنشاء طلب محو بيانات جديد
     * POST /privacy/privacy/erasure/request
     */
    createErasureRequest: async (data: DataErasureRequestCreate): Promise<DataErasureRequestResponse> => {
        try {
            const { data: result } = await apiClient.post<DataErasureRequestResponse>(
                "/privacy/privacy/erasure/request",
                data,
                { withCredentials: true }
            );
            return result;
        } catch (error) {
            throw handleError(error, "فشل إنشاء طلب المحو");
        }
    },

    /**
     * جلب طلبات محو البيانات الخاصة بي (مع Pagination)
     * GET /privacy/privacy/erasure/requests
     */
    listMyErasureRequests: async (
        params?: {
            offset?: number;
            size?: number;
            state?: string | null;
        }
    ): Promise<PaginatedErasureRequestResponse> => {
        try {
            const { data } = await apiClient.get<PaginatedErasureRequestResponse>(
                "/privacy/privacy/erasure/requests",
                { params, withCredentials: true }
            );
            return data;
        } catch (error) {
            throw handleError(error, "فشل جلب طلبات المحو");
        }
    },

    // ==========================================
    // 4. إدارة المشرفين (Admin Only)
    // ==========================================
    /**
     * جلب طلبات المحو المعلقة (للمشرفين فقط)
     * GET /privacy/privacy/admin/erasure/pending
     */
    getPendingErasureRequests: async (
        params?: { offset?: number; size?: number }
    ): Promise<PaginatedErasureRequestResponse> => {
        try {
            const { data } = await apiClient.get<PaginatedErasureRequestResponse>(
                "/privacy/privacy/admin/erasure/pending",
                { params, withCredentials: true }
            );
            return data;
        } catch (error) {
            throw handleError(error, "فشل جلب الطلبات المعلقة");
        }
    },

    /**
     * معالجة طلب محو بيانات (للمشرفين فقط)
     * POST /privacy/privacy/admin/erasure/{request_id}/process
     */
    processErasureRequest: async (
        requestId: number,
        params: { approved: boolean; comment?: string | null }
    ): Promise<void> => {
        try {
            const id = Number(requestId);
            if (isNaN(id)) throw new Error("معرف الطلب غير صحيح");
            await apiClient.post(`/privacy/privacy/admin/erasure/${id}/process`, undefined, {
                params,
                withCredentials: true,
            });
        } catch (error) {
            throw handleError(error, "فشل معالجة الطلب");
        }
    },
};