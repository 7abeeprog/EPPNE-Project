// types/social.ts
export type PostType = 'TEXT' | 'IMAGE' | 'VIDEO' | 'POLL' | 'DOCUMENT';
export type GroupPrivacy = 'PUBLIC' | 'PRIVATE' | 'SECRET';
export type EventApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED';
export type ConnectionType = 'FOLLOW' | 'FRIEND' | 'COLLEAGUE' | 'MENTOR';

export interface Post {
  id: number;
  tenant_id: number;
  author_id: number;
  author_name?: string;
  author_avatar?: string;
  content?: string;
  post_type: PostType;
  media_urls: string[];
  likes_count: number;
  comments_count: number;
  shares_count: number;
  share_reward_mr7: number;
  green_tag_verified: boolean;
  created_at: string;
  is_liked?: boolean;
}

export interface PostComment {
  id: number;
  post_id: number;
  author_id: number;
  author_name?: string;
  content: string;
  likes_count: number;
  parent_comment_id?: number;
  created_at: string;
}

export interface SocialGroup {
  id: number;
  tenant_id: number;
  creator_id: number;
  creator_name?: string;
  name: string;
  description?: string;
  privacy: GroupPrivacy;
  linked_project_id?: number;
  dao_contract_address?: string;
  created_at: string;
  member_count?: number;
  is_member?: boolean;
}

export interface SocialPage {
  id: number;
  tenant_id: number;
  owner_id: number;
  owner_name?: string;
  name: string;
  slug: string;
  about?: string;
  is_verified: boolean;
  page_wallet_address?: string;
  created_at: string;
  follower_count?: number;
}

export interface SocialSmartContract {
  id: number;
  creator_id: number;
  creator_name?: string;
  template_id?: number;
  contract_type: string;
  title: string;
  terms_and_conditions: Record<string, any>;
  status: 'DRAFT' | 'SIGNED' | 'EXECUTED' | 'TERMINATED';
  smart_contract_address?: string;
  blockchain_tx_hash?: string;
  created_at: string;
  signers?: ContractSignature[];
}

export interface ContractSignature {
  id: number;
  contract_id: number;
  signer_id: number;
  signer_name?: string;
  digital_signature_hash: string;
  signed_at: string;
}

export interface SocialEvent {
  id: number;
  creator_id: number;
  creator_name?: string;
  group_id?: number;
  page_id?: number;
  title: string;
  description?: string;
  event_type: string;
  start_time: string;
  end_time: string;
  location_details?: Record<string, any>;
  requires_approval: boolean;
  approval_status: EventApprovalStatus;
  approved_by_id?: number;
  is_published: boolean;
  created_at: string;
  attendee_count?: number;
  is_attending?: boolean;
}

export interface UserOccasion {
  id: number;
  user_id: number;
  occasion_type: string;
  title?: string;
  description?: string;
  occasion_date: string;
  is_public: boolean;
  remind_days_before: number;
  created_at: string;
}

export interface DigitalGift {
  id: number;
  sender_id: number;
  sender_name?: string;
  receiver_id: number;
  receiver_name?: string;
  occasion_id?: number;
  gift_type: string;
  gift_value_mrusdt: number;
  gift_message?: string;
  gift_metadata: Record<string, any>;
  sent_at: string;
  is_redeemed: boolean;
  redeemed_at?: string;
}

export interface PhysicalGiftRequest {
  id: number;
  sender_id: number;
  sender_name?: string;
  receiver_id: number;
  receiver_name?: string;
  occasion_id?: number;
  product_id?: number;
  product_name: string;
  product_description?: string;
  product_price_mrusdt: number;
  shipping_address: Record<string, any>;
  shipping_status: string;
  payment_tx_hash?: string;
  order_tracking_number?: string;
  created_at: string;
}

export interface GroupSubscriptionPlan {
  id: number;
  tenant_id: number;
  name: string;
  description?: string;
  price_monthly_mrusdt: number;
  price_yearly_mrusdt: number;
  included_features: string[];
  is_active: boolean;
  created_at: string;
}

export interface GroupSubscription {
  id: number;
  group_id: number;
  plan_id: number;
  start_date: string;
  end_date: string;
  auto_renew: boolean;
  status: string;
  payment_tx_hash?: string;
  created_at: string;
}

export interface AIMatchProfile {
  id: number;
  user_id: number;
  seek_type: Record<string, any>;
  ai_preferences: Record<string, any>;
  is_discoverable: boolean;
  created_at: string;
}

export interface UserConnection {
  id: number;
  user_a_id: number;
  user_b_id: number;
  connection_type: ConnectionType;
  match_score?: number;
  status: string;
  created_at: string;
}

export interface MatchSuggestion {
  suggested_user_id: number;
  match_score: number;
  reasoning: string;
  user_name?: string;
}

// ========== UI Types ==========
export interface SocialStats {
  total_posts: number;
  total_groups: number;
  total_connections: number;
  total_gifts_sent: number;
}