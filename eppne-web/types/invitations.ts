// types/invitations.ts
export type InvitationType = 'GENERAL' | 'PRIVATE';
export type InvitationTargetType = 'PERSON' | 'CIVIL_ORGANIZATION' | 'GOVERNMENT_BODY' | 'INTERNATIONAL_ORGANIZATION' | 'UNIVERSITY' | 'COMPANY';
export type InvitationStatus = 'DRAFT' | 'SENT' | 'ACCEPTED' | 'DECLINED' | 'EXPIRED';
export type CampaignType = 'BOOTCAMP' | 'COURSE' | 'SERVICE' | 'PRODUCT' | 'EVENT';
export type LeadStatus = 'NEW' | 'CONTACTED' | 'QUALIFIED' | 'CONVERTED' | 'LOST';
export type LeadSource = 'INVITATION' | 'SOCIAL_FACEBOOK' | 'SOCIAL_INSTAGRAM' | 'SOCIAL_LINKEDIN' | 'SOCIAL_TWITTER' | 'EMAIL' | 'REFERRAL' | 'WEBSITE';
export type CampaignStatus = 'DRAFT' | 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'CANCELLED';
export type InteractionType = 'EMAIL' | 'PHONE' | 'CHAT' | 'MEETING' | 'SOCIAL_MEDIA';
export type TicketStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED';

export interface SovereignInvitation {
  id: number;
  tenant_id: number;
  sender_user_id?: number | null;
  sender_entity_id?: number | null;
  invitation_type: InvitationType;
  target_type: InvitationTargetType;
  target_user_id?: number | null;
  target_entity_identifier?: string | null;
  custom_message?: string | null;
  title?: string | null;
  campaign_type: CampaignType;
  campaign_id: number;
  discount_percentage: number | string;
  gift_coins_amount: number | string;
  gift_currency: string;
  max_uses: number;
  current_uses: number;
  expires_at?: string | null;
  status: InvitationStatus;
  assigned_ai_agent_id?: number | null;
  click_count: number;
  first_clicked_at?: string | null;
  last_clicked_at?: string | null;
  created_at: string;
  updated_at: string;
  invitation_url?: string | null;
}

export interface Lead {
  id: number;
  tenant_id: number;
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  company?: string;
  position?: string;
  source: LeadSource;
  source_reference?: string;
  status: LeadStatus;
  score: number;
  social_profiles: Record<string, string>;
  notes?: string;
  assigned_to?: number;
  assigned_to_name?: string;
  converted_user_id?: number;
  converted_at?: string;
  created_at: string;
  updated_at: string;
  interactions?: CustomerInteraction[];
}

export interface CustomerInteraction {
  id: number;
  tenant_id: number;
  lead_id: number;
  user_id?: number;
  user_name?: string;
  interaction_type: InteractionType;
  title?: string;
  content: string;
  metadata: Record<string, any>;
  created_at: string;
}

export interface MarketingCampaign {
  id: number;
  tenant_id: number;
  name: string;
  description?: string | null;
  campaign_type: CampaignType;
  target_audience: Record<string, any>;
  budget_mrusdt: string;
  spent_mrusdt: string;
  start_date: string;
  end_date?: string | null;
  status: CampaignStatus;
  channels: string[];
  total_leads: number;
  converted_leads: number;
  created_by: number;
  created_at: string;
  updated_at: string;
}

export interface SupportTicket {
  id: number;
  tenant_id: number;
  lead_id?: number | null;
  user_id?: number | null;
  user_name?: string | null;
  assigned_to?: number | null;
  assigned_to_name?: string | null;
  subject: string;
  description: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
  status: TicketStatus;
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
  comments?: TicketComment[] | null;
}

export interface TicketComment {
  id: number;
  tenant_id: number;
  ticket_id: number;
  user_id: number;
  user_name?: string | null;
  comment: string;
  is_internal: boolean;
  created_at: string;
}

export interface InvitationTracking {
  id: number;
  invitation_id: number;
  ip_address?: string;
  user_agent?: string;
  device_type?: string;
  location_city?: string;
  location_country?: string;
  page_visited?: string;
  time_spent_seconds: number;
  actions: string[];
  created_at: string;
}

export interface InvitationConversation {
  id: number;
  invitation_id: number;
  visitor_session_id?: string;
  visitor_user_id?: number;
  message: string;
  is_from_ai: boolean;
  ai_agent_id?: number;
  created_at: string;
}

export interface ClientInsight {
  id: number;
  invitation_id: number;
  ai_analysis: Record<string, any>;
  recommended_discount?: number;
  recommended_message_template?: string;
  readiness_score: number;
  created_at: string;
}

// ========== UI Types ==========
export interface InvitationStats {
  total_invitations: number;
  sent_invitations: number;
  accepted_invitations: number;
  conversion_rate: number;
  total_clicks: number;
  total_leads: number;
  converted_leads: number;
  active_campaigns: number;
  open_tickets: number;
}

export interface LeadFormData {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  company?: string;
  position?: string;
  source: LeadSource;
  source_reference?: string;
  status: LeadStatus;
  notes?: string;
  assigned_to?: number;
  social_profiles?: Record<string, string>;
}

export interface CampaignFormData {
  name: string;
  description?: string;
  campaign_type: CampaignType;
  target_audience: Record<string, any>;
  budget_mrusdt: number;
  start_date: string;
  end_date?: string;
  channels: string[];
}

export interface InvitationFormData {
  invitation_type: InvitationType;
  target_type: InvitationTargetType;
  target_user_id?: number;
  target_entity_identifier?: string;
  custom_message?: string;
  title?: string;
  campaign_type: CampaignType;
  campaign_id: number;
  discount_percentage: number;
  gift_coins_amount: number;
  gift_currency: string;
  max_uses: number;
  expires_at?: string;
}

export interface TicketFormData {
  lead_id?: number;
  subject: string;
  description: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
}