// types/automation.ts
export type NodeType =
  | 'HTTP_REQUEST'
  | 'CONDITION'
  | 'DELAY'
  | 'TRANSFORM'
  | 'NOTIFICATION'
  | 'EMAIL'
  | 'AI_AGENT'
  | 'SQL_QUERY'
  | 'WEBHOOK_RESPONSE'
  | 'LOOP'
  | 'WEBSOCKET'
  | 'FILE_UPLOAD';

export type TriggerType = 'WEBHOOK' | 'SCHEDULE' | 'EVENT' | 'MANUAL';
export type ExecutionStatus = 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'RETRY' | 'CANCELLED';

export interface WorkflowNode {
  id: string;
  type: NodeType;
  name: string;
  position: { x: number; y: number };
  config: Record<string, any>; // مرن لأي نوع عقدة
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
}

export interface Workflow {
  id: number;
  name: string;
  description?: string;
  is_active: boolean;
  trigger_type: TriggerType;
  trigger_config: Record<string, any>;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  max_retries: number;
  retry_delay_seconds: number;
  timeout_seconds: number;
  concurrency_limit: number;
  webhook_path?: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowExecution {
  id: number;
  workflow_id: number;
  triggered_by: string;
  trigger_payload?: Record<string, any>;
  status: ExecutionStatus;
  started_at: string;
  finished_at?: string;
  current_node_id?: string;
  node_results: Record<string, any>;
  error_message?: string;
  retry_count: number;
  context: Record<string, any>;
}

export interface NodeExecutionLog {
  id: number;
  execution_id: number;
  node_id: string;
  node_type: string;
  status: string;
  input_data?: Record<string, any>;
  output_data?: Record<string, any>;
  error_message?: string;
  started_at: string;
  finished_at?: string;
}

export interface Secret {
  id: number;
  name: string;
  created_at: string;
}

// نوع مفيد لواجهة المحرر (مع بيانات React Flow)
export interface RFNode extends WorkflowNode {
  // يمكن إضافة حقول إضافية خاصة بـ React Flow مثل `selected`, `dragging`
}

export interface RFEdge extends WorkflowEdge {
  // حقول React Flow مثل `animated`, `style`
}