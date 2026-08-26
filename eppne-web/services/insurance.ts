// services/insurance.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

type InsurancePolicyCreate = components['schemas']['InsurancePolicyCreate'];
type InsurancePolicyResponse = components['schemas']['InsurancePolicyResponse'];
type PolicyType = components['schemas']['PolicyType'];
type InsuranceSubscriptionCreate = components['schemas']['InsuranceSubscriptionCreate'];
type InsuranceSubscriptionResponse = components['schemas']['InsuranceSubscriptionResponse'];
type InsuranceClaimCreate = components['schemas']['InsuranceClaimCreate'];
type InsuranceClaimResponse = components['schemas']['InsuranceClaimResponse'];
type ClaimStatus = components['schemas']['ClaimStatus'];
type PensionRecordCreate = components['schemas']['PensionRecordCreate'];
type PensionRecordResponse = components['schemas']['PensionRecordResponse'];
type EmployeeInsuranceProfileCreate = components['schemas']['EmployeeInsuranceProfileCreate'];
type EmployeeInsuranceProfileResponse = components['schemas']['EmployeeInsuranceProfileResponse'];

export const InsuranceService = {
  /**
   * إنشاء سياسة تأمين جديدة
   * POST /insurance/policies
   * تدعم X-Tenant-ID
   */
  createPolicy: async (data: InsurancePolicyCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<InsurancePolicyResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<InsurancePolicyResponse>("/insurance/policies", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء سياسة التأمين");
    }
  },

  /**
   * جلب قائمة سياسات التأمين مع التصفية
   * GET /insurance/policies
   * تدعم X-Tenant-ID
   */
  listPolicies: async (
    params?: {
      policy_type?: PolicyType | null;
      is_active?: boolean | null;
      skip?: number;
      limit?: number;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<InsurancePolicyResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<InsurancePolicyResponse[]>("/insurance/policies", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب سياسات التأمين");
    }
  },

  /**
   * جلب تفاصيل سياسة تأمين محددة
   * GET /insurance/policies/{policy_id}
   * تدعم X-Tenant-ID
   */
  getPolicy: async (policyId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<InsurancePolicyResponse> => {
    try {
      const id = Number(policyId);
      if (isNaN(id)) throw new Error("معرف السياسة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<InsurancePolicyResponse>(`/insurance/policies/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل سياسة التأمين");
    }
  },

  /**
   * الاشتراك في سياسة تأمين
   * POST /insurance/subscriptions
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  subscribe: async (
    data: InsuranceSubscriptionCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<InsuranceSubscriptionResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<InsuranceSubscriptionResponse>(
        "/insurance/subscriptions",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل الاشتراك في التأمين");
    }
  },

  /**
   * جلب اشتراكات التأمين الخاصة بي
   * GET /insurance/subscriptions/me
   * تدعم X-Tenant-ID
   */
  getMySubscriptions: async (
    params?: {
      status?: string | null;
      skip?: number;
      limit?: number;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<InsuranceSubscriptionResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<InsuranceSubscriptionResponse[]>("/insurance/subscriptions/me", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب اشتراكاتي");
    }
  },

  /**
   * تجديد اشتراك تأمين
   * POST /insurance/subscriptions/{subscription_id}/renew
   * تدعم X-Tenant-ID
   */
  renewSubscription: async (
    subscriptionId: number,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<InsuranceSubscriptionResponse> => {
    try {
      const id = Number(subscriptionId);
      if (isNaN(id)) throw new Error("معرف الاشتراك غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<InsuranceSubscriptionResponse>(
        `/insurance/subscriptions/${id}/renew`,
        undefined,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تجديد الاشتراك");
    }
  },

  /**
   * تقديم مطالبة تأمين
   * POST /insurance/claims
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  submitClaim: async (
    data: InsuranceClaimCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<InsuranceClaimResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<InsuranceClaimResponse>(
        "/insurance/claims",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تقديم المطالبة");
    }
  },

  /**
   * جلب مطالباتي
   * GET /insurance/claims/me
   * تدعم X-Tenant-ID
   */
  getMyClaims: async (
    params?: { status?: ClaimStatus | null },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<InsuranceClaimResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<InsuranceClaimResponse[]>("/insurance/claims/me", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب مطالباتي");
    }
  },

  /**
   * مراجعة مطالبة تأمين (للمشرفين)
   * PUT /insurance/claims/{claim_id}/review
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  reviewClaim: async (
    claimId: number,
    params: {
      approve: boolean;
      approved_amount?: number | string | null;
      notes?: string | null;
    },
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<InsuranceClaimResponse> => {
    try {
      const id = Number(claimId);
      if (isNaN(id)) throw new Error("معرف المطالبة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.put<InsuranceClaimResponse>(
        `/insurance/claims/${id}/review`,
        undefined,
        { params, headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل مراجعة المطالبة");
    }
  },

  /**
   * إنشاء سجل معاش جديد
   * POST /insurance/pensions
   * تدعم X-Tenant-ID
   */
  createPension: async (data: PensionRecordCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<PensionRecordResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<PensionRecordResponse>("/insurance/pensions", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء سجل المعاش");
    }
  },

  /**
   * جلب معاشاتي
   * GET /insurance/pensions/me
   * تدعم X-Tenant-ID
   */
  getMyPensions: async (headers?: { 'X-Tenant-ID'?: number }): Promise<PensionRecordResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<PensionRecordResponse[]>("/insurance/pensions/me", {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب معاشاتي");
    }
  },

  /**
   * إنشاء ملف تأمين موظف جديد
   * POST /insurance/employee-profiles
   * تدعم X-Tenant-ID
   */
  createEmployeeProfile: async (
    data: EmployeeInsuranceProfileCreate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<EmployeeInsuranceProfileResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<EmployeeInsuranceProfileResponse>(
        "/insurance/employee-profiles",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء ملف الموظف");
    }
  },

  /**
   * جلب ملف التأمين الخاص بي كموظف
   * GET /insurance/employee-profiles/me
   * تدعم X-Tenant-ID
   */
  getMyEmployeeProfile: async (headers?: { 'X-Tenant-ID'?: number }): Promise<EmployeeInsuranceProfileResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<EmployeeInsuranceProfileResponse>(
        "/insurance/employee-profiles/me",
        { headers: reqHeaders, withCredentials: true }
      );
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب ملف الموظف");
    }
  },

  /**
   * صرف المعاشات (للمشرفين)
   * POST /insurance/admin/disburse-pensions
   * تدعم X-Tenant-ID
   */
  disbursePensions: async (headers?: { 'X-Tenant-ID'?: number }): Promise<void> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      await apiClient.post("/insurance/admin/disburse-pensions", undefined, {
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل صرف المعاشات");
    }
  },
};