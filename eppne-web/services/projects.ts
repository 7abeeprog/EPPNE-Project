// services/projects.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

export type ProjectCreate = components['schemas']['ProjectCreate'];
export type ProjectResponse = components['schemas']['ProjectResponse'];
export type ProjectUpdate = components['schemas']['ProjectUpdate'];
export type ProjectType = components['schemas']['ProjectType'];
export type ProjectStatus = components['schemas']['ProjectStatus'];
export type PaginatedResponse_ProjectResponse_ = components['schemas']['PaginatedResponse_ProjectResponse_'];
type ContributionCreate = components['schemas']['ContributionCreate'];
type ContributionApprove = components['schemas']['ContributionApprove'];
type ContributionResponse = components['schemas']['ContributionResponse'];
type MilestoneCreate = components['schemas']['MilestoneCreate'];
type MilestoneResponse = components['schemas']['MilestoneResponse'];
type MilestoneComplete = components['schemas']['MilestoneComplete'];
type FollowResponse = components['schemas']['FollowResponse'];
type ProjectUpdateCreate = components['schemas']['ProjectUpdateCreate'];
type ProjectUpdateResponse = components['schemas']['ProjectUpdateResponse'];
type ProjectAnalyticsResponse = components['schemas']['ProjectAnalyticsResponse'];

export const ProjectsService = {
  /**
   * جلب قائمة المشاريع مع التصفية
   * GET projects/
   * تدعم X-Tenant-ID
   */
  listProjects: async (
    params?: {
      project_type?: ProjectType | null;
      status?: ProjectStatus | null;
      country?: string | null;
      skip?: number;
      limit?: number;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<ProjectResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<ProjectResponse[]>("projects/", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المشاريع");
    }
  },

  /**
   * إنشاء مشروع جديد
   * POST projects/
   * تدعم X-Tenant-ID
   */
  createProject: async (data: ProjectCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<ProjectResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<ProjectResponse>("projects/", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المشروع");
    }
  },

  /**
   * تحديث مشروع
   * PUT projects/{project_id}
   * تدعم X-Tenant-ID
   */
  updateProject: async (
    projectId: number,
    data: ProjectUpdate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<ProjectResponse> => {
    try {
      const id = Number(projectId);
      if (isNaN(id)) throw new Error("معرف المشروع غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.put<ProjectResponse>(`projects/${id}`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث المشروع");
    }
  },

  /**
   * حذف مشروع (حذف منطقي افتراضيًا)
   * DELETE projects/{project_id}
   * تدعم X-Tenant-ID
   */
  deleteProject: async (projectId: number, soft: boolean = true, headers?: { 'X-Tenant-ID'?: number }): Promise<void> => {
    try {
      const id = Number(projectId);
      if (isNaN(id)) throw new Error("معرف المشروع غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      await apiClient.delete(`projects/${id}`, {
        params: { soft },
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل حذف المشروع");
    }
  },

  /**
   * نشر مشروع (جعله عامًا)
   * POST projects/{project_id}/publish
   * تدعم X-Tenant-ID
   */
  publishProject: async (projectId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<ProjectResponse> => {
    try {
      const id = Number(projectId);
      if (isNaN(id)) throw new Error("معرف المشروع غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<ProjectResponse>(`projects/${id}/publish`, undefined, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل نشر المشروع");
    }
  },

  /**
   * جلب قائمة المنتجات (من نطاق المشاريع)
   * GET projects/products
   */
  listProducts: async (params: { store_id: number; skip?: number; limit?: number }): Promise<PaginatedResponse_ProjectResponse_> => {
    try {
      const { data } = await apiClient.get<PaginatedResponse_ProjectResponse_>("projects/products", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المنتجات");
    }
  },

  /**
   * إضافة مساهمة جديدة
   * POST projects/contributions
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  addContribution: async (
    data: ContributionCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<void> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      await apiClient.post("projects/contributions", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل إضافة المساهمة");
    }
  },

  /**
   * الموافقة على مساهمة أو رفضها
   * POST projects/contributions/{contribution_id}/approve
   * تدعم X-Tenant-ID
   */
  approveContribution: async (
    contributionId: number,
    data: ContributionApprove,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<ContributionResponse> => {
    try {
      const id = Number(contributionId);
      if (isNaN(id)) throw new Error("معرف المساهمة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<ContributionResponse>(
        `projects/contributions/${id}/approve`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل مراجعة المساهمة");
    }
  },

  /**
   * جلب تفاصيل مساهمة محددة
   * GET projects/contributions/{contribution_id}
   * تدعم X-Tenant-ID
   */
  getContribution: async (contributionId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<ContributionResponse> => {
    try {
      const id = Number(contributionId);
      if (isNaN(id)) throw new Error("معرف المساهمة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<ContributionResponse>(`projects/contributions/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل المساهمة");
    }
  },

  /**
   * جلب معالم مشروع
   * GET projects/{project_id}/milestones
   * تدعم X-Tenant-ID
   */
  getMilestones: async (projectId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<MilestoneResponse[]> => {
    try {
      const id = Number(projectId);
      if (isNaN(id)) throw new Error("معرف المشروع غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<MilestoneResponse[]>(`projects/${id}/milestones`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب معالم المشروع");
    }
  },

  /**
   * إضافة معلم جديد
   * POST projects/{project_id}/milestones
   * تدعم X-Tenant-ID
   */
  addMilestone: async (
    projectId: number,
    data: MilestoneCreate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<MilestoneResponse> => {
    try {
      const id = Number(projectId);
      if (isNaN(id)) throw new Error("معرف المشروع غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<MilestoneResponse>(`projects/${id}/milestones`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إضافة المعلم");
    }
  },

  /**
   * إكمال معلم
   * POST projects/milestones/{milestone_id}/complete
   * تدعم X-Tenant-ID
   */
  completeMilestone: async (
    milestoneId: number,
    data: MilestoneComplete,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<MilestoneResponse> => {
    try {
      const id = Number(milestoneId);
      if (isNaN(id)) throw new Error("معرف المعلم غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<MilestoneResponse>(
        `projects/milestones/${id}/complete`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إكمال المعلم");
    }
  },

  /**
   * متابعة مشروع
   * POST projects/{project_id}/follow
   * تدعم X-Tenant-ID
   */
  followProject: async (projectId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<FollowResponse> => {
    try {
      const id = Number(projectId);
      if (isNaN(id)) throw new Error("معرف المشروع غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<FollowResponse>(`projects/${id}/follow`, undefined, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل متابعة المشروع");
    }
  },

  /**
   * إلغاء متابعة مشروع
   * DELETE projects/{project_id}/follow
   * تدعم X-Tenant-ID
   */
  unfollowProject: async (projectId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<void> => {
    try {
      const id = Number(projectId);
      if (isNaN(id)) throw new Error("معرف المشروع غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      await apiClient.delete(`projects/${id}/follow`, {
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل إلغاء متابعة المشروع");
    }
  },

  /**
   * جلب متابعي مشروع
   * GET projects/{project_id}/followers
   * تدعم X-Tenant-ID
   */
  getFollowers: async (projectId: number, params?: { skip?: number; limit?: number }, headers?: { 'X-Tenant-ID'?: number }): Promise<any[]> => {
    try {
      const id = Number(projectId);
      if (isNaN(id)) throw new Error("معرف المشروع غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<any[]>(`projects/${id}/followers`, {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب متابعي المشروع");
    }
  },

  /**
   * جلب تحديثات المشروع
   * GET projects/{project_id}/updates
   * تدعم X-Tenant-ID
   */
  getProjectUpdates: async (projectId: number, params?: { skip?: number; limit?: number }, headers?: { 'X-Tenant-ID'?: number }): Promise<ProjectUpdateResponse[]> => {
    try {
      const id = Number(projectId);
      if (isNaN(id)) throw new Error("معرف المشروع غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<ProjectUpdateResponse[]>(`projects/${id}/updates`, {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تحديثات المشروع");
    }
  },

  /**
   * إضافة تحديث للمشروع
   * POST projects/{project_id}/updates
   * تدعم X-Tenant-ID
   */
  addProjectUpdate: async (
    projectId: number,
    data: ProjectUpdateCreate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<ProjectUpdateResponse> => {
    try {
      const id = Number(projectId);
      if (isNaN(id)) throw new Error("معرف المشروع غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<ProjectUpdateResponse>(`projects/${id}/updates`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إضافة تحديث للمشروع");
    }
  },

  /**
   * جلب تحليلات المشروع
   * GET projects/{project_id}/analytics
   * تدعم X-Tenant-ID
   */
  getAnalytics: async (projectId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<ProjectAnalyticsResponse> => {
    try {
      const id = Number(projectId);
      if (isNaN(id)) throw new Error("معرف المشروع غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<ProjectAnalyticsResponse>(`projects/${id}/analytics`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تحليلات المشروع");
    }
  },
};