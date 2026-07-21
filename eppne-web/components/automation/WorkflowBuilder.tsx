// components/automation/WorkflowBuilder.tsx
'use client';

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ReactFlow, Controls, Background, useNodesState, useEdgesState, addEdge, Connection, Node, Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { createWorkflow, updateWorkflow } from '@/services/automation.service';
import { Loader2, Save, Play, X, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';
import DOMPurify from 'dompurify';

// استيراد مكونات العقد المخصصة (سننشئها لاحقاً)
// import CustomNode from './nodes/CustomNode';
// import HTTPNode from './nodes/HTTPNode';
// ...

// ===== المود الجديد: استيراد لوحة إعدادات العقدة =====
import NodeSettingsPanel from './NodeSettingsPanel';

import type { Workflow, WorkflowNode, WorkflowEdge } from '@/types/automation';

// ===== المود الجديد: تعريف أنواع العقد المدعومة في اللوحة (مصنفة حسب القطاع) =====
const NODE_TYPES_BY_CATEGORY = [
  {
    category: '🌐 عامة',
    nodes: [
      { type: 'HTTP_REQUEST', label: 'HTTP Request', icon: '🌐', color: '#3b82f6' },
      { type: 'CONDITION', label: 'Condition (if/else)', icon: '🔀', color: '#f59e0b' },
      { type: 'DELAY', label: 'Delay', icon: '⏳', color: '#8b5cf6' },
      { type: 'TRANSFORM', label: 'Transform Data', icon: '🔄', color: '#06b6d4' },
      { type: 'NOTIFICATION', label: 'Notification', icon: '🔔', color: '#ec4899' },
      { type: 'EMAIL', label: 'Send Email', icon: '✉️', color: '#14b8a6' },
      { type: 'LOOP', label: 'Loop', icon: '🔄', color: '#a855f7' },
      { type: 'WEBSOCKET', label: 'WebSocket', icon: '🔌', color: '#6366f1' },
      { type: 'FILE_UPLOAD', label: 'File Upload', icon: '📁', color: '#f97316' },
    ]
  },
  {
    category: '🪪 الهوية والصلاحيات',
    nodes: [
      { type: 'CREATE_USER', label: 'إنشاء مستخدم', icon: '👤', color: '#8b5cf6' },
      { type: 'ASSIGN_ROLE', label: 'تعيين دور', icon: '🛡️', color: '#7c3aed' },
    ]
  },
  {
    category: '🏛️ الكيانات السيادية',
    nodes: [
      { type: 'CREATE_ENTITY', label: 'إنشاء كيان', icon: '🏢', color: '#0ea5e9' },
      { type: 'VERIFY_KYB', label: 'مراجعة KYB', icon: '✅', color: '#22c55e' },
    ]
  },
  {
    category: '💰 المالية',
    nodes: [
      { type: 'CREATE_INVOICE', label: 'إنشاء فاتورة', icon: '📄', color: '#f59e0b' },
      { type: 'TRANSFER_FUNDS', label: 'تحويل أموال', icon: '💸', color: '#10b981' },
    ]
  },
  {
    category: '🛒 التجارة',
    nodes: [
      { type: 'CREATE_ORDER', label: 'إنشاء طلب', icon: '📦', color: '#ec4899' },
      { type: 'UPDATE_INVENTORY', label: 'تحديث المخزون', icon: '📊', color: '#f43f5e' },
    ]
  },
  {
    category: '🎓 الأكاديمية',
    nodes: [
      { type: 'ENROLL_COURSE', label: 'تسجيل في كورس', icon: '📚', color: '#06b6d4' },
      { type: 'ISSUE_CERTIFICATE', label: 'إصدار شهادة', icon: '🎓', color: '#8b5cf6' },
    ]
  },
  // ===== المود الجديد: قطاع الذكاء الاصطناعي =====
  {
    category: '🧠 الذكاء الاصطناعي',
    nodes: [
      { type: 'AI_AGENT', label: 'وكيل ذكاء اصطناعي', icon: '🤖', color: '#8b5cf6' },
    ]
  },
];

interface WorkflowBuilderProps {
  initialWorkflow?: Workflow;
  isNew?: boolean;
}

export default function WorkflowBuilder({ initialWorkflow, isNew }: WorkflowBuilderProps) {
  const router = useRouter();
  const queryClient = useQueryClient();

  // ========== حالة React Flow (محلية) ==========
  const [nodes, setNodes, onNodesChange] = useNodesState(
    initialWorkflow?.nodes?.map(n => ({
      id: n.id,
      type: 'default', // سنخصص لكل نوع لاحقاً
      position: n.position,
      data: { label: n.name, config: n.config, nodeType: n.type },
    })) || []
  );
  const [edges, setEdges, onEdgesChange] = useEdgesState(
    initialWorkflow?.edges?.map(e => ({
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: e.sourceHandle,
      targetHandle: e.targetHandle,
    })) || []
  );

  // ========== حالة المحرر العامة ==========
  const [workflowName, setWorkflowName] = useState(initialWorkflow?.name || '');
  const [workflowDescription, setWorkflowDescription] = useState(initialWorkflow?.description || '');
  const [triggerType, setTriggerType] = useState(initialWorkflow?.trigger_type || 'MANUAL');
  const [triggerConfig, setTriggerConfig] = useState(initialWorkflow?.trigger_config || {});
  const [maxRetries, setMaxRetries] = useState(initialWorkflow?.max_retries || 3);
  const [retryDelay, setRetryDelay] = useState(initialWorkflow?.retry_delay_seconds || 5);
  const [timeoutSeconds, setTimeoutSeconds] = useState(initialWorkflow?.timeout_seconds || 60);
  const [concurrencyLimit, setConcurrencyLimit] = useState(initialWorkflow?.concurrency_limit || 10);
  const [isSaving, setIsSaving] = useState(false);

  // ========== حالة اللوحة الجانبية (إعدادات العقدة المحددة) ==========
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const selectedNode = nodes.find(n => n.id === selectedNodeId);

  // ========== دوال معالجة العقد ==========
  const onConnect = useCallback((connection: Connection) => {
    setEdges(eds => addEdge({ ...connection, id: `edge-${Date.now()}` }, eds));
  }, [setEdges]);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  // إضافة عقدة جديدة من اللوحة
  const addNode = useCallback((type: string, label: string) => {
    const newNode: Node = {
      id: `node-${Date.now()}`,
      type: 'default',
      position: { x: Math.random() * 500 + 100, y: Math.random() * 300 + 100 },
      data: {
        label: label,
        nodeType: type,
        config: {}, // فارغ، سيملؤه المستخدم عبر اللوحة الجانبية
      },
    };
    setNodes(nds => [...nds, newNode]);
  }, [setNodes]);

  // تحديث إعدادات العقدة المحددة
  const updateNodeConfig = useCallback((key: string, value: any) => {
    if (!selectedNodeId) return;
    setNodes(nds =>
      nds.map(n =>
        n.id === selectedNodeId
          ? {
            ...n,
            data: {
              ...n.data,
              config: {
                ...n.data.config,
                [key]: value,
              },
            },
          }
          : n
      )
    );
  }, [selectedNodeId, setNodes]);

  // ===== المود الجديد: دوال محدثة للتعامل مع NodeSettingsPanel =====
  const handleNodeConfigUpdate = useCallback((nodeId: string, config: Record<string, any>) => {
    setNodes(nds =>
      nds.map(n =>
        n.id === nodeId
          ? { ...n, data: { ...n.data, config } }
          : n
      )
    );
  }, [setNodes]);

  const handleNodeLabelUpdate = useCallback((nodeId: string, label: string) => {
    setNodes(nds =>
      nds.map(n =>
        n.id === nodeId
          ? { ...n, data: { ...n.data, label } }
          : n
      )
    );
  }, [setNodes]);

  // ========== حفظ سير العمل ==========
  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name: workflowName || 'Untitled Workflow',
        description: workflowDescription,
        trigger_type: triggerType,
        trigger_config: triggerConfig,
        nodes: nodes.map(n => ({
          id: n.id,
          type: n.data.nodeType,
          name: n.data.label,
          position: n.position,
          config: n.data.config,
        })),
        edges: edges.map(e => ({
          id: e.id,
          source: e.source,
          target: e.target,
          sourceHandle: e.sourceHandle,
          targetHandle: e.targetHandle,
        })),
        max_retries: maxRetries,
        retry_delay_seconds: retryDelay,
        timeout_seconds: timeoutSeconds,
        concurrency_limit: concurrencyLimit,
      };

      if (isNew) {
        return createWorkflow(payload);
      } else {
        return updateWorkflow(initialWorkflow!.id, payload);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      router.push('/automation/workflows');
    },
  });

  const handleSave = () => {
    saveMutation.mutate();
  };

  // ========== تطبيق DOMPurify على محتوى العقد (عند العرض) ==========
  const safeConfig = useCallback((config: any) => {
    if (typeof config === 'string') return DOMPurify.sanitize(config);
    if (typeof config === 'object') {
      const sanitized: any = {};
      for (const key in config) {
        sanitized[key] = typeof config[key] === 'string' ? DOMPurify.sanitize(config[key]) : config[key];
      }
      return sanitized;
    }
    return config;
  }, []);

  // ========== العرض ==========
  return (
    <div className="flex flex-col h-screen bg-background">
      {/* الهيدر العلوي */}
      <div className="flex items-center justify-between p-4 border-b border-white/10 bg-card/30 backdrop-blur-xl">
        <div className="flex items-center gap-4 flex-1">
          <input
            type="text"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            placeholder="اسم سير العمل"
            className="bg-transparent border-0 text-xl font-bold text-foreground/90 outline-none placeholder:text-muted-foreground/40 w-64"
          />
          <input
            type="text"
            value={workflowDescription}
            onChange={(e) => setWorkflowDescription(e.target.value)}
            placeholder="وصف (اختياري)"
            className="bg-transparent border-0 text-sm text-muted-foreground/70 outline-none placeholder:text-muted-foreground/40 flex-1"
          />
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saveMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
          >
            {saveMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            حفظ
          </button>
        </div>
      </div>

      {/* المحتوى الرئيسي (المحرر + اللوحات الجانبية) */}
      <div className="flex flex-1 overflow-hidden">
        {/* ===== المود الجديد: لوحة العقد الجانبية (Node Palette) مع التصنيفات ===== */}
        <div className="w-56 p-4 border-r border-white/10 bg-card/20 backdrop-blur-sm overflow-y-auto">
          <h3 className="text-sm font-medium text-foreground/80 mb-3">🧩 العقد</h3>
          {NODE_TYPES_BY_CATEGORY.map((category) => (
            <div key={category.category} className="mb-4">
              <p className="text-xs text-muted-foreground/50 mb-1.5">{category.category}</p>
              <div className="space-y-1.5">
                {category.nodes.map((nt) => (
                  <button
                    key={nt.type}
                    onClick={() => addNode(nt.type, nt.label)}
                    className="flex items-center gap-2 w-full p-2 rounded-xl bg-white/5 hover:bg-white/10 transition-colors text-sm text-foreground/80 border border-white/5 hover:border-primary/20"
                  >
                    <span>{nt.icon}</span>
                    <span className="flex-1 text-right">{nt.label}</span>
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: nt.color }} />
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* منطقة React Flow */}
        <div className="flex-1 relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            fitView
          >
            <Background gap={16} color="rgba(255,255,255,0.05)" />
            <Controls />
          </ReactFlow>
        </div>

        {/* ===== المود الجديد: اللوحة الجانبية باستخدام NodeSettingsPanel ===== */}
        <div className={cn(
          "border-l border-white/10 bg-card/30 backdrop-blur-xl transition-all duration-300",
          selectedNodeId ? "w-80" : "w-0 overflow-hidden"
        )}>
          <NodeSettingsPanel
            node={selectedNode}
            onUpdate={handleNodeConfigUpdate}
            onUpdateLabel={handleNodeLabelUpdate}
            onClose={() => setSelectedNodeId(null)}
          />
        </div>
      </div>

      {/* شريط إعدادات سير العمل السفلي (اختياري) – يمكن وضعه في مكان آخر */}
      <div className="border-t border-white/10 bg-card/20 backdrop-blur-sm p-3 flex items-center gap-6 text-xs text-muted-foreground/60">
        <span>المشغل: {triggerType}</span>
        <span>الحد الأقصى للتكرار: {maxRetries}</span>
        <span>تأخير إعادة المحاولة: {retryDelay}ث</span>
        <span>المهلة: {timeoutSeconds}ث</span>
        <span>حد التزامن: {concurrencyLimit}</span>
      </div>
    </div>
  );
}