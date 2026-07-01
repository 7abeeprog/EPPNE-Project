// types/ai-agents.ts
export type AgentRole =
  | 'CEO'
  | 'SWARM_ORCHESTRATOR'
  | 'CLIMATE_BROKER'
  | 'ARBITRATOR'
  | 'SURVIVAL_CRISIS'
  | 'PHILANTHROPY'
  | 'SALES_NEGOTIATOR'
  | 'DEVOPS_ARCHITECT'
  | 'IOT_CONTROLLER'
  | 'HEALTH_BIO'
  | 'ACCESSIBILITY'
  | 'EDUCATOR'
  | 'DIGITAL_TWIN'
  | 'SUPPORT';

export type AgentStatus = 'IDLE' | 'ACTIVE' | 'LEARNING' | 'SUSPENDED';
export type ApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED';

export const AGENT_ROLE_LABELS: Record<AgentRole, { label: string; icon: string; description: string }> = {
  CEO: { label: 'مدير تنفيذي', icon: '👔', description: 'اتخاذ قرارات استراتيجية عليا' },
  SWARM_ORCHESTRATOR: { label: 'منسق سرب', icon: '🐝', description: 'تنسيق مجموعة من الوكلاء' },
  CLIMATE_BROKER: { label: 'وسيط مناخي', icon: '🌍', description: 'تحليل وإدارة البصمة الكربونية' },
  ARBITRATOR: { label: 'محكم', icon: '⚖️', description: 'حل النزاعات الرقمية' },
  SURVIVAL_CRISIS: { label: 'إدارة الأزمات', icon: '🆘', description: 'استجابة للطوارئ والأزمات' },
  PHILANTHROPY: { label: 'أعمال خيرية', icon: '🤝', description: 'إدارة التبرعات والمبادرات الخيرية' },
  SALES_NEGOTIATOR: { label: 'مفاوض مبيعات', icon: '💼', description: 'التفاوض وإتمام الصفقات' },
  DEVOPS_ARCHITECT: { label: 'مهندس DevOps', icon: '⚙️', description: 'إدارة البنية التحتية والنشر' },
  IOT_CONTROLLER: { label: 'التحكم في IoT', icon: '📡', description: 'إدارة أجهزة إنترنت الأشياء' },
  HEALTH_BIO: { label: 'صحي حيوي', icon: '💊', description: 'تحليل البيانات الصحية' },
  ACCESSIBILITY: { label: 'إتاحة', icon: '♿', description: 'ضمان إتاحة المنصة للجميع' },
  EDUCATOR: { label: 'معلم', icon: '📚', description: 'إنشاء وإدارة المحتوى التعليمي' },
  DIGITAL_TWIN: { label: 'توأم رقمي', icon: '🔄', description: 'محاكاة السيناريوهات' },
  SUPPORT: { label: 'دعم فني', icon: '🎧', description: 'الدعم والمساندة' },
};

export const AGENT_STATUS_CONFIG: Record<AgentStatus, { label: string; color: string; glow: string }> = {
  IDLE: { label: 'خامل', color: 'text-gray-400 border-gray-400/30', glow: '' },
  ACTIVE: { label: 'نشط', color: 'text-emerald-400 border-emerald-400/30', glow: 'shadow-[0_0_30px_rgba(52,211,153,0.3)]' },
  LEARNING: { label: 'قيد التعلم', color: 'text-amber-400 border-amber-400/30', glow: 'shadow-[0_0_30px_rgba(245,158,11,0.2)]' },
  SUSPENDED: { label: 'موقف', color: 'text-red-400 border-red-400/30', glow: '' },
};

// ============================================================
// الواجهات الأساسية
// ============================================================

export interface AIAgent {
  id: number;
  tenant_id: number;
  owner_id: number;
  name: string;
  role: AgentRole;
  status: AgentStatus;
  system_prompt: string;
  base_model: string;
  can_execute_payments: boolean;
  can_sign_contracts: boolean;
  requires_human_approval: boolean;
  interaction_cost_mrusdt: number;
  agent_wallet_address?: string;
  created_at: string;
  updated_at: string;
}

export interface AgentApproval {
  id: number;
  agent_id: number;
  human_approver_id: number;
  action_type: string;
  proposed_payload: Record<string, any>;
  status: ApprovalStatus;
  human_feedback?: string;
  created_at: string;
  resolved_at?: string;
}

export interface AITaskLog {
  id: number;
  agent_id?: number;
  user_id?: number;
  task_type: string;
  prompt_tokens: number;
  completion_tokens: number;
  cost_mrusdt: number;
  payment_tx_hash?: string;
  created_at: string;
}

// ============================================================
// واجهات نماذج البيانات (Forms)
// ============================================================

export interface AgentFormData {
  name: string;
  role: AgentRole;
  system_prompt: string;
  base_model: string;
  can_execute_payments: boolean;
  can_sign_contracts: boolean;
  requires_human_approval: boolean;
  interaction_cost_mrusdt: number;
}

// ============================================================
// 🔥 الواجهات الجديدة (طلبات الموافقات)
// ============================================================

export interface ApprovalRequest {
  id: number;
  agent_id: number;
  agent_name?: string; // للعرض في واجهة المستخدم
  human_approver_id: number;
  action_type: 'TRANSFER_FUNDS' | 'SIGN_CONTRACT' | 'SHUTDOWN_FACTORY' | 'DEPLOY_CODE';
  proposed_payload: Record<string, any>;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED';
  human_feedback?: string;
  created_at: string;
  resolved_at?: string;
}

export interface ApprovalResolution {
  status: 'APPROVED' | 'REJECTED' | 'CANCELLED';
  human_feedback?: string;
}

// ============================================================
// واجهات التحليلات والإحصائيات
// ============================================================

export interface AgentAnalytics {
  total_cost_mrusdt: number;
  total_tasks: number;
  tasks_by_type: Record<string, number>;
  days: number;
}

export interface AgentStatusResponse {
  id: number;
  name: string;
  role: AgentRole;
  status: AgentStatus;
  requires_human_approval: boolean;
  can_execute_payments: boolean;
  can_sign_contracts: boolean;
  interaction_cost_mrusdt: number;
}

// ============================================================
// حالة واجهة المستخدم (UI State)
// ============================================================

export interface ApprovalUI {
  pendingApprovalsCount: number;
  selectedApproval: ApprovalRequest | null;
}

// ============================================================
// دوال مساعدة (Utility Types)
// ============================================================

export interface AgentExecutionResult {
  status: 'EXECUTED' | 'PENDING_APPROVAL' | 'FAILED';
  result?: Record<string, any>;
  task_log_id?: number;
  approval_id?: number;
  message?: string;
}