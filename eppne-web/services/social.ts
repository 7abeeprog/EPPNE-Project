// services/social.ts
import api from '@/lib/axios';
import type {
  Post,
  PostComment,
  SocialGroup,
  SocialPage,
  SocialSmartContract,
  SocialEvent,
  UserOccasion,
  DigitalGift,
  PhysicalGiftRequest,
  GroupSubscriptionPlan,
  GroupSubscription,
  AIMatchProfile,
  UserConnection,
  MatchSuggestion,
  PostType,
  GroupPrivacy,
  ConnectionType,
  EventApprovalStatus,
} from '@/types/social';

// ========== Posts ==========
export const getFeed = (params?: { skip?: number; limit?: number }) =>
  api.get<Post[]>('/social/feed', { params });

export const getPost = (id: number) => api.get<Post>(`/social/posts/${id}`);

export const createPost = (data: {
  content?: string;
  post_type?: PostType;
  media_urls?: string[];
  page_id?: number;
  group_id?: number;
  share_reward_mr7?: number;
}) => api.post<Post>('/social/posts', data);

export const likePost = (postId: number, idempotencyKey?: string) =>
  api.post<{ status: string; message: string }>(
    `/social/posts/${postId}/like`,
    {},
    { headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {} }
  );

export const sharePost = (postId: number) =>
  api.post<{ status: string; message: string }>(`/social/posts/${postId}/share`);

export const getPostComments = (postId: number, params?: { skip?: number; limit?: number }) =>
  api.get<PostComment[]>(`/social/posts/${postId}/comments`, { params });

export const createComment = (postId: number, data: { content: string; parent_comment_id?: number }) =>
  api.post<PostComment>(`/social/posts/${postId}/comments`, data);

// ========== Groups ==========
export const getGroups = (params?: { privacy?: GroupPrivacy; skip?: number; limit?: number }) =>
  api.get<SocialGroup[]>('/social/groups', { params });

export const getGroup = (id: number) => api.get<SocialGroup>(`/social/groups/${id}`);

export const createGroup = (data: {
  name: string;
  description?: string;
  privacy?: GroupPrivacy;
  linked_project_id?: number;
}) => api.post<SocialGroup>('/social/groups', data);

export const joinGroup = (groupId: number) => api.post(`/social/groups/${groupId}/join`);

export const leaveGroup = (groupId: number) => api.delete(`/social/groups/${groupId}/leave`);

export const getGroupMembers = (groupId: number, params?: { skip?: number; limit?: number }) =>
  api.get<{ user_id: number; role: string }[]>(`/social/groups/${groupId}/members`, { params });

// ========== Pages ==========
export const getPages = (params?: { skip?: number; limit?: number }) =>
  api.get<SocialPage[]>('/social/pages', { params });

export const getPage = (id: number) => api.get<SocialPage>(`/social/pages/${id}`);

export const createPage = (data: { name: string; slug: string; about?: string }) =>
  api.post<SocialPage>('/social/pages', data);

export const followPage = (pageId: number) => api.post(`/social/pages/${pageId}/follow`);

export const unfollowPage = (pageId: number) => api.delete(`/social/pages/${pageId}/follow`);

// ========== Contracts ==========
export const getContracts = (params?: { status?: string; skip?: number; limit?: number }) =>
  api.get<SocialSmartContract[]>('/social/contracts', { params });

export const getContract = (id: number) => api.get<SocialSmartContract>(`/social/contracts/${id}`);

export const createContract = (data: {
  template_id?: number;
  contract_type: string;
  title: string;
  terms_and_conditions: Record<string, any>;
}) => api.post<SocialSmartContract>('/social/contracts', data);

export const signContract = (contractId: number, data: { digital_signature_hash: string }, idempotencyKey?: string) =>
  api.post<{ status: string; message: string }>(
    `/social/contracts/${contractId}/sign`,
    data,
    { headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {} }
  );

// ========== Events ==========
export const getEvents = (params?: { event_type?: string; skip?: number; limit?: number }) =>
  api.get<SocialEvent[]>('/social/events', { params });

export const getEvent = (id: number) => api.get<SocialEvent>(`/social/events/${id}`);

export const createEvent = (data: {
  group_id?: number;
  page_id?: number;
  title: string;
  description?: string;
  event_type: string;
  start_time: string;
  end_time: string;
  location_details?: Record<string, any>;
  requires_approval?: boolean;
}) => api.post<SocialEvent>('/social/events', data);

export const attendEvent = (eventId: number) => api.post(`/social/events/${eventId}/attend`);

export const unattendEvent = (eventId: number) => api.delete(`/social/events/${eventId}/attend`);

// ========== Occasions ==========
export const getOccasions = () => api.get<UserOccasion[]>('/social/occasions');

export const getUpcomingOccasions = (params?: { days_ahead?: number }) =>
  api.get<UserOccasion[]>('/social/occasions/upcoming', { params });

export const createOccasion = (data: {
  occasion_type: string;
  title?: string;
  description?: string;
  occasion_date: string;
  is_public?: boolean;
  remind_days_before?: number;
}) => api.post<UserOccasion>('/social/occasions', data);

export const deleteOccasion = (id: number) => api.delete(`/social/occasions/${id}`);

// ========== Gifts ==========
export const getDigitalGifts = () => api.get<DigitalGift[]>('/social/gifts/digital');

export const getPhysicalGifts = () => api.get<PhysicalGiftRequest[]>('/social/gifts/physical');

export const sendDigitalGift = (
  data: {
    receiver_id: number;
    occasion_id?: number;
    gift_type: string;
    gift_value_mrusdt?: number;
    gift_message?: string;
    gift_metadata?: Record<string, any>;
  },
  idempotencyKey?: string
) =>
  api.post<DigitalGift>('/social/gifts/digital', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const requestPhysicalGift = (
  data: {
    receiver_id: number;
    occasion_id?: number;
    product_id?: number;
    product_name: string;
    product_price_mrusdt: number;
    shipping_address: Record<string, any>;
  },
  idempotencyKey?: string
) =>
  api.post<PhysicalGiftRequest>('/social/gifts/physical', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

// ========== Subscriptions ==========
export const getSubscriptionPlans = () => api.get<GroupSubscriptionPlan[]>('/social/groups/subscriptions/plans');

export const createSubscriptionPlan = (data: {
  name: string;
  description?: string;
  price_monthly_mrusdt: number;
  price_yearly_mrusdt: number;
  included_features: string[];
}) => api.post<GroupSubscriptionPlan>('/social/groups/subscriptions/plans', data);

export const getGroupSubscription = (groupId: number) =>
  api.get<GroupSubscription>(`/social/groups/${groupId}/subscription`);

export const subscribeGroup = (
  groupId: number,
  data: { plan_id: number; duration_months?: number },
  idempotencyKey?: string
) =>
  api.post<GroupSubscription>(`/social/groups/${groupId}/subscribe`, data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const cancelSubscription = (groupId: number) =>
  api.delete(`/social/groups/${groupId}/subscription`);

// ========== AI Matchmaking ==========
export const getMatchProfile = () => api.get<AIMatchProfile>('/social/match/profile');

export const updateMatchProfile = (data: {
  seek_type: Record<string, any>;
  ai_preferences: Record<string, any>;
  is_discoverable?: boolean;
}) => api.post<AIMatchProfile>('/social/match/profile', data);

export const getMatchSuggestions = (params?: { limit?: number }) =>
  api.get<MatchSuggestion[]>('/social/match/suggestions', { params });

// ========== Connections ==========
export const getConnections = () => api.get<UserConnection[]>('/social/connections');

export const requestConnection = (data: { target_user_id: number; connection_type: ConnectionType }) =>
  api.post<UserConnection>('/social/connections/request', data);

export const acceptConnection = (connectionId: number) =>
  api.patch<UserConnection>(`/social/connections/${connectionId}/accept`);

export const rejectConnection = (connectionId: number) =>
  api.delete(`/social/connections/${connectionId}`);