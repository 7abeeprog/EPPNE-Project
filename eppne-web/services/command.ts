// services/command.ts
import api from '@/lib/axios';
import type {
  CommandStats,
  DashboardMetric,
  Brand,
  BrandStats,
  SystemAlert,
  UserSession,
  PlatformMetric,
  MetricPeriod,
  AlertSeverity,
  BrandFormData,
} from '@/types/command';

// ========== Dashboard ==========
export const getCommandStats = () => api.get<CommandStats>('/command/stats');

export const getDashboardMetrics = (params?: { period?: MetricPeriod }) =>
  api.get<DashboardMetric[]>('/command/metrics', { params });

// ========== Brands ==========
export const getBrands = (params?: { is_active?: boolean; skip?: number; limit?: number }) =>
  api.get<Brand[]>('/command/brands', { params });

export const getBrand = (id: number) => api.get<Brand>(`/command/brands/${id}`);

export const getBrandStats = (id: number) => api.get<BrandStats>(`/command/brands/${id}/stats`);

export const createBrand = (data: FormData) =>
  api.post<Brand>('/command/brands', data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

export const updateBrand = (id: number, data: FormData) =>
  api.put<Brand>(`/command/brands/${id}`, data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

export const deleteBrand = (id: number) => api.delete(`/command/brands/${id}`);

// ========== Users ==========
export const getPlatformUsers = (params?: { role?: string; tenant_id?: number; skip?: number; limit?: number }) =>
  api.get<User[]>('/command/users', { params });

export const getUserSessions = (userId?: number) =>
  api.get<UserSession[]>('/command/sessions', { params: { user_id: userId } });

// ========== Alerts ==========
export const getSystemAlerts = (params?: { severity?: AlertSeverity; is_resolved?: boolean; skip?: number; limit?: number }) =>
  api.get<SystemAlert[]>('/command/alerts', { params });

export const resolveAlert = (alertId: number) =>
  api.post<SystemAlert>(`/command/alerts/${alertId}/resolve`);

export const dismissAlert = (alertId: number) =>
  api.delete(`/command/alerts/${alertId}`);

// ========== Metrics ==========
export const getPlatformMetrics = (params?: { metric_name?: string; period?: MetricPeriod; skip?: number; limit?: number }) =>
  api.get<PlatformMetric[]>('/command/metrics', { params });

// ========== Reports ==========
export const generateReport = (data: {
  report_type: string;
  date_from: string;
  date_to: string;
  tenant_id?: number;
  format?: 'PDF' | 'EXCEL';
}) => api.post('/command/reports/generate', data, { responseType: 'blob' });