// services/invitations.ts
import api from '@/lib/axios';
import type {
  SovereignInvitation,
  Lead,
  CustomerInteraction,
  MarketingCampaign,
  SupportTicket,
  TicketComment,
  InvitationTracking,
  InvitationConversation,
  ClientInsight,
  InvitationStats,
  LeadFormData,
  CampaignFormData,
  InvitationFormData,
  TicketFormData,
  LeadStatus,
  CampaignStatus,
  InvitationStatus,
  TicketStatus,
  InteractionType,
  LeadSource,
} from '@/types/invitations';

// ========== Invitations ==========
export const getInvitations = (params?: { status?: InvitationStatus; campaign_type?: string; skip?: number; limit?: number }) =>
  api.get<SovereignInvitation[]>('/invitations', { params });

export const getInvitation = (id: number) => api.get<SovereignInvitation>(`/invitations/${id}`);

export const createInvitation = (data: InvitationFormData, idempotencyKey?: string) =>
  api.post<SovereignInvitation>('/invitations', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const updateInvitation = (id: number, data: Partial<InvitationFormData>) =>
  api.put<SovereignInvitation>(`/invitations/${id}`, data);

export const deleteInvitation = (id: number) => api.delete(`/invitations/${id}`);

export const getInvitationStats = () => api.get<InvitationStats>('/invitations/stats');

export const acceptInvitation = (invitationId: number, data: { email?: string; password?: string; name?: string; phone?: string }, idempotencyKey?: string) =>
  api.post<{ message: string; user_id: number; lead_id: number; redirect_url: string }>(
    `/invitations/${invitationId}/accept`,
    data,
    { headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {} }
  );

// ========== Leads ==========
export const getLeads = (params?: { status?: LeadStatus; source?: LeadSource; skip?: number; limit?: number }) =>
  api.get<Lead[]>('/invitations/leads', { params });

export const getLead = (id: number) => api.get<Lead>(`/invitations/leads/${id}`);

export const createLead = (data: LeadFormData, idempotencyKey?: string) =>
  api.post<Lead>('/invitations/leads', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const updateLead = (id: number, data: Partial<LeadFormData>) =>
  api.put<Lead>(`/invitations/leads/${id}`, data);

export const deleteLead = (id: number) => api.delete(`/invitations/leads/${id}`);

// ========== Interactions ==========
export const getLeadInteractions = (leadId: number, params?: { limit?: number }) =>
  api.get<CustomerInteraction[]>(`/invitations/leads/${leadId}/interactions`, { params });

export const createInteraction = (
  leadId: number,
  data: { interaction_type: InteractionType; title?: string; content: string; metadata?: Record<string, any> },
  idempotencyKey?: string
) =>
  api.post<CustomerInteraction>(`/invitations/leads/${leadId}/interactions`, data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

// ========== Campaigns ==========
export const getCampaigns = (params?: { status?: CampaignStatus; campaign_type?: string; skip?: number; limit?: number }) =>
  api.get<MarketingCampaign[]>('/invitations/campaigns', { params });

export const getCampaign = (id: number) => api.get<MarketingCampaign>(`/invitations/campaigns/${id}`);

export const createCampaign = (data: CampaignFormData, idempotencyKey?: string) =>
  api.post<MarketingCampaign>('/invitations/campaigns', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const updateCampaign = (id: number, data: Partial<CampaignFormData>) =>
  api.put<MarketingCampaign>(`/invitations/campaigns/${id}`, data);

export const deleteCampaign = (id: number) => api.delete(`/invitations/campaigns/${id}`);

// ========== Tickets ==========
export const getTickets = (params?: { status?: TicketStatus; assigned_to?: number; skip?: number; limit?: number }) =>
  api.get<SupportTicket[]>('/invitations/tickets', { params });

export const getTicket = (id: number) => api.get<SupportTicket>(`/invitations/tickets/${id}`);

export const createTicket = (data: TicketFormData, idempotencyKey?: string) =>
  api.post<SupportTicket>('/invitations/tickets', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const updateTicket = (id: number, data: Partial<TicketFormData & { status: TicketStatus }>) =>
  api.put<SupportTicket>(`/invitations/tickets/${id}`, data);

export const getTicketComments = (ticketId: number) =>
  api.get<TicketComment[]>(`/invitations/tickets/${ticketId}/comments`);

export const createTicketComment = (
  ticketId: number,
  data: { comment: string; is_internal?: boolean },
  idempotencyKey?: string
) =>
  api.post<TicketComment>(`/invitations/tickets/${ticketId}/comments`, data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

// ========== AI Chat ==========
export const chatWithAI = (
  invitationId: number,
  data: { message: string; visitor_session_id?: string },
  idempotencyKey?: string
) =>
  api.post<{ reply: string; conversation_id: number }>(
    `/invitations/${invitationId}/chat`,
    data,
    { headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {} }
  );

// ========== Tracking ==========
export const getInvitationTracking = (invitationId: number) =>
  api.get<InvitationTracking[]>(`/invitations/${invitationId}/tracking`);

export const getInvitationConversations = (invitationId: number) =>
  api.get<InvitationConversation[]>(`/invitations/${invitationId}/conversations`);

export const getClientInsight = (invitationId: number) =>
  api.get<ClientInsight>(`/invitations/${invitationId}/insight`);