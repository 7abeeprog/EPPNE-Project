// services/automation.ts
import api from '@/lib/axios';
import type {
  Workflow,
  WorkflowExecution,
  NodeExecutionLog,
  Secret,
  WorkflowNode,
  WorkflowEdge,
  TriggerType,
} from '@/types/automation';

// ========== Workflows ==========
export const getWorkflows = (params?: { skip?: number; limit?: number; include_inactive?: boolean }) =>
  api.get<Workflow[]>('/automation/workflows', { params });

export const getWorkflow = (workflowId: number) =>
  api.get<Workflow>(`/automation/workflows/${workflowId}`);

export const createWorkflow = (data: {
  name: string;
  description?: string;
  trigger_type: TriggerType;
  trigger_config: Record<string, any>;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  max_retries?: number;
  retry_delay_seconds?: number;
  timeout_seconds?: number;
  concurrency_limit?: number;
}) => api.post<Workflow>('/automation/workflows', data);

export const updateWorkflow = (workflowId: number, data: Partial<Omit<Workflow, 'id' | 'created_at' | 'updated_at'>>) =>
  api.put<Workflow>(`/automation/workflows/${workflowId}`, data);

export const deleteWorkflow = (workflowId: number, soft: boolean = true) =>
  api.delete(`/automation/workflows/${workflowId}?soft=${soft}`);

// ===== Toggle Active Status =====
export const toggleWorkflowActive = (workflowId: number, isActive: boolean) =>
  api.patch<Workflow>(`/automation/workflows/${workflowId}`, { is_active: isActive });

// ========== Triggers ==========
export const triggerWorkflowManual = (workflowId: number, payload?: Record<string, any>) =>
  api.post(`/automation/workflows/${workflowId}/trigger`, { trigger_payload: payload || {} });

// ========== Executions ==========
export const getWorkflowExecutions = (
  workflowId: number,
  params?: { skip?: number; limit?: number; status?: string }
) => api.get<WorkflowExecution[]>(`/automation/workflows/${workflowId}/executions`, { params });

export const getExecution = (executionId: number) =>
  api.get<WorkflowExecution>(`/automation/executions/${executionId}`);

export const getExecutionLogs = (executionId: number) =>
  api.get<NodeExecutionLog[]>(`/automation/executions/${executionId}/logs`);

// ===== دوال إدارة التنفيذات المتقدمة =====
export const cancelExecution = (executionId: number) =>
  api.post<WorkflowExecution>(`/automation/executions/${executionId}/cancel`);

export const retryExecution = (executionId: number) =>
  api.post<WorkflowExecution>(`/automation/executions/${executionId}/retry`);

export const getExecutionStats = (workflowId: number) =>
  api.get<{ total: number; success: number; failed: number; running: number }>(
    `/automation/workflows/${workflowId}/executions/stats`
  );

// ========== Secrets ==========
export const getSecrets = () => api.get<Secret[]>('/automation/secrets');

export const createSecret = (data: { name: string; value: string }) =>
  api.post<Secret>('/automation/secrets', data);

export const deleteSecret = (name: string) => api.delete(`/automation/secrets/${name}`);

// ============================================================
// 🆕 جلب الوكلاء المتاحين لعقدة AI_AGENT
// ============================================================
export const getAvailableAgents = () =>
  api.get<{ id: number; name: string; role: string; can_execute_payments: boolean; can_sign_contracts: boolean }[]>(
    '/automation/ai-agents'
  );

// ========== Webhook (public) ==========
// المسار: /automation/webhook/{path}