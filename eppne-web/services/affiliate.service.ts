// services/affiliate.service.ts
import { apiClient } from "@/lib/api-client";
import {
  AffiliateProfile,
  AffiliateLink,
  Commission,
  AffiliateStats,
  WithdrawRequest,
  WithdrawResponse,
  AffiliateDashboardStats,
  ReferralTree,
  PaginatedResponse,
} from "@/types/affiliate";
import { handleError } from "@/lib/error-handler";

export const AffiliateService = {
  // ==========================================
  // 1. ملف الداعي
  // ==========================================
  getProfile: async (): Promise<AffiliateProfile> => {
    try {
      const { data } = await apiClient.get('/affiliate/profile');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب ملف الداعي');
    }
  },

  updateProfile: async (payload: Partial<AffiliateProfile>): Promise<AffiliateProfile> => {
    try {
      const { data } = await apiClient.put('/affiliate/profile', payload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل تحديث ملف الداعي');
    }
  },

  // ==========================================
  // 2. روابط الدعوة
  // ==========================================
  getLinks: async (skip: number = 0, limit: number = 20): Promise<PaginatedResponse<AffiliateLink>> => {
    try {
      const { data } = await apiClient.get('/affiliate/links', {
        params: { skip, limit },
      });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب روابط الدعوة');
    }
  },

  createLink: async (payload: Omit<AffiliateLink, 'id' | 'affiliate_id' | 'clicks' | 'conversions' | 'created_at' | 'updated_at'>): Promise<AffiliateLink> => {
    try {
      const { data } = await apiClient.post('/affiliate/links', payload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل إنشاء رابط الدعوة');
    }
  },

  // ==========================================
  // 3. العمولات
  // ==========================================
  getCommissions: async (skip: number = 0, limit: number = 20, status?: string): Promise<PaginatedResponse<Commission>> => {
    try {
      const { data } = await apiClient.get('/affiliate/commissions', {
        params: { skip, limit, status },
      });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب العمولات');
    }
  },

  releaseCommissions: async (): Promise<void> => {
    try {
      await apiClient.post('/affiliate/commissions/release');
    } catch (error) {
      throw handleError(error, 'فشل إفراج العمولات');
    }
  },

  // ==========================================
  // 4. سحب العمولات
  // ==========================================
  withdraw: async (payload: WithdrawRequest): Promise<WithdrawResponse> => {
    try {
      const { data } = await apiClient.post('/affiliate/withdraw', payload);
      return data;
    } catch (error) {
      throw handleError(error, 'فشل سحب العمولات');
    }
  },

  // ==========================================
  // 5. الإحصائيات
  // ==========================================
  getStats: async (): Promise<AffiliateStats> => {
    try {
      const { data } = await apiClient.get('/affiliate/stats');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب إحصائيات الداعي');
    }
  },

  getDashboardStats: async (): Promise<AffiliateDashboardStats> => {
    try {
      const { data } = await apiClient.get('/affiliate/dashboard/stats');
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب إحصائيات لوحة التحكم');
    }
  },

  // ==========================================
  // 6. شجرة الإحالة
  // ==========================================
  getTree: async (maxDepth: number = 5): Promise<ReferralTree[]> => {
    try {
      const { data } = await apiClient.get('/affiliate/tree', {
        params: { max_depth: maxDepth },
      });
      return data;
    } catch (error) {
      throw handleError(error, 'فشل جلب شجرة الإحالة');
    }
  },

  // ==========================================
  // 7. تتبع الإحالة (مسار عام)
  // ==========================================
  trackReferral: async (referralCode: string, target?: string, productId?: number): Promise<void> => {
    try {
      await apiClient.get(`/affiliate/track/${referralCode}`, {
        params: { target, product_id: productId },
      });
    } catch (error) {
      throw handleError(error, 'فشل تتبع الإحالة');
    }
  },
};