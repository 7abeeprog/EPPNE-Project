// types/command.ts
export type UserRole = 'SUPER_ADMIN' | 'BRAND_ADMIN' | 'OPERATOR' | 'VIEWER';
export type AlertSeverity = 'INFO' | 'WARNING' | 'CRITICAL' | 'SUCCESS';
export type MetricPeriod = 'DAILY' | 'WEEKLY' | 'MONTHLY' | 'YEARLY';

export interface DashboardMetric {
  id: string;
  label: string;
  value: number;
  previousValue: number;
  change: number;
  trend: 'up' | 'down' | 'stable';
  icon: string;
  color: string;
}

export interface Brand {
  id: number;
  tenant_id: number;
  name: string;
  logo_url?: string;
  primary_color: string;
  secondary_color: string;
  is_active: boolean;
  subscription_plan: string;
  subscription_expiry?: string;
  admin_user_id: number;
  admin_name?: string;
  created_at: string;
  stats?: BrandStats;
}

export interface BrandStats {
  total_users: number;
  active_users: number;
  total_revenue: number;
  total_transactions: number;
  total_projects: number;
  total_orders: number;
}

export interface SystemAlert {
  id: number;
  tenant_id?: number;
  severity: AlertSeverity;
  title: string;
  description: string;
  source: string; // القطاع المصدر
  is_resolved: boolean;
  created_at: string;
  resolved_at?: string;
}

export interface UserSession {
  id: number;
  user_id: number;
  user_name: string;
  user_email: string;
  tenant_id: number;
  ip_address: string;
  user_agent: string;
  last_activity: string;
  is_active: boolean;
  created_at: string;
}

export interface PlatformMetric {
  id: number;
  metric_name: string;
  metric_value: number;
  period: MetricPeriod;
  recorded_at: string;
}

export interface CommandStats {
  total_users: number;
  total_tenants: number;
  total_revenue: number;
  total_transactions: number;
  active_sessions: number;
  pending_alerts: number;
  system_health: number; // 0-100
  uptime_percentage: number;
}

// ========== UI Types ==========
export interface BrandFormData {
  name: string;
  primary_color: string;
  secondary_color: string;
  subscription_plan: string;
  admin_user_id: number;
  logo_file?: File;
}

export interface CommandFilter {
  tenant_id?: number;
  severity?: AlertSeverity;
  date_from?: string;
  date_to?: string;
}