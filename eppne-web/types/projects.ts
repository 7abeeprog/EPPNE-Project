// types/projects.ts
export type ProjectType =
  | 'INDUSTRIAL'
  | 'AGRICULTURAL'
  | 'REAL_ESTATE'
  | 'EDUCATIONAL'
  | 'HEALTHCARE'
  | 'ENERGY'
  | 'TECHNOLOGY'
  | 'SOCIAL'
  | 'OTHER';

export type ProjectStatus =
  | 'DRAFT'
  | 'FUNDRAISING'
  | 'UNDER_CONSTRUCTION'
  | 'OPERATIONAL'
  | 'COMPLETED'
  | 'CANCELLED';

export type ContributionType =
  | 'MONETARY'
  | 'LAND'
  | 'FACILITY'
  | 'LABOR_HOURS'
  | 'EQUIPMENT'
  | 'CONSULTING';

export type CarbonImpactScope = 'CONSTRUCTION' | 'OPERATION' | 'FULL_LIFECYCLE';

export interface Project {
  id: number;
  owner_id: number;
  title: string;
  description: string;
  project_type: ProjectType;
  status: ProjectStatus;
  carbon_impact_scope?: CarbonImpactScope;
  country?: string;
  funding_goal_mrusdt: number;
  current_funding_mrusdt: number;
  currency: string;
  is_published: boolean;
  cover_image_url?: string;
  gallery_urls: string[];
  created_at: string;
  updated_at: string;
}

export interface ProjectMilestone {
  id: number;
  project_id: number;
  title: string;
  target_date: string;
  funds_to_release: number;
  is_completed: boolean;
  actual_date?: string;
}

export interface Contribution {
  id: number;
  project_id: number;
  contributor_id: number;
  contribution_type: ContributionType;
  equivalent_value_mrusdt: number;
  amount_mrusdt?: number;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  created_at: string;
  approved_at?: string;
}

export interface ProjectUpdate {
  id: number;
  project_id: number;
  author_id: number;
  title: string;
  content: string;
  media_urls: string[];
  created_at: string;
}

export interface ProjectAnalytics {
  project_id: number;
  total_contributors: number;
  total_monetary_contributions: number;
  total_in_kind_value: number;
  total_funding_mrusdt: number;
  funding_percentage: number;
  remaining_to_goal: number;
  milestones_completed: number;
  milestones_total: number;
  status: ProjectStatus;
  updated_at: string;
}

// ========== UI-Specific Types ==========
export interface ProjectFormData {
  title: string;
  description: string;
  project_type: ProjectType;
  country?: string;
  funding_goal_mrusdt: number;
  currency: string;
  carbon_impact_scope?: CarbonImpactScope;
  cover_image_url?: string;
  gallery_urls?: string[];
}