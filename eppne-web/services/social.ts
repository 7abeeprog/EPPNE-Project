// services/social.service.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";

type PostCreate = components['schemas']['PostCreate'];
type PostResponse = components['schemas']['PostResponse'];
type SocialGroupCreate = components['schemas']['SocialGroupCreate'];
type SocialGroupResponse = components['schemas']['SocialGroupResponse'];
type SocialContractCreate = components['schemas']['SocialContractCreate'];
type SocialContractResponse = components['schemas']['SocialContractResponse'];
type AIMatchProfileCreate = components['schemas']['AIMatchProfileCreate'];
type AIMatchProfileResponse = components['schemas']['AIMatchProfileResponse'];
type ConnectionRequest = components['schemas']['ConnectionRequest'];
type ConnectionResponse = components['schemas']['ConnectionResponse'];
type UserOccasionCreate = components['schemas']['UserOccasionCreate'];
type UserOccasionResponse = components['schemas']['UserOccasionResponse'];
type DigitalGiftCreate = components['schemas']['DigitalGiftCreate'];
type DigitalGiftResponse = components['schemas']['DigitalGiftResponse'];
type PhysicalGiftCreate = components['schemas']['PhysicalGiftCreate'];
type PhysicalGiftResponse = components['schemas']['PhysicalGiftResponse'];
type GroupSubscriptionPlanCreate = components['schemas']['GroupSubscriptionPlanCreate'];
type GroupSubscriptionPlanResponse = components['schemas']['GroupSubscriptionPlanResponse'];
type GroupSubscriptionCreate = components['schemas']['GroupSubscriptionCreate'];
type GroupSubscriptionResponse = components['schemas']['GroupSubscriptionResponse'];
type ContractSignRequest = components['schemas']['app__domains__social__schemas__ContractSignRequest'];

export const SocialService = {
  // ==========================================
  // 1. المنشورات (Posts)
  // ==========================================
  /**
   * إنشاء منشور جديد
   * POST /social/social/posts
   */
  createPost: async (data: PostCreate): Promise<PostResponse> => {
    try {
      const { data: result } = await apiClient.post<PostResponse>("/social/social/posts", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المنشور");
    }
  },

  /**
   * جلب الخلاصة (Feed)
   * GET /social/social/feed
   */
  getFeed: async (params?: { skip?: number; limit?: number }): Promise<PostResponse[]> => {
    try {
      const { data } = await apiClient.get<PostResponse[]>("/social/social/feed", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الخلاصة");
    }
  },

  /**
   * الإعجاب بمنشور
   * POST /social/social/posts/{post_id}/like
   */
  likePost: async (postId: number): Promise<void> => {
    try {
      await apiClient.post(`/social/social/posts/${postId}/like`, undefined, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل الإعجاب بالمنشور");
    }
  },

  /**
   * مشاركة منشور
   * POST /social/social/posts/{post_id}/share
   */
  sharePost: async (postId: number): Promise<void> => {
    try {
      await apiClient.post(`/social/social/posts/${postId}/share`, undefined, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل مشاركة المنشور");
    }
  },

  // ==========================================
  // 2. المجموعات (Groups)
  // ==========================================
  /**
   * إنشاء مجموعة جديدة
   * POST /social/social/groups
   */
  createGroup: async (data: SocialGroupCreate): Promise<SocialGroupResponse> => {
    try {
      const { data: result } = await apiClient.post<SocialGroupResponse>("/social/social/groups", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المجموعة");
    }
  },

  /**
   * الانضمام إلى مجموعة
   * POST /social/social/groups/{group_id}/join
   */
  joinGroup: async (groupId: number): Promise<void> => {
    try {
      await apiClient.post(`/social/social/groups/${groupId}/join`, undefined, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل الانضمام إلى المجموعة");
    }
  },

  // ==========================================
  // 3. العقود الاجتماعية (Contracts)
  // ==========================================
  /**
   * إنشاء عقد اجتماعي جديد
   * POST /social/social/contracts
   */
  createContract: async (data: SocialContractCreate): Promise<SocialContractResponse> => {
    try {
      const { data: result } = await apiClient.post<SocialContractResponse>("/social/social/contracts", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء العقد");
    }
  },

  /**
   * توقيع عقد اجتماعي
   * POST /social/social/contracts/{contract_id}/sign
   */
  signContract: async (contractId: number, data: ContractSignRequest): Promise<void> => {
    try {
      await apiClient.post(`/social/social/contracts/${contractId}/sign`, data, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل توقيع العقد");
    }
  },

  // ==========================================
  // 4. التوفيق (Matchmaking)
  // ==========================================
  /**
   * إعداد ملف التوفيق
   * POST /social/social/match/profile
   */
  setupMatchProfile: async (data: AIMatchProfileCreate): Promise<AIMatchProfileResponse> => {
    try {
      const { data: result } = await apiClient.post<AIMatchProfileResponse>("/social/social/match/profile", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إعداد ملف التوفيق");
    }
  },

  /**
   * جلب اقتراحات التوفيق
   * GET /social/social/match/suggestions
   */
  getMatchSuggestions: async (params?: { limit?: number }): Promise<any[]> => {
    try {
      const { data } = await apiClient.get<any[]>("/social/social/match/suggestions", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب اقتراحات التوفيق");
    }
  },

  // ==========================================
  // 5. الاتصالات (Connections)
  // ==========================================
  /**
   * طلب اتصال
   * POST /social/social/connections/request
   */
  requestConnection: async (data: ConnectionRequest): Promise<ConnectionResponse> => {
    try {
      const { data: result } = await apiClient.post<ConnectionResponse>("/social/social/connections/request", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل طلب الاتصال");
    }
  },

  /**
   * جلب اتصالاتي
   * GET /social/social/connections
   */
  getMyConnections: async (): Promise<ConnectionResponse[]> => {
    try {
      const { data } = await apiClient.get<ConnectionResponse[]>("/social/social/connections", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الاتصالات");
    }
  },

  // ==========================================
  // 6. المناسبات (Occasions)
  // ==========================================
  /**
   * إنشاء مناسبة جديدة
   * POST /social/social/occasions
   */
  createOccasion: async (data: UserOccasionCreate): Promise<UserOccasionResponse> => {
    try {
      const { data: result } = await apiClient.post<UserOccasionResponse>("/social/social/occasions", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المناسبة");
    }
  },

  /**
   * جلب المناسبات القادمة
   * GET /social/social/occasions/upcoming
   */
  getUpcomingOccasions: async (params?: { days_ahead?: number }): Promise<UserOccasionResponse[]> => {
    try {
      const { data } = await apiClient.get<UserOccasionResponse[]>("/social/social/occasions/upcoming", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المناسبات القادمة");
    }
  },

  // ==========================================
  // 7. الهدايا (Gifts)
  // ==========================================
  /**
   * إرسال هدية رقمية
   * POST /social/social/gifts/digital
   */
  sendDigitalGift: async (data: DigitalGiftCreate): Promise<DigitalGiftResponse> => {
    try {
      const { data: result } = await apiClient.post<DigitalGiftResponse>("/social/social/gifts/digital", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إرسال الهدية الرقمية");
    }
  },

  /**
   * طلب هدية مادية
   * POST /social/social/gifts/physical
   */
  requestPhysicalGift: async (data: PhysicalGiftCreate): Promise<PhysicalGiftResponse> => {
    try {
      const { data: result } = await apiClient.post<PhysicalGiftResponse>("/social/social/gifts/physical", data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل طلب الهدية المادية");
    }
  },

  // ==========================================
  // 8. اشتراكات المجموعات (Group Subscriptions)
  // ==========================================
  /**
   * إنشاء خطة اشتراك جديدة
   * POST /social/social/groups/subscriptions/plans
   */
  createSubscriptionPlan: async (data: GroupSubscriptionPlanCreate): Promise<GroupSubscriptionPlanResponse> => {
    try {
      const { data: result } = await apiClient.post<GroupSubscriptionPlanResponse>(
        "/social/social/groups/subscriptions/plans",
        data,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء خطة الاشتراك");
    }
  },

  /**
   * اشتراك مجموعة في خطة
   * POST /social/social/groups/{group_id}/subscribe
   */
  subscribeGroup: async (groupId: number, data: GroupSubscriptionCreate): Promise<GroupSubscriptionResponse> => {
    try {
      const { data: result } = await apiClient.post<GroupSubscriptionResponse>(
        `/social/social/groups/${groupId}/subscribe`,
        data,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل اشتراك المجموعة");
    }
  },

  /**
   * جلب ميزات المجموعة
   * GET /social/social/groups/{group_id}/features
   */
  getGroupFeatures: async (groupId: number): Promise<string[]> => {
    try {
      const { data } = await apiClient.get<string[]>(`/social/social/groups/${groupId}/features`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب ميزات المجموعة");
    }
  },
};