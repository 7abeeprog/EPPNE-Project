// services/zamakana.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

type ZamakanaNodeCreate = components['schemas']['ZamakanaNodeCreate'];
type ZamakanaNodeResponse = components['schemas']['ZamakanaNodeResponse'];
type ZamakanaNodeType = components['schemas']['ZamakanaNodeType'];
type ZamakanaEdgeCreate = components['schemas']['ZamakanaEdgeCreate'];
type ZamakanaEdgeResponse = components['schemas']['ZamakanaEdgeResponse'];
type PlanetaryCampaignCreate = components['schemas']['PlanetaryCampaignCreate'];
type PlanetaryCampaignResponse = components['schemas']['PlanetaryCampaignResponse'];
type TimePledgeCreate = components['schemas']['TimePledgeCreate'];
type TimePledgeResponse = components['schemas']['TimePledgeResponse'];
type TimePledgeFulfill = components['schemas']['TimePledgeFulfill'];
type FutureScenarioCreate = components['schemas']['FutureScenarioCreate'];
type FutureScenarioResponse = components['schemas']['FutureScenarioResponse'];
type HumanFeedbackCreate = components['schemas']['HumanFeedbackCreate'];
type HumanFeedbackResponse = components['schemas']['HumanFeedbackResponse'];

export const ZamakanaService = {
  /**
   * جلب قائمة العقد المعرفية حسب النوع
   * GET /zamakana/zamakana/nodes
   * تدعم X-Tenant-ID
   */
  listNodes: async (params?: { node_type?: string | null; skip?: number; limit?: number }, headers?: { 'X-Tenant-ID'?: number }): Promise<ZamakanaNodeResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<ZamakanaNodeResponse[]>("/zamakana/zamakana/nodes", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب العقد المعرفية");
    }
  },

  /**
   * إنشاء عقدة معرفية جديدة (حقبة، ابتكار، شخص، حدث)
   * POST /zamakana/zamakana/nodes
   * تدعم X-Tenant-ID
   */
  createNode: async (data: ZamakanaNodeCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<ZamakanaNodeResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<ZamakanaNodeResponse>("/zamakana/zamakana/nodes", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء العقدة المعرفية");
    }
  },

  /**
   * جلب عقدة معرفية محددة
   * GET /zamakana/zamakana/nodes/{node_id}
   * تدعم X-Tenant-ID
   */
  getNode: async (nodeId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<ZamakanaNodeResponse> => {
    try {
      const id = Number(nodeId);
      if (isNaN(id)) throw new Error("معرف العقدة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<ZamakanaNodeResponse>(`/zamakana/zamakana/nodes/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب العقدة المعرفية");
    }
  },

  /**
   * تحديث عقدة معرفية (يتطلب أن يكون المستخدم هو منشئها)
   * PUT /zamakana/zamakana/nodes/{node_id}
   * تدعم X-Tenant-ID
   */
  updateNode: async (nodeId: number, data: ZamakanaNodeCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<ZamakanaNodeResponse> => {
    try {
      const id = Number(nodeId);
      if (isNaN(id)) throw new Error("معرف العقدة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.put<ZamakanaNodeResponse>(`/zamakana/zamakana/nodes/${id}`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث العقدة المعرفية");
    }
  },

  /**
   * حذف عقدة معرفية (يتطلب أن يكون المستخدم هو منشئها)
   * DELETE /zamakana/zamakana/nodes/{node_id}
   * تدعم X-Tenant-ID
   */
  deleteNode: async (nodeId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<void> => {
    try {
      const id = Number(nodeId);
      if (isNaN(id)) throw new Error("معرف العقدة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      await apiClient.delete(`/zamakana/zamakana/nodes/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل حذف العقدة المعرفية");
    }
  },

  /**
   * ربط عقدتين (تأثير سببي أو تأثير الفراشة)
   * POST /zamakana/zamakana/edges
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  createEdge: async (
    data: ZamakanaEdgeCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<ZamakanaEdgeResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<ZamakanaEdgeResponse>("/zamakana/zamakana/edges", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الرابط المعرفي");
    }
  },

  /**
   * استرجاع شبكة المعرفة (جميع العقد والحواف) للتصور
   * GET /zamakana/zamakana/graph
   * تدعم X-Tenant-ID
   */
  getKnowledgeGraph: async (params?: { node_type?: string | null; limit?: number }, headers?: { 'X-Tenant-ID'?: number }): Promise<Record<string, any>> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<Record<string, any>>("/zamakana/zamakana/graph", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب شبكة المعرفة");
    }
  },

  /**
   * إنشاء حملة كوكبية لجمع ساعات تطوعية
   * POST /zamakana/zamakana/campaigns
   * تدعم X-Tenant-ID
   */
  createCampaign: async (data: PlanetaryCampaignCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<PlanetaryCampaignResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<PlanetaryCampaignResponse>("/zamakana/zamakana/campaigns", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الحملة الكوكبية");
    }
  },

  /**
   * قائمة الحملات الكوكبية
   * GET /zamakana/zamakana/campaigns
   * تدعم X-Tenant-ID
   */
  listCampaigns: async (params?: { status?: string | null; skip?: number; limit?: number }, headers?: { 'X-Tenant-ID'?: number }): Promise<PlanetaryCampaignResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<PlanetaryCampaignResponse[]>("/zamakana/zamakana/campaigns", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الحملات الكوكبية");
    }
  },

  /**
   * جلب حملة كوكبية محددة
   * GET /zamakana/zamakana/campaigns/{campaign_id}
   * تدعم X-Tenant-ID
   */
  getCampaign: async (campaignId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<PlanetaryCampaignResponse> => {
    try {
      const id = Number(campaignId);
      if (isNaN(id)) throw new Error("معرف الحملة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<PlanetaryCampaignResponse>(`/zamakana/zamakana/campaigns/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الحملة الكوكبية");
    }
  },

  /**
   * التعهد بساعات تطوعية لحملة معينة
   * POST /zamakana/zamakana/pledges
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  pledgeTime: async (
    data: TimePledgeCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<TimePledgeResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<TimePledgeResponse>("/zamakana/zamakana/pledges", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل التعهد بالوقت");
    }
  },

  /**
   * إثبات إنجاز الساعات المتعهد بها (رفع إثبات)
   * POST /zamakana/zamakana/pledges/{pledge_id}/fulfill
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  fulfillPledge: async (
    pledgeId: number,
    data: TimePledgeFulfill,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<TimePledgeResponse> => {
    try {
      const id = Number(pledgeId);
      if (isNaN(id)) throw new Error("معرف التعهد غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<TimePledgeResponse>(
        `/zamakana/zamakana/pledges/${id}/fulfill`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إثبات إنجاز التعهد");
    }
  },

  /**
   * قائمة التعهدات الخاصة بحملة معينة
   * GET /zamakana/zamakana/campaigns/{campaign_id}/pledges
   * تدعم X-Tenant-ID
   */
  getCampaignPledges: async (campaignId: number, params?: { status?: string | null }, headers?: { 'X-Tenant-ID'?: number }): Promise<TimePledgeResponse[]> => {
    try {
      const id = Number(campaignId);
      if (isNaN(id)) throw new Error("معرف الحملة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<TimePledgeResponse[]>(`/zamakana/zamakana/campaigns/${id}/pledges`, {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تعهدات الحملة");
    }
  },

  /**
   * إنشاء سيناريو مستقبلي جديد
   * POST /zamakana/zamakana/scenarios
   * تدعم X-Tenant-ID
   */
  createScenario: async (data: FutureScenarioCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<FutureScenarioResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<FutureScenarioResponse>("/zamakana/zamakana/scenarios", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء السيناريو المستقبلي");
    }
  },

  /**
   * قائمة السيناريوهات المستقبلية
   * GET /zamakana/zamakana/scenarios
   * تدعم X-Tenant-ID
   */
  listScenarios: async (params?: { status?: string | null; skip?: number; limit?: number }, headers?: { 'X-Tenant-ID'?: number }): Promise<FutureScenarioResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<FutureScenarioResponse[]>("/zamakana/zamakana/scenarios", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب السيناريوهات المستقبلية");
    }
  },

  /**
   * جلب سيناريو مستقبلي محدد
   * GET /zamakana/zamakana/scenarios/{scenario_id}
   * تدعم X-Tenant-ID
   */
  getScenario: async (scenarioId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<FutureScenarioResponse> => {
    try {
      const id = Number(scenarioId);
      if (isNaN(id)) throw new Error("معرف السيناريو غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<FutureScenarioResponse>(`/zamakana/zamakana/scenarios/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب السيناريو المستقبلي");
    }
  },

  /**
   * طلب تحليل الذكاء الاصطناعي للسيناريو
   * POST /zamakana/zamakana/scenarios/{scenario_id}/analyze
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  analyzeScenario: async (
    scenarioId: number,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<FutureScenarioResponse> => {
    try {
      const id = Number(scenarioId);
      if (isNaN(id)) throw new Error("معرف السيناريو غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<FutureScenarioResponse>(
        `/zamakana/zamakana/scenarios/${id}/analyze`,
        undefined,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحليل السيناريو");
    }
  },

  /**
   * إضافة مراجعة بشرية على تقرير AI للسيناريو
   * POST /zamakana/zamakana/scenarios/{scenario_id}/feedback
   * تدعم X-Tenant-ID
   */
  addFeedback: async (
    scenarioId: number,
    data: HumanFeedbackCreate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<HumanFeedbackResponse> => {
    try {
      const id = Number(scenarioId);
      if (isNaN(id)) throw new Error("معرف السيناريو غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<HumanFeedbackResponse>(
        `/zamakana/zamakana/scenarios/${id}/feedback`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إضافة المراجعة البشرية");
    }
  },

  /**
   * اعتماد السيناريو بعد المراجعة البشرية
   * POST /zamakana/zamakana/scenarios/{scenario_id}/confirm
   * تدعم X-Tenant-ID
   */
  confirmScenario: async (scenarioId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<FutureScenarioResponse> => {
    try {
      const id = Number(scenarioId);
      if (isNaN(id)) throw new Error("معرف السيناريو غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<FutureScenarioResponse>(
        `/zamakana/zamakana/scenarios/${id}/confirm`,
        undefined,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل اعتماد السيناريو");
    }
  },
};