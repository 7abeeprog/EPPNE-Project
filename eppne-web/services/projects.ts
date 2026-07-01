// services/projects.ts
import api from '@/lib/axios';
import type {
  Project,
  ProjectMilestone,
  Contribution,
  ProjectUpdate,
  ProjectAnalytics,
  ProjectFormData,
  ProjectStatus,
  ProjectType,
  ContributionType,
} from '@/types/projects';

// ========== Projects CRUD ==========
export const getProjects = (params?: {
  project_type?: ProjectType;
  status?: ProjectStatus;
  country?: string;
  skip?: number;
  limit?: number;
}) => api.get<Project[]>('/projects', { params });

export const getProject = (projectId: number) =>
  api.get<Project>(`/projects/${projectId}`);

export const createProject = (data: ProjectFormData) =>
  api.post<Project>('/projects', data);

export const updateProject = (projectId: number, data: Partial<ProjectFormData>) =>
  api.put<Project>(`/projects/${projectId}`, data);

export const publishProject = (projectId: number) =>
  api.post<Project>(`/projects/${projectId}/publish`);

// ========== Milestones ==========
export const addMilestone = (
  projectId: number,
  data: { title: string; target_date: string; funds_to_release?: number }
) => api.post<ProjectMilestone>(`/projects/${projectId}/milestones`, data);

export const getProjectMilestones = (projectId: number) =>
  api.get<ProjectMilestone[]>(`/projects/${projectId}/milestones`);

export const completeMilestone = (
  milestoneId: number,
  data: { actual_date: string; completion_notes?: string }
) => api.post<ProjectMilestone>(`/projects/milestones/${milestoneId}/complete`, data);

export const releaseMilestoneFunds = (milestoneId: number) =>
  api.post(`/projects/milestones/${milestoneId}/release-funds`);

// ========== Contributions ==========
export const addContribution = (
  data: {
    project_id: number;
    contribution_type: ContributionType;
    amount_mrusdt?: number;
    // in-kind fields
    land_area_sqm?: number;
    land_address?: string;
    labor_hours?: number;
    labor_description?: string;
    consulting_hours?: number;
    consulting_expertise?: string;
    equipment_description?: string;
    equipment_estimated_value?: number;
  },
  idempotencyKey?: string
) =>
  api.post<Contribution>('/projects/contributions', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const approveContribution = (
  contributionId: number,
  data: { approved: boolean; notes?: string }
) => api.post<Contribution>(`/projects/contributions/${contributionId}/approve`, data);

// ========== Updates ==========
export const addProjectUpdate = (
  projectId: number,
  data: { title: string; content: string; media_urls?: string[] }
) => api.post<ProjectUpdate>(`/projects/${projectId}/updates`, data);

export const getProjectUpdates = (projectId: number, params?: { skip?: number; limit?: number }) =>
  api.get<ProjectUpdate[]>(`/projects/${projectId}/updates`, { params });

// ========== Follow ==========
export const followProject = (projectId: number) =>
  api.post(`/projects/${projectId}/follow`);

export const unfollowProject = (projectId: number) =>
  api.delete(`/projects/${projectId}/follow`);

// ========== Analytics ==========
export const getProjectAnalytics = (projectId: number) =>
  api.get<ProjectAnalytics>(`/projects/${projectId}/analytics`);