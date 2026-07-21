// components/automation/node-configs/AIAgentConfig.tsx
'use client';

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAvailableAgents } from '@/services/automation.service';
import { Loader2, AlertTriangle, Shield, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AIAgentConfigProps {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}

export default function AIAgentConfig({ config, onChange }: AIAgentConfigProps) {
  const [selectedAgent, setSelectedAgent] = useState<string>(config.agent_id || '');

  const { data: agents, isLoading } = useQuery({
    queryKey: ['available-agents'],
    queryFn: () => getAvailableAgents().then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  // تحديث الإعدادات عند تغيير الوكيل
  const handleAgentChange = (agentId: string) => {
    setSelectedAgent(agentId);
    onChange('agent_id', parseInt(agentId));

    // تحديث الإعدادات الافتراضية بناءً على قدرات الوكيل
    const agent = agents?.find(a => a.id === parseInt(agentId));
    if (agent) {
      if (agent.can_execute_payments) {
        onChange('action_type', 'TRANSFER_FUNDS');
      } else if (agent.can_sign_contracts) {
        onChange('action_type', 'SIGN_CONTRACT');
      } else {
        onChange('action_type', 'ANALYZE_SENSOR');
      }
    }
  };

  const selectedAgentData = agents?.find(a => a.id === parseInt(selectedAgent));

  return (
    <div className="space-y-4">
      {/* اختيار الوكيل */}
      <div>
        <label className="text-xs text-muted-foreground/60">الوكيل الرقمي</label>
        {isLoading ? (
          <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground/60">
            <Loader2 className="w-4 h-4 animate-spin" />
            جاري تحميل الوكلاء...
          </div>
        ) : (
          <select
            value={selectedAgent}
            onChange={(e) => handleAgentChange(e.target.value)}
            className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80"
          >
            <option value="">اختر وكيلاً...</option>
            {agents?.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name} ({agent.role})
              </option>
            ))}
          </select>
        )}
      </div>

      {/* تفاصيل الوكيل المختار */}
      {selectedAgentData && (
        <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground/60">الدور</span>
            <span className="text-foreground/80">{selectedAgentData.role}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground/60">الصلاحيات</span>
            <div className="flex gap-2">
              {selectedAgentData.can_execute_payments && (
                <span className="text-xs text-amber-500 flex items-center gap-1">
                  <Shield className="w-3 h-3" /> مالي
                </span>
              )}
              {selectedAgentData.can_sign_contracts && (
                <span className="text-xs text-blue-500 flex items-center gap-1">
                  <CheckCircle className="w-3 h-3" /> تعاقدي
                </span>
              )}
              {!selectedAgentData.can_execute_payments && !selectedAgentData.can_sign_contracts && (
                <span className="text-xs text-muted-foreground/50">تحليلي</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* حقل التعليمات (Prompt) */}
      <div>
        <label className="text-xs text-muted-foreground/60">التعليمات (Prompt)</label>
        <textarea
          value={config.prompt || ''}
          onChange={(e) => onChange('prompt', e.target.value)}
          rows={3}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/70 resize-none"
          placeholder="حلل هذه البيانات وأعط توصية: {{node_1.output}}"
        />
        <p className="text-[10px] text-muted-foreground/40 mt-1">
          استخدم {'{{'}node_id.output{'}}'} للإشارة إلى مخرجات عقد سابقة
        </p>
      </div>

      {/* نوع الإجراء */}
      <div>
        <label className="text-xs text-muted-foreground/60">نوع الإجراء</label>
        <select
          value={config.action_type || 'ANALYZE_SENSOR'}
          onChange={(e) => onChange('action_type', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80"
        >
          <option value="ANALYZE_SENSOR">تحليل بيانات</option>
          <option value="ANALYZE_PROJECT">تحليل مشروع</option>
          <option value="ASSIGN_COURSE">تسجيل في كورس</option>
          <option value="SEND_EMAIL">إرسال بريد</option>
          <option value="CREATE_TICKET">إنشاء تذكرة</option>
          {selectedAgentData?.can_execute_payments && (
            <option value="TRANSFER_FUNDS" className="text-amber-500">💰 تحويل أموال</option>
          )}
          {selectedAgentData?.can_sign_contracts && (
            <option value="SIGN_CONTRACT" className="text-blue-500">📝 توقيع عقد</option>
          )}
        </select>
      </div>

      {/* خيارات متقدمة */}
      <div className="space-y-3 p-3 rounded-xl bg-white/5 border border-white/10">
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-muted-foreground/60 cursor-pointer">
            <input
              type="checkbox"
              checked={config.wait_for_approval || false}
              onChange={(e) => onChange('wait_for_approval', e.target.checked)}
              className="w-4 h-4 rounded border-white/20 bg-white/5"
            />
            انتظار الموافقة البشرية
          </label>
          {config.wait_for_approval && (
            <span className="text-[10px] text-amber-500/70 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              سيتوقف التنفيذ لحين الموافقة
            </span>
          )}
        </div>
        <div>
          <label className="text-xs text-muted-foreground/60">مهلة الانتظار (ثانية)</label>
          <input
            type="number"
            value={config.timeout_seconds || 60}
            onChange={(e) => onChange('timeout_seconds', parseInt(e.target.value) || 60)}
            className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            min="5"
            max="300"
          />
        </div>
        <div>
          <label className="text-xs text-muted-foreground/60">مفتاح حفظ النتيجة في السياق</label>
          <input
            type="text"
            value={config.save_response_to || 'ai_response'}
            onChange={(e) => onChange('save_response_to', e.target.value)}
            className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/80"
            placeholder="ai_response"
          />
        </div>
      </div>
    </div>
  );
}