// services/invitations.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

type InvitationCreate = components['schemas']['InvitationCreate'];
type InvitationResponse = components['schemas']['InvitationResponse'];
type InvitationUpdate = components['schemas']['InvitationUpdate'];
type InvitationStatus = components['schemas']['InvitationStatus'];
type CampaignType = components['schemas']['CampaignType'];
type InvitationAccept = components['schemas']['InvitationAccept'];
type InvitationAcceptResponse = components['schemas']['InvitationAcceptResponse'];
type ConversationMessage = components['schemas']['ConversationMessage'];
type ConversationResponse = components['schemas']['ConversationResponse'];
type InvitationTrackingResponse = components['schemas']['InvitationTrackingResponse'];
type ClientInsightResponse = components['schemas']['ClientInsightResponse'];
type InvitationStatsResponse = components['schemas']['InvitationStatsResponse'];
type LeadCreate = components['schemas']['LeadCreate'];
type LeadResponse = components['schemas']['LeadResponse'];
type LeadUpdate = components['schemas']['LeadUpdate'];
type LeadStatus = components['schemas']['LeadStatus'];
type LeadSource = components['schemas']['LeadSource'];
type InteractionCreate = components['schemas']['InteractionCreate'];
type InteractionResponse = components['schemas']['InteractionResponse'];
type CampaignCreate = components['schemas']['CampaignCreate'];
type CampaignResponse = components['schemas']['CampaignResponse'];
type CampaignUpdate = components['schemas']['CampaignUpdate'];
type CampaignStatus = components['schemas']['CampaignStatus'];
type TicketCreate = components['schemas']['TicketCreate'];
type TicketResponse = components['schemas']['app__domains__invitations__schemas__TicketResponse'];
type TicketUpdate = components['schemas']['TicketUpdate'];
type TicketStatus = components['schemas']['TicketStatus'];
type TicketCommentCreate = components['schemas']['TicketCommentCreate'];
type TicketCommentResponse = components['schemas']['TicketCommentResponse'];
type InvitationTrackingCreate = components['schemas']['InvitationTrackingCreate'];

export const InvitationsService = {
  /**
   * جلب قائمة الدعوات الخاصة بالمستأجر الحالي
   * GET /invitations/invitations/
   * تدعم X-Tenant-ID
   */
  listInvitations: async (
    params?: {
      status?: InvitationStatus | null;
      campaign_type?: CampaignType | null;
      skip?: number;
      limit?: number;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<InvitationResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<InvitationResponse[]>("/invitations/invitations/", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب قائمة الدعوات");
    }
  },

  /**
   * إنشاء دعوة جديدة مع تحليل الذكاء الاصطناعي للهدف
   * POST /invitations/invitations/
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  createInvitation: async (
    data: InvitationCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<InvitationResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<InvitationResponse>("/invitations/invitations/", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الدعوة");
    }
  },

  /**
   * جلب تفاصيل دعوة محددة مع تتبع الزيارة
   * GET /invitations/invitations/{invitation_id}
   * تدعم X-Tenant-ID
   */
  getInvitation: async (invitationId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<InvitationResponse> => {
    try {
      const id = Number(invitationId);
      if (isNaN(id)) throw new Error("معرف الدعوة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<InvitationResponse>(`/invitations/invitations/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل الدعوة");
    }
  },

  /**
   * تحديث دعوة موجودة (يتطلب أن يكون المستخدم هو منشئها)
   * PUT /invitations/invitations/{invitation_id}
   * تدعم X-Tenant-ID
   */
  updateInvitation: async (
    invitationId: number,
    data: InvitationUpdate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<InvitationResponse> => {
    try {
      const id = Number(invitationId);
      if (isNaN(id)) throw new Error("معرف الدعوة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.put<InvitationResponse>(`/invitations/invitations/${id}`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث الدعوة");
    }
  },

  /**
   * حذف دعوة (يتطلب أن يكون المستخدم هو منشئها)
   * DELETE /invitations/invitations/{invitation_id}
   * تدعم X-Tenant-ID
   */
  deleteInvitation: async (invitationId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<void> => {
    try {
      const id = Number(invitationId);
      if (isNaN(id)) throw new Error("معرف الدعوة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      await apiClient.delete(`/invitations/invitations/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل حذف الدعوة");
    }
  },

  /**
   * قبول الدعوة (تحويل العميل إلى Lead)
   * POST /invitations/invitations/{invitation_id}/accept
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  acceptInvitation: async (
    invitationId: number,
    data: InvitationAccept,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<InvitationAcceptResponse> => {
    try {
      const id = Number(invitationId);
      if (isNaN(id)) throw new Error("معرف الدعوة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<InvitationAcceptResponse>(
        `/invitations/invitations/${id}/accept`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل قبول الدعوة");
    }
  },

  /**
   * محادثة مع وكيل الذكاء الاصطناعي (مدعوم بـ AI Governance)
   * POST /invitations/invitations/{invitation_id}/chat
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  chatWithAI: async (
    invitationId: number,
    data: ConversationMessage,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<ConversationResponse> => {
    try {
      const id = Number(invitationId);
      if (isNaN(id)) throw new Error("معرف الدعوة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<ConversationResponse>(
        `/invitations/invitations/${id}/chat`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل الاتصال بالوكيل الذكي");
    }
  },

  /**
   * جلب بيانات تتبع سلوك المدعو
   * GET /invitations/invitations/{invitation_id}/tracking
   * تدعم X-Tenant-ID
   */
  getInvitationTracking: async (invitationId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<InvitationTrackingResponse[]> => {
    try {
      const id = Number(invitationId);
      if (isNaN(id)) throw new Error("معرف الدعوة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<InvitationTrackingResponse[]>(`/invitations/invitations/${id}/tracking`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب بيانات التتبع");
    }
  },

  /**
   * جلب محادثات العميل مع وكيل الذكاء الاصطناعي
   * GET /invitations/invitations/{invitation_id}/conversations
   * تدعم X-Tenant-ID
   */
  getInvitationConversations: async (invitationId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<ConversationResponse[]> => {
    try {
      const id = Number(invitationId);
      if (isNaN(id)) throw new Error("معرف الدعوة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<ConversationResponse[]>(`/invitations/invitations/${id}/conversations`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب محادثات العميل");
    }
  },

  /**
   * جلب تحليلات الذكاء الاصطناعي للعميل المستهدف
   * GET /invitations/invitations/{invitation_id}/insight
   * تدعم X-Tenant-ID
   */
  getClientInsight: async (invitationId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<ClientInsightResponse> => {
    try {
      const id = Number(invitationId);
      if (isNaN(id)) throw new Error("معرف الدعوة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<ClientInsightResponse>(`/invitations/invitations/${id}/insight`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تحليلات العميل");
    }
  },

  /**
   * إحصائيات الدعوات والحملات والعملاء
   * GET /invitations/invitations/stats
   * تدعم X-Tenant-ID
   */
  getInvitationStats: async (headers?: { 'X-Tenant-ID'?: number }): Promise<InvitationStatsResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<InvitationStatsResponse>("/invitations/invitations/stats", {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب إحصائيات الدعوات");
    }
  },

  /**
   * قائمة العملاء المحتملين مع التصفية حسب الحالة والمصدر
   * GET /invitations/invitations/leads
   * تدعم X-Tenant-ID
   */
  listLeads: async (
    params?: {
      status?: LeadStatus | null;
      source?: LeadSource | null;
      skip?: number;
      limit?: number;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<LeadResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<LeadResponse[]>("/invitations/invitations/leads", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب قائمة العملاء المحتملين");
    }
  },

  /**
   * إضافة عميل محتمل جديد (يدوياً أو من مصدر خارجي)
   * POST /invitations/invitations/leads
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  createLead: async (
    data: LeadCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<LeadResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<LeadResponse>("/invitations/invitations/leads", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إضافة العميل المحتمل");
    }
  },

  /**
   * جلب تفاصيل عميل محتمل مع جميع التفاعلات
   * GET /invitations/invitations/leads/{lead_id}
   * تدعم X-Tenant-ID
   */
  getLead: async (leadId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<LeadResponse> => {
    try {
      const id = Number(leadId);
      if (isNaN(id)) throw new Error("معرف العميل غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<LeadResponse>(`/invitations/invitations/leads/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل العميل");
    }
  },

  /**
   * تحديث بيانات العميل المحتمل أو حالته
   * PUT /invitations/invitations/leads/{lead_id}
   * تدعم X-Tenant-ID
   */
  updateLead: async (
    leadId: number,
    data: LeadUpdate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<LeadResponse> => {
    try {
      const id = Number(leadId);
      if (isNaN(id)) throw new Error("معرف العميل غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.put<LeadResponse>(`/invitations/invitations/leads/${id}`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث العميل");
    }
  },

  /**
   * حذف عميل محتمل (حذف منطقي)
   * DELETE /invitations/invitations/leads/{lead_id}
   * تدعم X-Tenant-ID
   */
  deleteLead: async (leadId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<void> => {
    try {
      const id = Number(leadId);
      if (isNaN(id)) throw new Error("معرف العميل غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      await apiClient.delete(`/invitations/invitations/leads/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل حذف العميل");
    }
  },

  /**
   * جلب جميع تفاعلات العميل (مرتبة تنازلياً حسب التاريخ)
   * GET /invitations/invitations/leads/{lead_id}/interactions
   * تدعم X-Tenant-ID
   */
  getLeadInteractions: async (leadId: number, params?: { limit?: number }, headers?: { 'X-Tenant-ID'?: number }): Promise<InteractionResponse[]> => {
    try {
      const id = Number(leadId);
      if (isNaN(id)) throw new Error("معرف العميل غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<InteractionResponse[]>(`/invitations/invitations/leads/${id}/interactions`, {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاعلات العميل");
    }
  },

  /**
   * تسجيل تفاعل جديد مع العميل (مكالمة، بريد، اجتماع، إلخ)
   * POST /invitations/invitations/leads/{lead_id}/interactions
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  createInteraction: async (
    leadId: number,
    data: InteractionCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<InteractionResponse> => {
    try {
      const id = Number(leadId);
      if (isNaN(id)) throw new Error("معرف العميل غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<InteractionResponse>(
        `/invitations/invitations/leads/${id}/interactions`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تسجيل التفاعل");
    }
  },

  /**
   * قائمة الحملات التسويقية مع التصفية حسب الحالة والنوع
   * GET /invitations/invitations/campaigns
   * تدعم X-Tenant-ID
   */
  listCampaigns: async (
    params?: {
      status?: CampaignStatus | null;
      campaign_type?: CampaignType | null;
      skip?: number;
      limit?: number;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<CampaignResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<CampaignResponse[]>("/invitations/invitations/campaigns", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب قائمة الحملات");
    }
  },

  /**
   * إنشاء حملة تسويقية جديدة (مع دفع الميزانية المطلوبة)
   * POST /invitations/invitations/campaigns
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  createCampaign: async (
    data: CampaignCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<CampaignResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<CampaignResponse>("/invitations/invitations/campaigns", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الحملة");
    }
  },

  /**
   * جلب تفاصيل حملة تسويقية محددة مع إحصائيات الأداء
   * GET /invitations/invitations/campaigns/{campaign_id}
   * تدعم X-Tenant-ID
   */
  getCampaign: async (campaignId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<CampaignResponse> => {
    try {
      const id = Number(campaignId);
      if (isNaN(id)) throw new Error("معرف الحملة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<CampaignResponse>(`/invitations/invitations/campaigns/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل الحملة");
    }
  },

  /**
   * تحديث حملة تسويقية (يتطلب أن يكون المستخدم هو منشئها)
   * PUT /invitations/invitations/campaigns/{campaign_id}
   * تدعم X-Tenant-ID
   */
  updateCampaign: async (
    campaignId: number,
    data: CampaignUpdate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<CampaignResponse> => {
    try {
      const id = Number(campaignId);
      if (isNaN(id)) throw new Error("معرف الحملة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.put<CampaignResponse>(`/invitations/invitations/campaigns/${id}`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث الحملة");
    }
  },

  /**
   * حذف حملة تسويقية (يتطلب أن يكون المستخدم هو منشئها)
   * DELETE /invitations/invitations/campaigns/{campaign_id}
   * تدعم X-Tenant-ID
   */
  deleteCampaign: async (campaignId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<void> => {
    try {
      const id = Number(campaignId);
      if (isNaN(id)) throw new Error("معرف الحملة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      await apiClient.delete(`/invitations/invitations/campaigns/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل حذف الحملة");
    }
  },

  /**
   * إطلاق حملة (تغيير الحالة إلى ACTIVE)
   * POST /invitations/invitations/campaigns/{campaign_id}/launch
   * تدعم X-Tenant-ID
   */
  launchCampaign: async (campaignId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<CampaignResponse> => {
    try {
      const id = Number(campaignId);
      if (isNaN(id)) throw new Error("معرف الحملة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<CampaignResponse>(
        `/invitations/invitations/campaigns/${id}/launch`,
        undefined,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إطلاق الحملة");
    }
  },

  /**
   * قائمة تذاكر الدعم مع التصفية حسب الحالة والمسؤول
   * GET /invitations/invitations/tickets
   * تدعم X-Tenant-ID
   */
  listTickets: async (
    params?: {
      status?: TicketStatus | null;
      assigned_to?: number | null;
      skip?: number;
      limit?: number;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<TicketResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<TicketResponse[]>("/invitations/invitations/tickets", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب قائمة التذاكر");
    }
  },

  /**
   * إنشاء تذكرة دعم جديدة
   * POST /invitations/invitations/tickets
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  createTicket: async (
    data: TicketCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<TicketResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<TicketResponse>("/invitations/invitations/tickets", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء التذكرة");
    }
  },

  /**
   * جلب تفاصيل تذكرة دعم مع جميع التعليقات
   * GET /invitations/invitations/tickets/{ticket_id}
   * تدعم X-Tenant-ID
   */
  getTicket: async (ticketId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<TicketResponse> => {
    try {
      const id = Number(ticketId);
      if (isNaN(id)) throw new Error("معرف التذكرة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<TicketResponse>(`/invitations/invitations/tickets/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل التذكرة");
    }
  },

  /**
   * تحديث تذكرة دعم (تغيير الحالة، الأولوية، المسؤول)
   * PUT /invitations/invitations/tickets/{ticket_id}
   * تدعم X-Tenant-ID
   */
  updateTicket: async (
    ticketId: number,
    data: TicketUpdate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<TicketResponse> => {
    try {
      const id = Number(ticketId);
      if (isNaN(id)) throw new Error("معرف التذكرة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.put<TicketResponse>(`/invitations/invitations/tickets/${id}`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث التذكرة");
    }
  },

  /**
   * جلب جميع تعليقات التذكرة
   * GET /invitations/invitations/tickets/{ticket_id}/comments
   * تدعم X-Tenant-ID
   */
  getTicketComments: async (ticketId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<TicketCommentResponse[]> => {
    try {
      const id = Number(ticketId);
      if (isNaN(id)) throw new Error("معرف التذكرة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<TicketCommentResponse[]>(`/invitations/invitations/tickets/${id}/comments`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تعليقات التذكرة");
    }
  },

  /**
   * إضافة تعليق على تذكرة (داخلي أو خارجي)
   * POST /invitations/invitations/tickets/{ticket_id}/comments
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  addTicketComment: async (
    ticketId: number,
    data: TicketCommentCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<TicketCommentResponse> => {
    try {
      const id = Number(ticketId);
      if (isNaN(id)) throw new Error("معرف التذكرة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<TicketCommentResponse>(
        `/invitations/invitations/tickets/${id}/comments`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إضافة تعليق");
    }
  },

  /**
   * تتبع سلوك الزائر على صفحة الدعوة (يُستدعى من frontend عبر AJAX)
   * POST /invitations/invitations/tracking
   * تدعم X-Tenant-ID
   */
  trackInvitation: async (data: InvitationTrackingCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<InvitationTrackingResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<InvitationTrackingResponse>(
        "/invitations/invitations/tracking",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تتبع الزيارة");
    }
  },
};