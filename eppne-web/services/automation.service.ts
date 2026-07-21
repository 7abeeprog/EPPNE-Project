// services/automation.service.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";

type WorkflowCreate = components['schemas']['WorkflowCreate'];
type WorkflowResponse = components['schemas']['WorkflowResponse'];
type WorkflowUpdate = components['schemas']['WorkflowUpdate'];
type ExecutionTrigger = components['schemas']['ExecutionTrigger'];
type ExecutionResponse = components['schemas']['ExecutionResponse'];
type NodeLogResponse = components['schemas']['NodeLogResponse'];
type SecretCreate = components['schemas']['SecretCreate'];
type SecretResponse = components['schemas']['SecretResponse'];

export const AutomationService = {
  // ==========================================
  // 1. إدارة سير العمل (Workflows)
  // ==========================================

  /**
   * جلب قائمة سير العمل الخاصة بالمستأجر الحالي
   * GET /automation/workflows
   * تدعم X-Tenant-ID
   */
  listWorkflows: async (
    params?: {
      skip?: number;
      limit?: number;
      include_inactive?: boolean;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<WorkflowResponse[]> => {
    try {
      const { data } = await apiClient.get<WorkflowResponse[]>("/automation/workflows", {
        params,
        headers,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب قائمة سير العمل");
    }
  },

  /**
   * جلب تفاصيل سير عمل معين
   * GET /automation/workflows/{workflow_id}
   */
  getWorkflow: async (workflowId: number): Promise<WorkflowResponse> => {
    try {
      const id = Number(workflowId);
      if (isNaN(id)) throw new Error("معرف سير العمل غير صحيح");
      const { data } = await apiClient.get<WorkflowResponse>(`/automation/workflows/${id}`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل سير العمل");
    }
  },

  /**
   * إنشاء سير عمل جديد
   * POST /automation/workflows
   * تدعم X-Tenant-ID
   */
  createWorkflow: async (data: WorkflowCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<WorkflowResponse> => {
    try {
      const { data: result } = await apiClient.post<WorkflowResponse>("/automation/workflows", data, {
        headers,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء سير العمل");
    }
  },

  /**
   * تحديث سير عمل (الاسم، العقد، الإعدادات)
   * PUT /automation/workflows/{workflow_id}
   */
  updateWorkflow: async (workflowId: number, data: WorkflowUpdate): Promise<WorkflowResponse> => {
    try {
      const id = Number(workflowId);
      if (isNaN(id)) throw new Error("معرف سير العمل غير صحيح");
      const { data: result } = await apiClient.put<WorkflowResponse>(`/automation/workflows/${id}`, data, {
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث سير العمل");
    }
  },

  /**
   * حذف سير عمل (حذف منطقي أو دائم)
   * DELETE /automation/workflows/{workflow_id}
   */
  deleteWorkflow: async (workflowId: number, soft: boolean = true): Promise<void> => {
    try {
      const id = Number(workflowId);
      if (isNaN(id)) throw new Error("معرف سير العمل غير صحيح");
      await apiClient.delete(`/automation/workflows/${id}`, {
        params: { soft },
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل حذف سير العمل");
    }
  },

  /**
   * تشغيل سير العمل يدوياً
   * POST /automation/workflows/{workflow_id}/trigger
   */
  triggerWorkflowManual: async (workflowId: number, payload?: ExecutionTrigger): Promise<void> => {
    try {
      const id = Number(workflowId);
      if (isNaN(id)) throw new Error("معرف سير العمل غير صحيح");
      await apiClient.post(`/automation/workflows/${id}/trigger`, payload || { trigger_payload: {} }, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل تشغيل سير العمل");
    }
  },

  // ==========================================
  // 2. تنفيذات سير العمل (Executions)
  // ==========================================

  /**
   * جلب جميع تنفيذات سير العمل مع إمكانية التصفية
   * GET /automation/workflows/{workflow_id}/executions
   */
  getWorkflowExecutions: async (
    workflowId: number,
    params?: {
      skip?: number;
      limit?: number;
      status_filter?: string | null;
    }
  ): Promise<ExecutionResponse[]> => {
    try {
      const id = Number(workflowId);
      if (isNaN(id)) throw new Error("معرف سير العمل غير صحيح");
      const { data } = await apiClient.get<ExecutionResponse[]>(`/automation/workflows/${id}/executions`, {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تنفيذات سير العمل");
    }
  },

  /**
   * جلب تفاصيل تنفيذ معين
   * GET /automation/executions/{execution_id}
   */
  getExecution: async (executionId: number): Promise<ExecutionResponse> => {
    try {
      const id = Number(executionId);
      if (isNaN(id)) throw new Error("معرف التنفيذ غير صحيح");
      const { data } = await apiClient.get<ExecutionResponse>(`/automation/executions/${id}`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل التنفيذ");
    }
  },

  /**
   * جلب سجلات العقد لتنفيذ معين
   * GET /automation/executions/{execution_id}/logs
   */
  getExecutionLogs: async (executionId: number): Promise<NodeLogResponse[]> => {
    try {
      const id = Number(executionId);
      if (isNaN(id)) throw new Error("معرف التنفيذ غير صحيح");
      const { data } = await apiClient.get<NodeLogResponse[]>(`/automation/executions/${id}/logs`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب سجلات التنفيذ");
    }
  },

  // ==========================================
  // 3. الأسرار (Secrets)
  // ==========================================

  /**
   * قائمة الأسرار (بدون الكشف عن القيم)
   * GET /automation/secrets
   * تدعم X-Tenant-ID
   */
  listSecrets: async (headers?: { 'X-Tenant-ID'?: number }): Promise<SecretResponse[]> => {
    try {
      const { data } = await apiClient.get<SecretResponse[]>("/automation/secrets", {
        headers,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الأسرار");
    }
  },

  /**
   * تخزين سر (مثل API key) مشفر داخل قاعدة البيانات
   * POST /automation/secrets
   * تدعم X-Tenant-ID
   */
  createSecret: async (data: SecretCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<SecretResponse> => {
    try {
      const { data: result } = await apiClient.post<SecretResponse>("/automation/secrets", data, {
        headers,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء السر");
    }
  },

  /**
   * حذف سر
   * DELETE /automation/secrets/{secret_name}
   * تدعم X-Tenant-ID
   */
  deleteSecret: async (secretName: string, headers?: { 'X-Tenant-ID'?: number }): Promise<void> => {
    try {
      await apiClient.delete(`/automation/secrets/${secretName}`, {
        headers,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل حذف السر");
    }
  },

  // ==========================================
  // 4. الدوال الإضافية المطابقة لـ OpenAPI
  // ==========================================

  /**
   * جلب قائمة الوكلاء المتاحين للمستخدم الحالي
   * GET /automation/ai-agents
   * تدعم X-Tenant-ID
   */
  listAvailableAgents: async (headers?: { 'X-Tenant-ID'?: number }): Promise<
    { id: number; name: string; role: string; can_execute_payments: boolean; can_sign_contracts: boolean }[]
  > => {
    try {
      const { data } = await apiClient.get<
        { id: number; name: string; role: string; can_execute_payments: boolean; can_sign_contracts: boolean }[]
      >("/automation/ai-agents", {
        headers,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الوكلاء المتاحين");
    }
  },

  /**
   * نقطة نهاية Webhook لتشغيل سير العمل
   * POST /automation/webhook/{path}
   * @param path - المسار المُحدد عند إنشاء سير العمل
   * @param payload - حمولة الطلب (أي كائن JSON)
   * @param idempotencyKey - مفتاح تفادي التكرار (اختياري)
   */
  triggerWebhook: async (
    path: string,
    payload: Record<string, unknown>,
    idempotencyKey?: string
  ): Promise<void> => {
    try {
      const headers: Record<string, string> = {};
      if (idempotencyKey) {
        headers["Idempotency-Key"] = idempotencyKey;
      }
      await apiClient.post(`/automation/webhook/${path}`, payload, {
        headers,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل تنفيذ Webhook");
    }
  },
};