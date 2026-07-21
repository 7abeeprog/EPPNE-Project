// services/command.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";

type DashboardResponse = components['schemas']['DashboardResponse'];
type BrandSettingsCreate = components['schemas']['BrandSettingsCreate'];
type BrandSettingsResponse = components['schemas']['BrandSettingsResponse'];
type BrandSettingsUpdate = components['schemas']['BrandSettingsUpdate'];
type SystemAlertCreate = components['schemas']['SystemAlertCreate'];
type SystemAlertResponse = components['schemas']['SystemAlertResponse'];
type AlertStatus = components['schemas']['AlertStatus'];
type AlertSeverity = components['schemas']['AlertSeverity'];
type CommandReportCreate = components['schemas']['CommandReportCreate'];
type CommandReportResponse = components['schemas']['CommandReportResponse'];
type ReportType = components['schemas']['ReportType'];
type AIRecommendationResponse = components['schemas']['AIRecommendationResponse'];
type PlatformMetricCreate = components['schemas']['PlatformMetricCreate'];
type PlatformMetricResponse = components['schemas']['PlatformMetricResponse'];

export const CommandService = {
  // ==========================================
  // 1. لوحة التحكم (Dashboard)
  // ==========================================
  /**
   * جلب لوحة التحكم
   * GET /command/command/dashboard
   * تدعم X-Tenant-ID
   */
  getDashboard: async (headers?: { 'X-Tenant-ID'?: number }): Promise<DashboardResponse> => {
    try {
      const { data } = await apiClient.get<DashboardResponse>("/command/command/dashboard", {
        headers,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب لوحة التحكم");
    }
  },

  // ==========================================
  // 2. العلامات التجارية (Brands)
  // ==========================================
  /**
   * إنشاء علامة تجارية جديدة
   * POST /command/command/brands
   * تدعم X-Tenant-ID
   */
  createBrand: async (data: BrandSettingsCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<BrandSettingsResponse> => {
    try {
      const { data: result } = await apiClient.post<BrandSettingsResponse>("/command/command/brands", data, {
        headers,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء العلامة التجارية");
    }
  },

  /**
   * جلب العلامة التجارية الخاصة بي
   * GET /command/command/brands/me
   * تدعم X-Tenant-ID
   */
  getMyBrand: async (headers?: { 'X-Tenant-ID'?: number }): Promise<BrandSettingsResponse> => {
    try {
      const { data } = await apiClient.get<BrandSettingsResponse>("/command/command/brands/me", {
        headers,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب العلامة التجارية");
    }
  },

  /**
   * تحديث العلامة التجارية الخاصة بي
   * PUT /command/command/brands/me
   * تدعم X-Tenant-ID
   */
  updateMyBrand: async (data: BrandSettingsUpdate, headers?: { 'X-Tenant-ID'?: number }): Promise<BrandSettingsResponse> => {
    try {
      const { data: result } = await apiClient.put<BrandSettingsResponse>("/command/command/brands/me", data, {
        headers,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث العلامة التجارية");
    }
  },

  // ==========================================
  // 3. التنبيهات (Alerts)
  // ==========================================
  /**
   * جلب قائمة التنبيهات مع التصفية
   * GET /command/command/alerts
   * تدعم X-Tenant-ID
   */
  listAlerts: async (
    params?: {
      status?: AlertStatus | null;
      severity?: AlertSeverity | null;
      limit?: number;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<SystemAlertResponse[]> => {
    try {
      const { data } = await apiClient.get<SystemAlertResponse[]>("/command/command/alerts", {
        params,
        headers,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب التنبيهات");
    }
  },

  /**
   * إنشاء تنبيه جديد
   * POST /command/command/alerts
   * تدعم X-Tenant-ID
   */
  createAlert: async (data: SystemAlertCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<SystemAlertResponse> => {
    try {
      const { data: result } = await apiClient.post<SystemAlertResponse>("/command/command/alerts", data, {
        headers,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء التنبيه");
    }
  },

  /**
   * تأكيد استلام التنبيه
   * POST /command/command/alerts/{alert_id}/acknowledge
   * تدعم X-Tenant-ID
   */
  acknowledgeAlert: async (alertId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<SystemAlertResponse> => {
    try {
      const id = Number(alertId);
      if (isNaN(id)) throw new Error("معرف التنبيه غير صحيح");
      const { data: result } = await apiClient.post<SystemAlertResponse>(
        `/command/command/alerts/${id}/acknowledge`,
        undefined,
        { headers, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تأكيد استلام التنبيه");
    }
  },

  /**
   * حل التنبيه
   * POST /command/command/alerts/{alert_id}/resolve
   * تدعم X-Tenant-ID
   */
  resolveAlert: async (alertId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<SystemAlertResponse> => {
    try {
      const id = Number(alertId);
      if (isNaN(id)) throw new Error("معرف التنبيه غير صحيح");
      const { data: result } = await apiClient.post<SystemAlertResponse>(
        `/command/command/alerts/${id}/resolve`,
        undefined,
        { headers, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل حل التنبيه");
    }
  },

  // ==========================================
  // 4. التقارير (Reports)
  // ==========================================
  /**
   * جلب قائمة التقارير مع التصفية
   * GET /command/command/reports
   * تدعم X-Tenant-ID
   */
  listReports: async (
    params?: {
      report_type?: ReportType | null;
      skip?: number;
      limit?: number;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<CommandReportResponse[]> => {
    try {
      const { data } = await apiClient.get<CommandReportResponse[]>("/command/command/reports", {
        params,
        headers,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب التقارير");
    }
  },

  /**
   * إنشاء تقرير جديد
   * POST /command/command/reports
   * تدعم X-Tenant-ID
   */
  generateReport: async (data: CommandReportCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<CommandReportResponse> => {
    try {
      const { data: result } = await apiClient.post<CommandReportResponse>("/command/command/reports", data, {
        headers,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء التقرير");
    }
  },

  // ==========================================
  // 5. التوصيات (Recommendations)
  // ==========================================
  /**
   * جلب قائمة التوصيات
   * GET /command/command/recommendations
   * تدعم X-Tenant-ID
   */
  listRecommendations: async (
    params?: {
      status?: string | null;
      limit?: number;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<AIRecommendationResponse[]> => {
    try {
      const { data } = await apiClient.get<AIRecommendationResponse[]>("/command/command/recommendations", {
        params,
        headers,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب التوصيات");
    }
  },

  /**
   * توليد توصيات جديدة
   * POST /command/command/recommendations/generate
   * تدعم X-Tenant-ID
   */
  generateRecommendations: async (headers?: { 'X-Tenant-ID'?: number }): Promise<AIRecommendationResponse[]> => {
    try {
      const { data } = await apiClient.post<AIRecommendationResponse[]>(
        "/command/command/recommendations/generate",
        undefined,
        { headers, withCredentials: true }
      );
      return data;
    } catch (error) {
      throw handleError(error, "فشل توليد التوصيات");
    }
  },

  /**
   * تطبيق توصية محددة
   * POST /command/command/recommendations/{rec_id}/apply
   * تدعم X-Tenant-ID
   */
  applyRecommendation: async (recId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<AIRecommendationResponse> => {
    try {
      const id = Number(recId);
      if (isNaN(id)) throw new Error("معرف التوصية غير صحيح");
      const { data: result } = await apiClient.post<AIRecommendationResponse>(
        `/command/command/recommendations/${id}/apply`,
        undefined,
        { headers, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تطبيق التوصية");
    }
  },

  // ==========================================
  // 6. صحة النظام (System Health)
  // ==========================================
  /**
   * جلب صحة النظام
   * GET /command/command/system/health
   * تدعم X-Tenant-ID
   */
  getSystemHealth: async (headers?: { 'X-Tenant-ID'?: number }): Promise<any> => {
    try {
      const { data } = await apiClient.get<any>("/command/command/system/health", {
        headers,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب صحة النظام");
    }
  },

  // ==========================================
  // 7. المقاييس (Metrics)
  // ==========================================
  /**
   * تسجيل مقياس جديد
   * POST /command/command/metrics
   * تدعم X-Tenant-ID
   */
  recordMetric: async (data: PlatformMetricCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<PlatformMetricResponse> => {
    try {
      const { data: result } = await apiClient.post<PlatformMetricResponse>("/command/command/metrics", data, {
        headers,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تسجيل المقياس");
    }
  },
};