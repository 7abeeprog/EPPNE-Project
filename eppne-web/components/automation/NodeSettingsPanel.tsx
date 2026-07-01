// components/automation/NodeSettingsPanel.tsx
import React, { useState } from 'react';
import { X, Settings, Key } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Node } from '@xyflow/react';

// استيراد مكونات إعدادات العقد المختلفة (الأنواع الأساسية)
import HTTPConfig from './node-configs/HTTPConfig';
import ConditionConfig from './node-configs/ConditionConfig';
import DelayConfig from './node-configs/DelayConfig';
import TransformConfig from './node-configs/TransformConfig';
import NotificationConfig from './node-configs/NotificationConfig';
import EmailConfig from './node-configs/EmailConfig';
import SQLConfig from './node-configs/SQLConfig';
import LoopConfig from './node-configs/LoopConfig';
import WebSocketConfig from './node-configs/WebSocketConfig';
import FileUploadConfig from './node-configs/FileUploadConfig';
import SlackConfig from './node-configs/SlackConfig';
import DatabaseConfig from './node-configs/DatabaseConfig';
import HttpResponseConfig from './node-configs/HttpResponseConfig';

// ===== المود الجديد: استيراد مكونات إعدادات القطاعات الجديدة =====
import CreateUserConfig from './node-configs/CreateUserConfig';
import CreateEntityConfig from './node-configs/CreateEntityConfig';
import CreateInvoiceConfig from './node-configs/CreateInvoiceConfig';
import CreateOrderConfig from './node-configs/CreateOrderConfig';
import EnrollCourseConfig from './node-configs/EnrollCourseConfig';
import TransferFundsConfig from './node-configs/TransferFundsConfig';

// ===== المود الجديد: استيراد مكون إعدادات AI_AGENT =====
import AIAgentConfig from './node-configs/AIAgentConfig';

// خريطة ربط أنواع العقد بمكونات الإعدادات الخاصة بها
const configComponents: Record<string, React.ComponentType<any>> = {
  // ===== الأنواع الأساسية =====
  HTTP_REQUEST: HTTPConfig,
  CONDITION: ConditionConfig,
  DELAY: DelayConfig,
  TRANSFORM: TransformConfig,
  NOTIFICATION: NotificationConfig,
  EMAIL: EmailConfig,
  SQL_QUERY: SQLConfig,
  LOOP: LoopConfig,
  WEBSOCKET: WebSocketConfig,
  FILE_UPLOAD: FileUploadConfig,
  SLACK: SlackConfig,
  DATABASE: DatabaseConfig,
  HTTP_RESPONSE: HttpResponseConfig,

  // ===== قطاع الهوية (Identity) =====
  CREATE_USER: CreateUserConfig,
  ASSIGN_ROLE: CreateUserConfig, // يمكن تخصيص مكون منفصل لاحقاً
  UPDATE_USER: CreateUserConfig,
  DELETE_USER: CreateUserConfig,

  // ===== قطاع الكيانات السيادية (Sovereign Entities) =====
  CREATE_ENTITY: CreateEntityConfig,
  UPDATE_ENTITY: CreateEntityConfig,
  VERIFY_KYB: CreateEntityConfig,
  ADD_REPRESENTATIVE: CreateEntityConfig,

  // ===== قطاع المالية (Finance) =====
  CREATE_INVOICE: CreateInvoiceConfig,
  TRANSFER_FUNDS: TransferFundsConfig,
  RECORD_PAYMENT: CreateInvoiceConfig,
  CHECK_BALANCE: CreateInvoiceConfig,

  // ===== قطاع التجارة (Commerce) =====
  CREATE_ORDER: CreateOrderConfig,
  UPDATE_INVENTORY: CreateOrderConfig,
  SHIP_ORDER: CreateOrderConfig,
  CANCEL_ORDER: CreateOrderConfig,

  // ===== قطاع الأكاديمية (Academy) =====
  ENROLL_COURSE: EnrollCourseConfig,
  COMPLETE_LESSON: EnrollCourseConfig,
  ISSUE_CERTIFICATE: EnrollCourseConfig,
  CREATE_COURSE: EnrollCourseConfig,

  // ===== قطاع الذكاء الاصطناعي (AI) =====
  AI_AGENT: AIAgentConfig,
};

interface NodeSettingsPanelProps {
  node?: Node;
  onUpdate: (nodeId: string, config: Record<string, any>) => void;
  onUpdateLabel: (nodeId: string, label: string) => void;
  onClose: () => void;
}

export default function NodeSettingsPanel({
  node,
  onUpdate,
  onUpdateLabel,
  onClose,
}: NodeSettingsPanelProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  if (!node) {
    return null;
  }

  const nodeType = node.data?.nodeType || 'UNKNOWN';
  const ConfigComponent = configComponents[nodeType];

  // معالج تحديث الإعدادات العامة
  const handleConfigUpdate = (newConfig: Record<string, any>) => {
    onUpdate(node.id, newConfig);
  };

  // معالج تحديث الاسم
  const handleLabelChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onUpdateLabel(node.id, e.target.value);
  };

  return (
    <div className="flex flex-col h-full p-4 space-y-4 overflow-y-auto">
      {/* الهيدر */}
      <div className="flex items-center justify-between shrink-0">
        <h3 className="font-semibold text-foreground/90 text-sm flex items-center gap-2">
          <span>⚙️</span>
          إعدادات العقدة
        </h3>
        <button
          onClick={onClose}
          className="p-1 rounded-lg hover:bg-white/10 transition-colors"
        >
          <X className="w-4 h-4 text-muted-foreground/60" />
        </button>
      </div>

      {/* اسم العقدة */}
      <div className="shrink-0">
        <label className="text-xs text-muted-foreground/60">اسم العقدة</label>
        <input
          type="text"
          value={node.data?.label || ''}
          onChange={handleLabelChange}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
        />
      </div>

      {/* نوع العقدة */}
      <div className="shrink-0">
        <label className="text-xs text-muted-foreground/60">النوع</label>
        <div className="mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-sm text-foreground/70">
          {nodeType}
        </div>
      </div>

      {/* إعدادات خاصة بنوع العقدة */}
      {ConfigComponent ? (
        <div className="flex-1">
          <ConfigComponent
            config={node.data?.config || {}}
            onChange={handleConfigUpdate}
            nodeId={node.id}
          />
        </div>
      ) : (
        <div className="flex-1 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-500/70 text-sm">
          ⚠️ لا توجد إعدادات مخصصة لهذا النوع من العقد.
        </div>
      )}

      {/* تلميح الأسرار */}
      <div className="p-3 rounded-xl bg-primary/5 border border-primary/10 text-xs text-muted-foreground/60 shrink-0">
        <p className="flex items-center gap-1.5">
          <Key className="w-3 h-3 text-primary/60" />
          استخدم <code className="bg-black/20 px-1.5 py-0.5 rounded font-mono text-primary/80 text-[10px]">{'{{'}secrets.NAME{'}}'}</code> للإشارة إلى الأسرار المخزنة
        </p>
        <p className="mt-1 text-[10px] text-muted-foreground/40">
          أضف أسرارك من <span className="text-primary/70 cursor-pointer hover:underline" onClick={() => window.location.href = '/automation/secrets'}>صفحة الأسرار</span>
        </p>
      </div>

      {/* خيارات متقدمة (قابلة للطي) */}
      <button
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="flex items-center gap-2 text-xs text-muted-foreground/60 hover:text-foreground/80 transition-colors shrink-0"
      >
        <Settings className="w-3 h-3" />
        {showAdvanced ? 'إخفاء الخيارات المتقدمة' : 'عرض الخيارات المتقدمة'}
      </button>

      {showAdvanced && (
        <div className="space-y-3 p-3 rounded-xl bg-white/5 border border-white/10 shrink-0">
          <div>
            <label className="text-xs text-muted-foreground/60">مهلة (ثانية)</label>
            <input
              type="number"
              value={node.data?.config?.timeout_seconds || 30}
              onChange={(e) => {
                const newConfig = { ...node.data.config, timeout_seconds: parseInt(e.target.value) || 30 };
                handleConfigUpdate(newConfig);
              }}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground/60">إعادة المحاولة عند الفشل</label>
            <input
              type="number"
              value={node.data?.config?.retry_on_failure || 0}
              onChange={(e) => {
                const newConfig = { ...node.data.config, retry_on_failure: parseInt(e.target.value) || 0 };
                handleConfigUpdate(newConfig);
              }}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            />
          </div>
        </div>
      )}
    </div>
  );
}