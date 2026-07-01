// types/marketplace.ts
export type ServiceType =
  | 'RIDE_HAILING'
  | 'DELIVERY'
  | 'E_COMMERCE'
  | 'TOURISM_BOOKING'
  | 'EDUCATION_PLATFORM'
  | 'JOB_MARKETPLACE'
  | 'SOCIAL_NETWORK'
  | 'HEALTHCARE_PORTAL'
  | 'REAL_ESTATE'
  | 'EVENT_MANAGEMENT'
  | 'CUSTOM';

export type DeploymentStatus = 'PENDING' | 'DEPLOYING' | 'ACTIVE' | 'FAILED' | 'SUSPENDED';
export type SubscriptionPlan = 'FREE' | 'BASIC' | 'PROFESSIONAL' | 'ENTERPRISE';

export interface MarketplaceService {
  id: number;
  tenant_id: number;
  name: string;
  description?: string;
  service_type: ServiceType;
  version: string;
  thumbnail_url?: string;
  demo_url?: string;
  documentation_url?: string;
  database_schema?: any;
  api_blueprint?: any;
  frontend_template_url?: string;
  default_config: Record<string, any>;
  requires_modules: string[];
  min_sovereign_rank?: string;
  base_price_mrusdt: number;
  subscription_price_basic_mrusdt: number;
  subscription_price_pro_mrusdt: number;
  subscription_price_enterprise_mrusdt: number;
  available_addons: number[];
  is_active: boolean;
  is_featured: boolean;
  created_by: number;
  created_at: string;
  updated_at: string;
}

export interface ServiceVersion {
  id: number;
  service_id: number;
  version: string;
  changelog?: string;
  database_schema?: any;
  api_blueprint?: any;
  frontend_template_url?: string;
  is_active: boolean;
  created_at: string;
}

export interface ServiceLicense {
  id: number;
  service_id: number;
  tenant_id: number;
  buyer_user_id: number;
  deployed_domain?: string;
  deployment_status: DeploymentStatus;
  deployment_log?: string;
  subscription_plan: SubscriptionPlan;
  purchased_addons: number[];
  custom_config: Record<string, any>;
  paid_amount_mrusdt: number;
  subscription_start?: string;
  subscription_end?: string;
  auto_renew: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ServiceAddon {
  id: number;
  tenant_id: number;
  name: string;
  description?: string;
  addon_type: string;
  version: string;
  compatible_service_types: ServiceType[];
  database_schema?: any;
  api_blueprint?: any;
  frontend_component_url?: string;
  price_mrusdt: number;
  is_active: boolean;
  created_by: number;
  created_at: string;
  updated_at: string;
}

export interface CustomizationRequest {
  id: number;
  license_id: number;
  requester_id: number;
  title: string;
  description: string;
  proposed_budget_mrusdt?: number;
  status: 'PENDING' | 'APPROVED' | 'IN_PROGRESS' | 'COMPLETED' | 'REJECTED';
  assigned_developer_id?: number;
  created_at: string;
  updated_at: string;
}

// ========== UI Types ==========
export interface ServiceWithAddons extends MarketplaceService {
  addons?: ServiceAddon[];
}

export interface PurchaseData {
  service_id: number;
  subscription_plan: SubscriptionPlan;
  purchased_addons: number[];
  custom_config: Record<string, any>;
  custom_domain?: string;
  auto_renew: boolean;
}

export interface DeploymentStatusResponse {
  status: DeploymentStatus;
  log?: string;
  domain?: string;
  subscription_end?: string;
}