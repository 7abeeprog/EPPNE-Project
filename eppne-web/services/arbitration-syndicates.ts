// services/arbitration-syndicates.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

type ArbitrationCaseCreate = components['schemas']['ArbitrationCaseCreate'];
type ArbitrationCaseResponse = components['schemas']['ArbitrationCaseResponse'];
type JuryVoteCreate = components['schemas']['JuryVoteCreate'];
type VerdictCreate = components['schemas']['VerdictCreate'];
type SyndicateCreate = components['schemas']['SyndicateCreate'];
type SyndicateResponse = components['schemas']['SyndicateResponse'];
type SyndicateMembershipResponse = components['schemas']['SyndicateMembershipResponse'];
type ProfessionalLicenseCreate = components['schemas']['ProfessionalLicenseCreate'];
type ProfessionalLicenseResponse = components['schemas']['ProfessionalLicenseResponse'];
type ElectionCreate = components['schemas']['ElectionCreate'];
type ElectionResponse = components['schemas']['ElectionResponse'];
type CandidateCreate = components['schemas']['CandidateCreate'];
type CandidateResponse = components['schemas']['CandidateResponse'];
type VoteCast = components['schemas']['VoteCast'];

export const ArbitrationSyndicatesService = {
  /**
   * جلب قائمة القضايا الخاصة بي
   * GET /arbitration/arbitration-syndicates/cases/me
   * تدعم X-Tenant-ID
   */
  getMyCases: async (headers?: { 'X-Tenant-ID'?: number }): Promise<ArbitrationCaseResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<ArbitrationCaseResponse[]>("/arbitration/arbitration-syndicates/cases/me", {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب قضاياي");
    }
  },

  /**
   * إنشاء قضية تحكيم جديدة (نزاع)
   * POST /arbitration/arbitration-syndicates/cases
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  createDispute: async (
    data: ArbitrationCaseCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<ArbitrationCaseResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<ArbitrationCaseResponse>(
        "/arbitration/arbitration-syndicates/cases",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء القضية");
    }
  },

  /**
   * التصويت كعضو في هيئة المحلفين على قضية
   * POST /arbitration/arbitration-syndicates/cases/{case_id}/jury-vote
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  castJuryVote: async (
    caseId: number,
    data: JuryVoteCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<Record<string, any>> => {
    try {
      const id = Number(caseId);
      if (isNaN(id)) throw new Error("معرف القضية غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<Record<string, any>>(
        `/arbitration/arbitration-syndicates/cases/${id}/jury-vote`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل التصويت في هيئة المحلفين");
    }
  },

  /**
   * إصدار حكم في قضية (للمحكمين أو المشرفين)
   * POST /arbitration/arbitration-syndicates/cases/{case_id}/verdict
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  issueVerdict: async (
    caseId: number,
    data: VerdictCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<void> => {
    try {
      const id = Number(caseId);
      if (isNaN(id)) throw new Error("معرف القضية غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      await apiClient.post(`/arbitration/arbitration-syndicates/cases/${id}/verdict`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل إصدار الحكم");
    }
  },

  /**
   * جلب قائمة النقابات
   * GET /arbitration/arbitration-syndicates/syndicates
   * تدعم X-Tenant-ID
   */
  listSyndicates: async (headers?: { 'X-Tenant-ID'?: number }): Promise<SyndicateResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<SyndicateResponse[]>("/arbitration/arbitration-syndicates/syndicates", {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب النقابات");
    }
  },

  /**
   * إنشاء نقابة جديدة
   * POST /arbitration/arbitration-syndicates/syndicates
   * تدعم X-Tenant-ID
   */
  createSyndicate: async (data: SyndicateCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<SyndicateResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<SyndicateResponse>(
        "/arbitration/arbitration-syndicates/syndicates",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء النقابة");
    }
  },

  /**
   * الانضمام إلى نقابة
   * POST /arbitration/arbitration-syndicates/syndicates/{syndicate_id}/join
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  joinSyndicate: async (
    syndicateId: number,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<SyndicateMembershipResponse> => {
    try {
      const id = Number(syndicateId);
      if (isNaN(id)) throw new Error("معرف النقابة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<SyndicateMembershipResponse>(
        `/arbitration/arbitration-syndicates/syndicates/${id}/join`,
        undefined,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل الانضمام إلى النقابة");
    }
  },

  /**
   * جلب تراخيصي المهنية
   * GET /arbitration/arbitration-syndicates/licenses/me
   * تدعم X-Tenant-ID
   */
  getMyLicenses: async (headers?: { 'X-Tenant-ID'?: number }): Promise<ProfessionalLicenseResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<ProfessionalLicenseResponse[]>(
        "/arbitration/arbitration-syndicates/licenses/me",
        { headers: reqHeaders, withCredentials: true }
      );
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تراخيصي");
    }
  },

  /**
   * إصدار ترخيص مهني جديد
   * POST /arbitration/arbitration-syndicates/licenses
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  issueLicense: async (
    data: ProfessionalLicenseCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<ProfessionalLicenseResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<ProfessionalLicenseResponse>(
        "/arbitration/arbitration-syndicates/licenses",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إصدار الترخيص");
    }
  },

  /**
   * إنشاء انتخابات جديدة
   * POST /arbitration/arbitration-syndicates/elections
   * تدعم X-Tenant-ID
   */
  createElection: async (data: ElectionCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<ElectionResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<ElectionResponse>(
        "/arbitration/arbitration-syndicates/elections",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الانتخابات");
    }
  },

  /**
   * ترشيح مرشح في انتخابات
   * POST /arbitration/arbitration-syndicates/elections/{election_id}/candidates
   * تدعم X-Tenant-ID
   */
  nominateCandidate: async (
    electionId: number,
    data: CandidateCreate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<CandidateResponse> => {
    try {
      const id = Number(electionId);
      if (isNaN(id)) throw new Error("معرف الانتخابات غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<CandidateResponse>(
        `/arbitration/arbitration-syndicates/elections/${id}/candidates`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل ترشيح المرشح");
    }
  },

  /**
   * التصويت في انتخابات
   * POST /arbitration/arbitration-syndicates/elections/{election_id}/vote
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  voteInElection: async (
    electionId: number,
    data: VoteCast,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<void> => {
    try {
      const id = Number(electionId);
      if (isNaN(id)) throw new Error("معرف الانتخابات غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      await apiClient.post(`/arbitration/arbitration-syndicates/elections/${id}/vote`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل التصويت في الانتخابات");
    }
  },
};