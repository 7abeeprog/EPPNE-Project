// services/affiliate.service.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";

type AffiliateProfileResponse = components['schemas']['AffiliateProfileResponse'];
type AffiliateProfileUpdate = components['schemas']['AffiliateProfileUpdate'];
type AffiliateLinkCreate = components['schemas']['AffiliateLinkCreate'];
type AffiliateLinkResponse = components['schemas']['AffiliateLinkResponse'];
type PaginatedResponse = components['schemas']['PaginatedResponse'];
type WithdrawRequest = components['schemas']['WithdrawRequest'];
type WithdrawResponse = components['schemas']['WithdrawResponse'];
type AffiliateStatsResponse = components['schemas']['AffiliateStatsResponse'];

export const AffiliateService = {
  /**
   * جلب ملف الداعي السيادي
   * GET /affiliate/affiliate/profile
   */
  getProfile: async (): Promise<AffiliateProfileResponse> => {
    try {
      const { data } = await apiClient.get<AffiliateProfileResponse>("/affiliate/affiliate/profile", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب ملف الداعي");
    }
  },

  /**
   * تحديث ملف الداعي
   * PUT /affiliate/affiliate/profile
   */
  updateProfile: async (data: AffiliateProfileUpdate): Promise<AffiliateProfileResponse> => {
    try {
      const { data: result } = await apiClient.put<AffiliateProfileResponse>("/affiliate/affiliate/profile", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث ملف الداعي");
    }
  },

  /**
   * جلب روابط الدعوة الخاصة بالمستخدم
   * GET /affiliate/affiliate/links
   */
  getLinks: async (params?: { skip?: number; limit?: number }): Promise<PaginatedResponse> => {
    try {
      const { data } = await apiClient.get<PaginatedResponse>("/affiliate/affiliate/links", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب روابط الدعوة");
    }
  },

  /**
   * إنشاء رابط دعوة مخصص
   * POST /affiliate/affiliate/links
   */
  createLink: async (data: AffiliateLinkCreate): Promise<AffiliateLinkResponse> => {
    try {
      const { data: result } = await apiClient.post<AffiliateLinkResponse>("/affiliate/affiliate/links", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء رابط الدعوة");
    }
  },

  /**
   * جلب سجل العمولات حسب الحالة
   * GET /affiliate/affiliate/commissions
   */
  getCommissions: async (params?: { status?: string | null; skip?: number; limit?: number }): Promise<PaginatedResponse> => {
    try {
      const { data } = await apiClient.get<PaginatedResponse>("/affiliate/affiliate/commissions", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب العمولات");
    }
  },

  /**
   * إفراج العمولات المعلقة (تحويلها إلى العمليات الحسابية)
   * POST /affiliate/affiliate/commissions/release
   */
  releaseCommissions: async (): Promise<void> => {
    try {
      await apiClient.post("/affiliate/affiliate/commissions/release", undefined, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل إفراج العمولات");
    }
  },

  /**
   * طلب سحب العمولات المستحقة إلى المحفظة
   * POST /affiliate/affiliate/withdraw
   */
  withdraw: async (data: WithdrawRequest): Promise<WithdrawResponse> => {
    try {
      const { data: result } = await apiClient.post<WithdrawResponse>("/affiliate/affiliate/withdraw", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل سحب العمولات");
    }
  },

  /**
   * جلب إحصائيات الأداء (النقرات، التحويلات، الأرباح)
   * GET /affiliate/affiliate/stats
   */
  getStats: async (): Promise<AffiliateStatsResponse> => {
    try {
      const { data } = await apiClient.get<AffiliateStatsResponse>("/affiliate/affiliate/stats", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب إحصائيات الداعي");
    }
  },

  /**
   * جلب شجرة الإحالة الخاصة بالمستخدم
   * GET /affiliate/affiliate/tree
   */
  getReferralTree: async (params?: { max_depth?: number }): Promise<any[]> => {
    try {
      const { data } = await apiClient.get<any[]>("/affiliate/affiliate/tree", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب شجرة الإحالة");
    }
  },

  /**
   * تتبع نقرات روابط الدعوة (مسار عام للمستخدمين غير المسجلين)
   * GET /affiliate/affiliate/track/{referral_code}
   */
  trackReferralClick: async (
    referralCode: string,
    params?: {
      target?: string | null;
      product_id?: number | null;
      utm_source?: string | null;
      utm_medium?: string | null;
      utm_campaign?: string | null;
    }
  ): Promise<void> => {
    try {
      await apiClient.get(`/affiliate/affiliate/track/${referralCode}`, {
        params,
      });
    } catch (error) {
      throw handleError(error, "فشل تتبع النقرة");
    }
  },
};