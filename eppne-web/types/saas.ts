// types/saas.ts

export interface ServiceCatalog {
  id: number;
  name: string;
  code: string;
  description?: string;
  icon?: string;
  is_active: boolean;
  created_at: string;
}

export interface ServicePlan {
  id: number;
  service_id: number;
  name: string;
  code: string;
  price_monthly: number;
  price_yearly: number;
  currency: string;
  features: string[];
  max_users: number;
  max_products: number;
  max_courses: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TenantSubscription {
  id: number;
  tenant_id: number;
  plan_id: number;
  plan?: ServicePlan;
  status: 'ACTIVE' | 'TRIAL' | 'PAST_DUE' | 'EXPIRED' | 'CANCELLED';
  auto_renew: boolean;
  payment_method: string;
  grace_period_end_date?: string;
  trial_end_date?: string;
  start_date: string;
  end_date?: string;
  next_billing_date?: string;
  created_at: string;
  updated_at: string;
}

export interface Invoice {
  id: number;
  tenant_id: number;
  subscription_id: number;
  invoice_number: string;
  amount: number;
  currency: string;
  description?: string;
  items: Array<{ service: string; period: string; amount: number; currency: string }>;
  status: 'PENDING' | 'PAID' | 'FAILED' | 'CANCELLED';
  due_date?: string;
  paid_at?: string;
  paid_tx_hash?: string;
  created_at: string;
  updated_at: string;
}

export interface FeatureFlag {
  id: number;
  tenant_id: number;
  service_id: number;
  feature_key: string;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface ServiceAccessStatus {
  service_id: number;
  service_code: string;
  service_name: string;
  accessible: boolean;
  access_level: string;
  subscription_status: string;
  plan_name?: string;
  trial_end_date?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  skip: number;
  limit: number;
}

// ✅ إحصائيات لوحة التحكم
export interface SaasDashboardStats {
  total_services: number;
  active_services: number;
  total_subscriptions: number;
  active_subscriptions: number;
  pending_invoices: number;
  monthly_revenue: number;
  currency: string;
}

// ✅ طلبات وإنشاء
export interface SubscribeRequest {
  plan_id: number;
  payment_method?: string;
  auto_renew?: boolean;
}

export interface UpdateSubscriptionRequest {
  auto_renew?: boolean;
  payment_method?: string;
}

export interface CreateInvoiceRequest {
  subscription_id: number;
  amount: number;
  currency?: string;
  description?: string;
}